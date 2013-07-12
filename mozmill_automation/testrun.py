# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is MozMill automation code.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Henrik Skupin <hskupin@mozilla.com>
#   Dave Hunt <dhunt@mozilla.com>
#   Aaron Train <atrain@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import ConfigParser
import copy
import datetime
import os
import optparse
import shutil
import sys
import tempfile
import time
import urllib
import zipfile

import application
import install
import mozinfo
import mozmill
import rdf_parser
import report
import repository


MOZMILL_TESTS_REPOSITORIES = {
    'firefox' : "http://hg.mozilla.org/qa/mozmill-tests",
    'thunderbird' : "http://hg.mozilla.org/users/bugzilla_standard8.plus.com/qa-tests/",
}

MOZMILL_CLI = {
    'firefox' : mozmill.CLI,
    'thunderbird' : mozmill.ThunderbirdCLI,
}

MOZMILL_RESTART_CLI = {
    'firefox' : mozmill.RestartCLI,
    'thunderbird' : mozmill.ThunderbirdRestartCLI,
}


class TestFailedException(Exception):
    """Exception for a resource not being found (e.g. no logs)"""
    def __init__(self):
        Exception.__init__(self, "Some tests have been failed.")


class TestRun(object):
    """ Class to execute a Mozmill test-run. """

    parser_options = {("-a", "--addons",): dict(dest="addons",
                                                action="append",
                                                default=None,
                                                metavar="ADDONS",
                                                help="Add-ons to install",
                                               ),
                      ("--application",): dict(dest="application",
                                               choices=["firefox", "thunderbird"],
                                               metavar="APP",
                                               default="firefox",
                                               help="Application Name, i.e. firefox, thunderbird"),
                      ("--junit",): dict(dest="junit_file",
                                         default=None,
                                         metavar="PATH",
                                         help="Create JUnit XML style report file at given path"),
                      ("-r", "--report",): dict(dest="report_url",
                                                metavar="URL",
                                                help="Send results to the report server"),
                      ("--repository",): dict(dest="repository_url",
                                              default=None,
                                              metavar="URL",
                                              help="URL of a custom remote or local repository"),
                      ("--screenshot-path",): dict(dest="screenshot_path",
                                                   default=None,
                                                   metavar="PATH",
                                                   help="Path to use for screenshots"),
                      ("--tag",): dict(dest="tags",
                                       action="append",
                                       default=None,
                                       metavar="TAG",
                                       help="Tag to apply to the report")
                     }


    def __init__(self, args=sys.argv[1:], debug=False, repository_path=None,
                 test_path=None, timeout=None):

        self.mozmill_args = []

        usage = "usage: %prog [options] (binaries|folders)"
        self.parser = optparse.OptionParser(usage=usage)
        for names, opts in self.parser_options.items():
            self.parser.add_option(*names, **opts)

        mozmill_options = optparse.OptionGroup(self.parser, "Mozmill Options")
        mozmill_options.add_option("-l", "--logfile",
                                   action="callback",
                                   callback=self._add_mozmill_arg,
                                   dest="logfile",
                                   type="string",
                                   metavar="PATH",
                                   help="Path to the log file")
        mozmill_options.add_option("-P", "--port",
                                   action="callback",
                                   callback=self._add_mozmill_arg,
                                   default=None,
                                   dest="port",
                                   type="int",
                                   metavar="PORT",
                                   help="Port to use for JSBridge")
        mozmill_options.add_option("-p", "--profile",
                                   action="callback",
                                   callback=self._add_mozmill_arg,
                                   default=None,
                                   dest="profile",
                                   type="string",
                                   metavar="PATH",
                                   help="Profile path")
        self.parser.add_option_group(mozmill_options)

        (self.options, self.args) = self.parser.parse_args(args)
        # Consume the system arguments
        del sys.argv[1:]

        # Add Mozmill arguments
        sys.argv.extend(self.mozmill_args)

        self.binaries = self.args
        self.debug = debug
        self.timeout = timeout
        self.repository_path = repository_path
        self.test_path = test_path

        if self.options.repository_url:
            self.repository_url = self.options.repository_url
        else:
            self.repository_url = MOZMILL_TESTS_REPOSITORIES[self.options.application]

        self.addon_list = []
        self.downloaded_addons = []
        self.testrun_index = 0
        self.restart_tests = False

        self.last_failed_tests = None
        self.last_exception = None

    def _add_mozmill_arg(self, option, opt_str, value, parser):
        self.mozmill_args.append('%s=%s' % (option.get_opt_string(), value))

    def _generate_custom_report(self):
        if self.options.junit_file:
            filename = self._get_unique_filename(self.options.junit_file)
            custom_report = self.update_report(self._mozmill.mozmill.get_report())
            report.JUnitReport(custom_report, filename)

    def _get_binaries(self):
        """ Returns the list of binaries to test. """
        return self._binaries

    def _get_unique_filename(self, filename):
        (basename, ext) = os.path.splitext(filename)
        return '%s_%i%s' % (basename, self.testrun_index, ext)

    def _set_binaries(self, value):
        """ Sets the list of binaries to test. """
        self._binaries = [ ]

        if not value:
            return

        for path in value:
            if not os.path.exists(path):
                raise Exception("Path '%s' cannot be found." % (path))

            # Check if it's an installer or an already installed build
            if application.is_installer(self.options.application, path) or \
               application.is_app_folder(path):
                self._binaries.append(os.path.abspath(path))
                continue
            # Otherwise recursivily scan the folder and add existing files
            for root, dirs, files in os.walk(path):
                for file in files:
                    if not file in [".DS_Store"] and \
                    application.is_installer(self.options.application, file):
                        self._binaries.append(os.path.abspath(os.path.join(root, file)))

    binaries = property(_get_binaries, _set_binaries, None)

    def addon_details(self, path):
        """ Retrieve detailed information of the add-on """

        details = {
            'id' : None,
            'name': None,
            'version': None
        }

        try:
            # Retrieve the content of the install.rdf file
            file = zipfile.ZipFile(path, "r")

            # Parse RDF data
            from xml.dom.minidom import parseString
            doc = parseString(file.read("install.rdf"))

            # Find the namespace for the extension manager in the RDF root node
            em = rdf_parser.get_namespace_id(doc, "http://www.mozilla.org/2004/em-rdf#");
            rdf = rdf_parser.get_namespace_id(doc, "http://www.w3.org/1999/02/22-rdf-syntax-ns#");

            description = doc.getElementsByTagName(rdf + "Description").item(0);
            for node in description.childNodes:
                name = node.nodeName.replace(em, "")
                if name in details.keys():
                    details.update({
                        name: rdf_parser.get_text(node)
                    })

        except Exception, e:
            print e

        return details

    def cleanup_binary(self, binary):
        """ Remove the build when it has been installed before. """
        if application.is_installer(self.options.application, binary):
            install.Installer().uninstall(self._folder)

    def cleanup_repository(self):
        """ Removes the local version of the repository. """
        self._repository.remove()

    def clone_repository(self):
        """ Clones the repository to a local temporary location. """
        try:
            # XXX: mktemp is marked as deprecated but lets use it because with
            # older versions of Mercurial the target folder should not exist.
            self.repository_path = tempfile.mktemp(".mozmill-tests")
            self._repository = repository.Repository(self.repository_url,
                                                     self.repository_path)
            self._repository.clone()
        except Exception, e:
            raise Exception("Failure in setting up the mozmill-tests repository. " +
                            e.message)

    def download_addon(self, url, target_path):
        """ Download the XPI file """
        try:
            filename = url.split('?')[0].rstrip('/').rsplit('/', 1)[-1]
            target_path = os.path.join(target_path, filename)

            print "Downloading %s to %s" % (url, target_path)
            urllib.urlretrieve(url, target_path)

            return target_path
        except Exception, e:
            print e

    def prepare_addons(self):
        """ Prepare the addons for the test run. """

        for addon in self.options.addons:
            if addon.startswith("http") or addon.startswith("ftp"):
                path = self.download_addon(addon, tempfile.gettempdir())
                self.downloaded_addons.append(path)
                self.addon_list.append(path)
            else:
                self.addon_list.append(addon)

    def prepare_binary(self, binary):
        """ Prepare the binary for the test run. """

        if application.is_installer(self.options.application, binary):
            install_path = tempfile.mkdtemp(".binary")
            self._folder = install.Installer().install(binary, install_path)
            self._application = application.get_binary(self.options.application, self._folder)
        else:
            folder = os.path.dirname(binary)
            self._folder = folder if not os.path.isdir(binary) else binary
            self._application = binary

        # Print application details
        ini = application.ApplicationIni(self._folder)
        print '*** Application: %s %s' % (
            ini.get('App', 'Name'),
            ini.get('App', 'Version'))

    def prepare_repository(self):
        """ Update the repository to the needed branch. """

        # Retrieve the Gecko branch from the application.ini file
        ini = application.ApplicationIni(self._folder)
        repository_url = ini.get('App', 'SourceRepository')

        # Update the mozmill-test repository to match the Gecko branch
        branch_name = self._repository.identify_branch(repository_url)
        self._repository.update(branch_name)

    def prepare_tests(self):
        """ Preparation which has to be done before starting a test. """

        if self.restart_tests:
            cls = MOZMILL_RESTART_CLI[self.options.application]
        else:
            cls = MOZMILL_CLI[self.options.application]

        self._mozmill = cls()
        self._mozmill.addons = self.addon_list
        self._mozmill.options.debug = self.debug
        self._mozmill.options.binary = self._application
        self._mozmill.options.showall = True
        self._mozmill.tests = [os.path.join(self.repository_path, self.test_path)]

        if self.timeout:
            self._mozmill.mozmill.jsbridge_timeout = self.timeout

        self.installed_addons = None
        self._mozmill.mozmill.add_listener(self.addons_event, eventType='mozmill.installedAddons')

        self.graphics = None
        self._mozmill.mozmill.add_listener(self.graphics_event, eventType='mozmill.graphics')

        if self.options.screenshot_path:
            path = os.path.abspath(self.options.screenshot_path)
            if not os.path.isdir(path):
                os.makedirs(path)
            self._mozmill.mozmill.persisted["screenshotPath"] = path

    def addons_event(self, obj):
        if not self.installed_addons:
            self.installed_addons = obj

    def graphics_event(self, obj):
        if not self.graphics:
            self.graphics = obj

    def remove_downloaded_addons(self):
        for path in self.downloaded_addons:
            try:
                # Remove downloaded add-on
                print "*** Removing downloaded add-on '%s'." % path
                os.remove(path)
            except:
                print "*** Failed to remove downloaded add-on '%s'." % path

    def run_tests(self):
        """ Start the execution of the tests. """

        self.prepare_tests()

        try:
            self._mozmill.run()
        except SystemExit:
            # Mozmill itself calls sys.exit(1) but we do not want to exit
            pass

        # Whenever a test fails it has to be marked, so we quit with the correct exit code
        self.last_failed_tests = self.last_failed_tests or self._mozmill.mozmill.fails

        self._generate_custom_report()
        self.testrun_index += 1

        if self.options.report_url:
            self.send_report(self.options.report_url)

    def run(self):
        """ Run software update tests for all specified builds. """

        # If no binaries have been specified we cancel the test-run
        if not self.binaries:
            print "*** No builds have been specified. Use --help to see all options."
            return

        # Print platform details
        print '*** Platform: %s %s %sbit' % (
            str(mozinfo.os).capitalize(),
            mozinfo.version,
            mozinfo.bits)

        self.clone_repository()

        if self.options.addons:
            self.prepare_addons()

        try:
            # Run tests for each binary
            for binary in self.binaries:
                try:
                    self.prepare_binary(binary)
                    self.prepare_repository()
                    self.run_tests()
                except Exception, e:
                    print str(e)
                    self.last_exception = e
                finally:
                    self.cleanup_binary(binary)

        finally:
            self.remove_downloaded_addons()
            self.cleanup_repository()

            # If an exception has been thrown for any of the builds under test
            # re-throw the exact same exception again. We just need it for the
            # exit code
            if self.last_exception:
                raise self.last_exception

            # If a test has been failed ensure that we exit with status 2
            if self.last_failed_tests:
                raise TestFailedException()

    def send_report(self, report_url):
        """ Send the report to a CouchDB instance """

        report = self.update_report(self._mozmill.mozmill.get_report())
        return self._mozmill.mozmill.send_report(report, report_url)

    def update_report(self, report):
        """ Customize the report data. """

        report['report_type'] = self.report_type
        report['report_version'] = self.report_version
        report['tests_repository'] = self._repository.url
        report['tests_changeset'] = self._repository.changeset

        if self.options.tags:
            report['tags'] = self.options.tags

        # Optional information received by Python callbacks
        if self.installed_addons:
            report['addons'] = self.installed_addons
        if self.graphics:
            report['system_info']['graphics'] = self.graphics
        return report


