# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import optparse
import sys
import tempfile
import urllib

import manifestparser
import mozinstall
import mozmill
import mozmill.logger

import application
import report
import reports
import repository

MOZMILL_TESTS_REPOSITORIES = {
    'firefox' : "http://hg.mozilla.org/qa/mozmill-tests",
    'thunderbird' : "http://hg.mozilla.org/users/bugzilla_standard8.plus.com/qa-tests/",
}


class TestFailedException(Exception):
    """ Exception for failed tests. """
    def __init__(self):
        Exception.__init__(self, "Some tests have failed.")


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
                      ("-l", "--logfile",): dict(dest="logfile",
                                                 metavar="PATH",
                                                 help="Path to the log file"),
                      ("-P", "--port",): dict(dest="port",
                                              default=None,
                                              type="int",
                                              metavar="PORT",
                                              help="Port to use for JSBridge."),
                      ('-p', "--profile",): dict(dest="profile",
                                                 default=None,
                                                 metavar="PATH",
                                                 help="Profile path."),
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
                 manifest_path=None, timeout=None):

        usage = "usage: %prog [options] (binaries|folders)"
        self.parser = optparse.OptionParser(usage=usage)
        for names, opts in self.parser_options.items():
            self.parser.add_option(*names, **opts)
        (self.options, self.args) = self.parser.parse_args(args)
        # Consume the system arguments
        del sys.argv[1:]

        self.binaries = self.args
        self.debug = debug
        self.timeout = timeout
        self.repository_path = repository_path
        self.manifest_path = manifest_path

        if self.options.repository_url:
            self.repository_url = self.options.repository_url
        else:
            self.repository_url = MOZMILL_TESTS_REPOSITORIES[self.options.application]

        self.addon_list = []
        self.downloaded_addons = []
        self.testrun_index = 0

        self.last_failed_tests = None
        self.last_exception = None

    def _generate_custom_report(self):
        if self.options.junit_file:
            filename = self._get_unique_filename(self.options.junit_file)
            custom_report = self.update_report(self._mozmill.mozmill.get_report())
            report.JUnitReport(custom_report, filename)

    def _get_unique_filename(self, filename):
        (basename, ext) = os.path.splitext(filename)
        return '%s_%i%s' % (basename, self.testrun_index, ext)

    def cleanup_binary(self, binary):
        """ Remove the build when it has been installed before. """
        if application.is_installer(self.options.application, binary):
            mozinstall.uninstall(self._folder)

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

    def cleanup_repository(self):
        """ Removes the local version of the repository. """
        self._repository.remove()

    def download_addon(self, url, target_path):
        """ Download the XPI file. """
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
            self._folder = mozinstall.install(binary, install_path)
            self._application = application.get_binary(self.options.application, self._folder)
        else:
            folder = os.path.dirname(binary)
            self._folder = folder if not os.path.isdir(binary) else binary
            self._application = binary

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

        # instantiate handlers
        logger = mozmill.logger.LoggerListener(log_file=self.options.logfile,
                                               console_level=self.debug and 'DEBUG' or 'INFO',
                                               file_level=self.debug and 'DEBUG' or 'INFO',
                                               debug=self.debug)
        handlers = [logger]
        if self.options.report_url:
            self.report = reports.DashboardReport(self.options.report_url, self)
            handlers.append(self.report)

        # instantiate MozMill
        profile_args = dict(addons=self.addon_list)
        runner_args = dict(binary=self._application)
        mozmill_args = dict(app=self.options.application,
                            handlers=handlers,
                            profile_args=profile_args,
                            runner_args=runner_args)
        if self.options.port:
            mozmill_args['jsbridge_port'] = self.options.port
        if self.timeout:
            mozmill_args['jsbridge_timeout'] = self.timeout
        self._mozmill = mozmill.MozMill.create(**mozmill_args)

        self.installed_addons = None
        self._mozmill.add_listener(self.addons_event, eventType='mozmill.installedAddons')

        self.graphics = None
        self._mozmill.add_listener(self.graphics_event, eventType='mozmill.graphics')

        if self.options.screenshot_path:
            path = os.path.abspath(self.options.screenshot_path)
            if not os.path.isdir(path):
                os.makedirs(path)
            self._mozmill.persisted["screenshotPath"] = path

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
        manifest = manifestparser.TestManifest(
            manifests=[os.path.join(self.repository_path, self.manifest_path)],
            strict=False)

        self._mozmill.run(manifest.tests)

        # Whenever a test fails it has to be marked, so we quit with the correct exit code
        self.last_failed_tests = self.last_failed_tests or self._mozmill.results.fails

        self._generate_custom_report()
        self.testrun_index += 1

    def run(self):
        """ Run tests for all specified builds. """

        # If no binaries have been specified we cancel the test-run
        if not self.binaries:
            print "*** No builds have been specified. Use --help to see all options."
            return

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
                    self._mozmill.results.finish(self._mozmill.handlers)
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


class FunctionalTestRun(TestRun):
    """ Class to execute a Firefox functional test-run. """

    report_type = "firefox-functional"
    report_version = "2.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

    def run_tests(self):
        """ Execute the functional tests. """

        try:
            self.manifest_path = os.path.join('tests',
                                              'functional',
                                              'manifest.ini')
            TestRun.run_tests(self)
        except Exception, e:
            raise


def functional_cli():
    try:
        FunctionalTestRun().run()
    except TestFailedException:
        sys.exit(2)