class AddonsTestRun(TestRun):
    """ Class to execute a Firefox add-ons test-run """

    report_type = "firefox-addons"
    report_version = "1.0"

    parser_options = copy.copy(TestRun.parser_options)
    parser_options[("--target-addons",)] = dict(dest="target_addons",
                                                action='append',
                                                default=[],
                                                metavar="ID",
                                                help="Only test those listed add-ons from the " +
                                                     "mozmill-tests repository, e.g. ide@seleniumhq.org")
    parser_options[("--with-untrusted",)] = dict(dest="with_untrusted",
                                                 action="store_true",
                                                 default=False,
                                                 help="Also run tests for add-ons which are not stored on AMO")


    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

    def get_all_addons(self):
        """ Retrieves all add-ons inside the "addons" folder. """

        path = os.path.join(self.repository_path, "tests", "addons")
        return [entry for entry in os.listdir(path)
                      if os.path.isdir(os.path.join(path, entry))]

    def get_download_url(self):
        """ Read the addon.ini file and get the URL of the XPI. """

        try:
            filename = os.path.join(self.repository_path, self._addon_path, "addon.ini")
            config = ConfigParser.RawConfigParser()
            config.read(filename)

            # Get the platform the script is running on
            if sys.platform in ("cygwin", "win32"):
                platform = "win"
            elif sys.platform in ("darwin"):
                platform = "mac"
            elif sys.platform in ("linux2", "sunos5"):
                platform = "linux"

            return config.get("download", platform)
        except Exception, e:
            print str(e)
            return None

    def run_tests(self):
        """ Execute the normal and restart tests in sequence. """

        # If no target add-ons have been specified get all available add-on tests
        if not self.options.target_addons:
            self.options.target_addons = self.get_all_addons()

        for self._addon in self.options.target_addons:
            try:
                # Get the download URL
                self._addon_path = os.path.join('tests', 'addons', self._addon)
                url = self.get_download_url()

                if url is None:
                    print "*** Could not read settings from '%s'." % filename
                    continue

                # Check if the download URL is trusted and we can proceed
                if not "addons.mozilla.org" in url and not self.options.with_untrusted:
                    print "*** Download URL for '%s' is not trusted." % os.path.basename(url)
                    print "*** Use --with-untrusted to force testing this add-on."
                    continue

                # Download the add-on
                self.target_addon = self.download_addon(url, tempfile.gettempdir())

                # Run normal tests if some exist
                self.test_path = os.path.join(self._addon_path, 'tests')
                if os.path.isdir(os.path.join(self.repository_path, self.test_path)):
                    try:
                        self.restart_tests = False
                        self.addon_list.append(self.target_addon)
                        TestRun.run_tests(self)
                    except Exception, e:
                        print str(e)
                        self.last_exception = e
                    finally:
                        self.addon_list.remove(self.target_addon)

                # Run restart tests if some exist
                self.test_path = os.path.join(self._addon_path, 'restartTests')
                if os.path.isdir(os.path.join(self.repository_path, self.test_path)):
                    try:
                        self.restart_tests = True
                        self.addon_list.append(self.target_addon)
                        TestRun.run_tests(self)
                    except Exception, e:
                        print str(e)
                        self.last_exception = e
                    finally:
                        self.addon_list.remove(self.target_addon)

            except Exception, e:
                print str(e)
                self.last_exception = e
            finally:
                try:
                    # Remove downloaded add-on
                    if os.path.exists(self.target_addon):
                        print "*** Removing target add-on '%s'." % self.target_addon
                        os.remove(self.target_addon)
                except:
                    print "*** Failed to remove target add-on '%s'." % self.target_addon

    def update_report(self, report):
        TestRun.update_report(self, report)
        report['target_addon'] = self.addon_details(self.target_addon)

        return report


class EnduranceTestRun(TestRun):
    """ Class to execute a Firefox endurance test-run """

    report_type = "firefox-endurance"
    report_version = "1.2"

    parser_options = copy.copy(TestRun.parser_options)
    parser_options[("--delay",)] = dict(dest="delay",
                                        type="float",
                                        default=5,
                                        metavar="DELAY",
                                        help="Duration (in seconds) to wait before each iteration")
    parser_options[("--entities",)] = dict(dest="entities",
                                           type="int",
                                           default=1,
                                           metavar="ENTITIES",
                                           help="Number of entities to create within a test snippet")
    parser_options[("--iterations",)] = dict(dest="iterations",
                                             type="int",
                                             default=1,
                                             metavar="ITERATIONS",
                                             help="Number of times to repeat each test snippet")
    parser_options[("--no-restart",)] = dict(dest="restart_tests",
                                             action="store_false",
                                             default=True,
                                             help="Do not restart application between tests")
    parser_options[("--reserved",)] = dict(dest="reserved",
                                           default=None,
                                           metavar="RESERVED",
                                           help="Specify a reserved test to run")


    def __init__(self, *args, **kwargs):

        TestRun.__init__(self, *args, **kwargs)

        self.delay = "%.0d" % (self.options.delay * 1000)
        self.timeout = self.options.delay + 60
        self.restart_tests = self.options.restart_tests

    def calculate_stats(self, data, keys):
        """ Calculates the min/max/average of each key in data. """

        stats = {}
        for key in keys:
            stats[key] = {'average' : sum(data[key]) / len(data[key]),
                          'min' : min(data[key]),
                          'max' : max(data[key])}
        return stats

    def populate_metrics(self, dict, keys, data):
        for key in keys:
            _data = data[key]
            if not isinstance(_data, list):
                _data = [_data]
            dict.setdefault(key, []).extend(_data)

    def prepare_tests(self):
        TestRun.prepare_tests(self)
        self._mozmill.mozmill.add_listener(self.endurance_event, eventType='mozmill.enduranceResults')

        self._mozmill.mozmill.persisted['endurance'] = {'delay': self.delay,
                                                        'iterations': self.options.iterations,
                                                        'entities': self.options.entities,
                                                        'restart': self.options.restart_tests}

    def run_tests(self):
        """ Execute the endurance tests in sequence. """

        self.endurance_results = []

        try:
            self.test_path = os.path.join('tests', 'endurance')
            if self.options.reserved:
                self.test_path = os.path.join(self.test_path, 'reserved', self.options.reserved)
            TestRun.run_tests(self)

        except Exception, e:
            print str(e)
            self.last_exception = e

    def endurance_event(self, obj):
        self.endurance_results.append(obj)

    def update_report(self, report):
        # get basic report
        TestRun.update_report(self, report)

        # update report with endurance data
        report['endurance'] = self._mozmill.mozmill.persisted['endurance']
        report['endurance']['results'] = self.endurance_results

        blacklist = ('timestamp', 'label')
        metrics = []

        all_metrics = {}

        for test in report['endurance']['results']:
            test_metrics = {}

            for iteration in test['iterations']:
                iteration_metrics = {}

                for checkpoint in iteration['checkpoints']:
                    if not metrics:
                        metrics = [key for key in checkpoint.keys() if not key in blacklist]

                    self.populate_metrics(iteration_metrics, metrics, checkpoint)

                iteration['stats'] = self.calculate_stats(iteration_metrics, metrics)
                self.populate_metrics(test_metrics, metrics, iteration_metrics)

            test['stats'] = self.calculate_stats(test_metrics, metrics)
            self.populate_metrics(all_metrics, metrics, test_metrics)

        report['endurance']['stats'] = self.calculate_stats(all_metrics, metrics)

        return report


class FunctionalTestRun(TestRun):
    """ Class to execute a Firefox functional test-run """

    report_type = "firefox-functional"
    report_version = "1.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

    def run_tests(self):
        """ Execute the normal and restart tests in sequence. """

        try:
            self.restart_tests = False
            self.test_path = os.path.join('tests', 'functional')
            TestRun.run_tests(self)
        except Exception, e:
            print str(e)
            self.last_exception = e

        try:
            self.restart_tests = True
            self.test_path = os.path.join('tests', 'functional', 'restartTests')
            TestRun.run_tests(self)
        except Exception, e:
            print str(e)
            self.last_exception = e


class L10nTestRun(TestRun):
    """ Class to execute a Firefox l10n test-run """

    report_type = "firefox-l10n"
    report_version = "1.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

    def run_tests(self):
        """ Execute the existent l10n tests in sequence. """

        try:
            self.restart_tests = True
            self.test_path = os.path.join('tests','l10n')
            TestRun.run_tests(self)
        except Exception, e:
            print str(e)
            self.last_exception = e


class RemoteTestRun(TestRun):
    """ Class to execute a test-run for remote content. """

    report_type = "firefox-remote"
    report_version = "1.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

    def run_tests(self):
        """ Execute the normal and restart tests in sequence. """

        try:
            self.restart_tests = False
            self.test_path = os.path.join('tests', 'remote')
            TestRun.run_tests(self)
        except Exception, e:
            print str(e)
            self.last_exception = e

        try:
            self.restart_tests = True
            self.test_path = os.path.join('tests', 'remote', 'restartTests')
            TestRun.run_tests(self)
        except Exception, e:
            print str(e)
            self.last_exception = e


class UpdateTestRun(TestRun):
    """ Class to execute software update tests """

    report_type = "firefox-update"
    report_version = "1.0"

    parser_options = copy.copy(TestRun.parser_options)
    parser_options[("--channel",)] = dict(dest="channel",
                                          default=None,
                                          metavar="CHANNEL",
                                          help="Update channel")
    parser_options[("--no-fallback",)] = dict(dest="no_fallback",
                                              action="store_true",
                                              default=False,
                                              help="Do not perform a fallback update")
    parser_options[("--target-buildid",)] = dict(dest="target_buildid",
                                                 default=None,
                                                 metavar="TARGET_ID",
                                                 help="Expected build id of the updated build")


    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

        self.results = [ ]

        # Download of updates normally take longer than 60 seconds
        # Soft-timeout is 360s so make the hard-kill timeout 5s longer
        self.timeout = 365

    def build_wiki_entry(self, result):
        """ Until we show results on the dashboard create a wiki like output
            format for data from the first and last update performed """

        first_update = result["updates"][0]
        last_update = result["updates"][-1]

        entry = "* %s => %s, %s, %s, %s%s, %s, %s, '''%s'''\n" \
                "** %s ID:%s\n** %s ID:%s\n" \
                "** Passed %d :: Failed %d :: Skipped %d\n" % \
                (first_update["build_pre"]["version"],
                 last_update["build_post"]["version"],
                 last_update["patch"].get("type", "n/a"),
                 first_update["build_pre"]["locale"],
                 "complete" if last_update["patch"].get("is_complete", False) else "partial",
                 "+fallback" if last_update["fallback"] else "",
                 last_update["patch"].get("channel", "n/a"),
                 datetime.date.today(),
                 "PASS" if last_update["success"] else "FAIL",
                 first_update["build_pre"]["user_agent"],
                 first_update["build_pre"]["buildid"],
                 last_update["build_post"]["user_agent"],
                 last_update["build_post"]["buildid"],
                 len(result["passes"]),
                 len(result["fails"]),
                 len(result["skipped"]))
        return entry

    def prepare_binary(self, binary):
        TestRun.prepare_binary(self, binary)

        # If a fallback update has to be performed, create a second copy
        # of the application to avoid running the installer twice
        if not self.options.no_fallback:
            try:
                self._backup_folder = tempfile.mkdtemp(".binary_backup")

                print "*** Creating backup of binary (%s => %s)" % (self._folder,
                                                                    self._backup_folder)
                shutil.rmtree(self._backup_folder)
                shutil.copytree(self._folder, self._backup_folder)
            except Exception:
                print "*** Failure while creating the backup of the binary."

    def prepare_channel(self):
        update_channel = application.UpdateChannel()
        update_channel.folder = self._folder

        if self.options.channel is None:
            self.channel = update_channel.channel
        else:
            update_channel.channel = self.options.channel
            self.channel = self.options.channel

    def prepare_tests(self):
        self.prepare_channel()
        self.restart_tests = True

        TestRun.prepare_tests(self)
        self._mozmill.mozmill.persisted["channel"] = self.channel
        if self.options.target_buildid:
            self._mozmill.mozmill.persisted["targetBuildID"] = self.options.target_buildid

    def restore_binary(self):
        """ Restores the backup of the application binary. """
        timeout_rmtree = 15
        timeout = time.time() + timeout_rmtree

        print "*** Removing binary at '%s'" % self._folder
        while True:
            try:
                shutil.rmtree(self._folder)
                break
            except Exception, e:
                print str(e)
                if time.time() >= timeout:
                    print "*** Cannot remove folder '%s'" % self._folder
                    raise
                else:
                    time.sleep(1)

        print "*** Restoring backup from '%s'" % self._backup_folder
        shutil.move(self._backup_folder, self._folder)

    def run_tests(self):
        """ Start the execution of the tests. """

        fallback_result = False
        direct_result = False

        # Run fallback update test
        if not self.options.no_fallback:
            fallback_data = self.run_update_tests(True)
            if fallback_data["updates"]:
                fallback_result = fallback_data["updates"][-1].get("success", False)

            # Restoring application backup to run direct update tests
            self.restore_binary()

        # Run direct update test
        direct_data = self.run_update_tests(False)
        if direct_data["updates"]:
            direct_result = direct_data["updates"][-1].get("success", False)

        # Process results for wiki style output
        if self.options.no_fallback:
            # No fallback tests - simply add the result from the direct update
            self.results.append(self.build_wiki_entry(direct_data))
        else:
            # If direct and fallback updates passes simply add one single entry
            # Otherwise add both results from direct and fallback updates
            if direct_result and fallback_result:
                self.results.append(self.build_wiki_entry(direct_data))
            else:
                self.results.append(self.build_wiki_entry(direct_data))
                self.results.append(self.build_wiki_entry(fallback_data))

    def run_update_tests(self, is_fallback):
        try:
            folder = 'testFallbackUpdate' if is_fallback else 'testDirectUpdate'
            self.test_path = os.path.join('tests', 'update', folder)
            TestRun.run_tests(self)
        except Exception, e:
            print "Execution of test-run aborted: %s" % str(e)
            self.last_exception = e
        finally:
            data = self._mozmill.mozmill.persisted

            try:
                path = data["updateStagingPath"]
                if os.path.exists(path):
                    print "*** Removing updates staging folder '%s'" % path
                    shutil.rmtree(path)
            except Exception, e:
                print "Failed to remove the update staging folder: " + str(e)
                self.last_exception = e

            # If a Mozmill test fails the update has to be also marked as failed
            if self._mozmill.mozmill.fails:
                data["success"] = False

            data["passes"] = self._mozmill.mozmill.passes
            data["fails"] = self._mozmill.mozmill.fails
            data["skipped"] = self._mozmill.mozmill.skipped

            return data

    def run(self):
        self.results = [ ]
        TestRun.run(self)

        # Print results to the console
        print "\nResults:\n========"
        for result in self.results:
            print result

    def update_report(self, report):
        TestRun.update_report(self, report)
        report['updates'] = self._mozmill.mozmill.persisted['updates']

        return report


def exec_testrun(cls):
    try:
        cls().run()
    except TestFailedException:
        sys.exit(2)


def addons_cli():
    exec_testrun(AddonsTestRun)


def endurance_cli():
    exec_testrun(EnduranceTestRun)


def functional_cli():
    exec_testrun(FunctionalTestRun)


def l10n_cli():
    exec_testrun(L10nTestRun)


def remote_cli():
    exec_testrun(RemoteTestRun)


def update_cli():
    exec_testrun(UpdateTestRun)
