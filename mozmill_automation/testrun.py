# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import ConfigParser
import os
import optparse
import re
import shutil
import sys
import tempfile
import time
import traceback
import urllib

import manifestparser
import mozinfo
import mozinstall
import mozmill
import mozmill.logger

import application
import errors
import files
import reports
import repository


MOZMILL_TESTS_REPOSITORIES = {
    'firefox' : "http://hg.mozilla.org/qa/mozmill-tests",
    'thunderbird' : "http://hg.mozilla.org/users/bugzilla_standard8.plus.com/qa-tests/",
}


class TestRun(object):
    """Base class to execute a Mozmill test-run"""

    def __init__(self, args=sys.argv[1:], debug=False, manifest_path=None,
                 timeout=None):

        usage = "usage: %prog [options] binary"
        parser = optparse.OptionParser(usage=usage)
        self.add_options(parser)
        self.options, self.args = parser.parse_args(args)

        if len(self.args) != 1:
            parser.error("Exactly one binary has to be specified.")

        self.binary = self.args[0]
        self.debug = debug
        self.timeout = timeout
        self.manifest_path = manifest_path
        self.persisted = {}

        # default listeners
        self.listeners = [(self.graphics_event, 'mozmill.graphics')]

        url = self.options.repository_url if self.options.repository_url \
            else MOZMILL_TESTS_REPOSITORIES[self.options.application]
        self.repository = repository.MercurialRepository(url)

        self.addon_list = []
        self.downloaded_addons = []
        self.testrun_index = 0

        self.last_failed_tests = None

    def add_options(self, parser):
        """add options to the parser"""
        parser.add_option("-a", "--addons",
                          dest="addons",
                          action="append",
                          metavar="ADDONS",
                          help="add-ons to be installed")
        parser.add_option("--application",
                          dest="application",
                          default="firefox",
                          choices=["firefox", "thunderbird"],
                          metavar="APPLICATION",
                          help="application name [default: %default]")
        parser.add_option("--junit",
                          dest="junit_file",
                          metavar="PATH",
                          help="JUnit XML style report file")
        parser.add_option("--report",
                          dest="report_url",
                          metavar="URL",
                          help="send results to the report server")
        parser.add_option("--repository",
                          dest="repository_url",
                          metavar="URL",
                          help="URL of a custom repository")
        parser.add_option("--restart",
                          dest="restart",
                          default=False,
                          action="store_true",
                          help="restart the application between tests")
        parser.add_option("--screenshot-path",
                          dest="screenshot_path",
                          metavar="PATH",
                          help="path to use for screenshots")
        parser.add_option("--tag",
                          dest="tags",
                          action="append",
                          metavar="TAG",
                          help="Tag to apply to the report")

        mozmill = optparse.OptionGroup(parser, "Mozmill options")
        mozmill.add_option("-l", "--logfile",
                          dest="logfile",
                          metavar="PATH",
                          help="path to log file")
        mozmill.add_option('-p', "--profile",
                          dest="profile",
                          metavar="PATH",
                          help="path to the profile")
        parser.add_option_group(mozmill)

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

    def prepare_application(self, binary):
        # Prepare the binary for the test run
        if mozinstall.is_installer(self.binary):
            install_path = tempfile.mkdtemp(".binary")

            print "Install build: %s" % self.binary
            self._folder = mozinstall.install(self.binary, install_path)
            self._application = mozinstall.get_binary(self._folder,
                                                      self.options.application)
        else:
            if os.path.isdir(self.binary):
                self._folder = self.binary
            else:
                if sys.platform == "darwin":
                    # Ensure that self._folder is the app bundle on OS X
                    p = re.compile('.*\.app/')
                    self._folder = p.search(self.binary).group()
                else:
                    self._folder = os.path.dirname(self.binary)

            self._application = mozinstall.get_binary(self._folder,
                                                      self.options.application)

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
        manifest = manifestparser.TestManifest(
            manifests=[os.path.join(self.repository.path, self.manifest_path)],
            strict=False)

        tests = manifest.active_tests(**mozinfo.info)

        # instantiate handlers
        logger = mozmill.logger.LoggerListener(log_file=self.options.logfile,
                                               console_level=self.debug and 'DEBUG' or 'INFO',
                                               file_level=self.debug and 'DEBUG' or 'INFO',
                                               debug=self.debug)
        handlers = [logger]
        if self.options.report_url:
            self.report = reports.DashboardReport(self.options.report_url, self)
            handlers.append(self.report)

        if self.options.junit_file:
            filename = files.get_unique_filename(self.options.junit_file,
                                                 self.testrun_index)
            self.junit_report = reports.JUnitReport(filename, self)
            handlers.append(self.junit_report)

        # instantiate MozMill
        profile_args = dict(addons=self.addon_list)
        runner_args = dict(binary=self._application)
        mozmill_args = dict(app=self.options.application,
                            handlers=handlers,
                            profile_args=profile_args,
                            runner_args=runner_args)
        if self.timeout:
            mozmill_args['jsbridge_timeout'] = self.timeout
        self._mozmill = mozmill.MozMill.create(**mozmill_args)

        self.graphics = None

        for listener in self.listeners:
            self._mozmill.add_listener(listener[0], eventType=listener[1])

        self._mozmill.persisted.update(self.persisted)
        self._mozmill.run(tests, self.options.restart)

        self.results = self._mozmill.finish()

        # Whenever a test fails it has to be marked, so we quit with the correct exit code
        self.last_failed_tests = self.last_failed_tests or self.results.fails

        self.testrun_index += 1

    def run(self):
        """ Run tests for all specified builds. """

        try:
            self.prepare_application(self.binary)

            ini = application.ApplicationIni(self._application)
            print '*** Application: %s %s' % (
                ini.get('App', 'Name'),
                ini.get('App', 'Version'))

            # Print platform details
            print '*** Platform: %s %s %sbit' % (
                str(mozinfo.os).capitalize(),
                mozinfo.version,
                mozinfo.bits)

            # XXX: mktemp is marked as deprecated but lets use it because with
            # older versions of Mercurial the target folder should not exist.
            path = tempfile.mktemp(".mozmill-tests")
            print "*** Cloning test repository to '%s'" % path
            self.repository.clone(path)

            # Update the mozmill-test repository to match the Gecko branch
            app_repository_url = ini.get('App', 'SourceRepository')
            branch_name = application.get_mozmill_tests_branch(app_repository_url)

            print "*** Updating branch of test repository to '%s'" % branch_name
            self.repository.update(branch_name)

            if self.options.addons:
                self.prepare_addons()

            if self.options.screenshot_path:
                path = os.path.abspath(self.options.screenshot_path)
                if not os.path.isdir(path):
                    os.makedirs(path)
                self.persisted["screenshotPath"] = path

            self.run_tests()

        except Exception, e:
            exception_type, exception, tb = sys.exc_info()
            traceback.print_exception(exception_type, exception, tb)

        finally:
            # Remove the build when it has been installed before
            if mozinstall.is_installer(self.binary):
                print "Uninstall build: %s" % self._folder
                mozinstall.uninstall(self._folder)

            self.remove_downloaded_addons()

            # Remove the temporarily cloned repository
            print "*** Removing test repository '%s'" % self.repository.path
            self.repository.remove()

            # If a test has been failed ensure that we exit with status 2
            if self.last_failed_tests:
                raise errors.TestFailedException()


class AddonsTestRun(TestRun):
    """Class to execute an add-ons test-run"""

    report_type = "firefox-addons"
    report_version = "1.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

        self.target_addon = None

    def add_options(self, parser):
        addons = optparse.OptionGroup(parser, "Add-ons options")
        addons.add_option("--target-addons",
                          dest="target_addons",
                          default=[],
                          metavar="ID",
                          help="list of add-ons to test from the mozmill-test repository, "
                               "e.g. ide@seleniumhq.org")
        addons.add_option("--with-untrusted",
                          dest="with_untrusted",
                          default=False,
                          action="store_true",
                          help="run tests for add-ons which are not stored on AMO")
        parser.add_option_group(addons)

        TestRun.add_options(self, parser)

    def get_all_addons(self):
        """ Retrieves all add-ons inside the "addons" folder. """

        path = os.path.join(self.repository.path, "tests", "addons")
        return [entry for entry in os.listdir(path)
                      if os.path.isdir(os.path.join(path, entry))]

    def get_download_url(self):
        """ Read the addon.ini file and get the URL of the XPI. """

        filename = None

        # Get the platform the script is running on
        if sys.platform in ("cygwin", "win32"):
            platform = "win"
        elif sys.platform in ("darwin"):
            platform = "mac"
        elif sys.platform in ("linux2", "sunos5"):
            platform = "linux"
        else:
            platform = None

        try:
            filename = os.path.join(self.repository.path, self._addon_path, "addon.ini")
            config = ConfigParser.RawConfigParser()
            config.read(filename)

            return config.get("download", platform)
        except Exception, e:
            raise errors.NotFoundException('Could not read URL settings', filename)

    def run_tests(self):
        """ Execute the normal and restart tests in sequence. """

        # If no target add-ons have been specified get all available add-on tests
        if not self.options.target_addons:
            self.options.target_addons = self.get_all_addons()

        for addon in self.options.target_addons:
            try:
                # Resets state of target addon field for every iteration
                self.target_addon = None

                # Get the download URL
                self._addon_path = os.path.join('tests', 'addons', addon)

                try:
                    url = self.get_download_url()
                except errors.NotFoundException, e:
                    print str(e)
                    continue

                # Check if the download URL is trusted and we can proceed
                if not "addons.mozilla.org" in url and not self.options.with_untrusted:
                    print "*** Download URL for '%s' is not trusted." % os.path.basename(url)
                    print "*** Use --with-untrusted to force testing this add-on."
                    continue

                # Download the add-on
                self.target_addon = self.download_addon(url, tempfile.gettempdir())

                # Run normal tests if some exist
                try:
                    self.manifest_path = os.path.join(self._addon_path,
                                                      'tests', 'manifest.ini')
                    self.restart_tests = False
                    self.addon_list.append(self.target_addon)
                    TestRun.run_tests(self)
                except Exception, e:
                    print str(e)
                    self.last_exception = e
                finally:
                    self.addon_list.remove(self.target_addon)

                # Run restart tests if some exist
                try:
                    self.manifest_path = os.path.join(self._addon_path,
                                                      'restartTests', 'manifest.ini')
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
                if self.target_addon:
                    try:
                        # Remove downloaded add-on
                        if os.path.exists(self.target_addon):
                            print "*** Removing target add-on '%s'." % self.target_addon
                            os.remove(self.target_addon)
                    except:
                        print "*** Failed to remove target add-on '%s'." % self.target_addon


class EnduranceTestRun(TestRun):
    """Class to execute an endurance test-run"""

    report_type = "firefox-endurance"
    report_version = "1.2"

    def __init__(self, *args, **kwargs):

        TestRun.__init__(self, *args, **kwargs)

        self.delay = "%.0d" % (self.options.delay * 1000)
        self.timeout = self.options.delay + 60
        self.options.restart = self.options.no_restart

        self.listeners.append((self.endurance_event, 'mozmill.enduranceResults'))


    def add_options(self, parser):
        endurance = optparse.OptionGroup(parser, "Endurance options")
        endurance.add_option("--delay",
                             dest="delay",
                             default=5,
                             type="float",
                             metavar="DELAY",
                             help="seconds to wait before each iteration "
                                  "[default: %default]")
        endurance.add_option("--entities",
                             dest="entities",
                             default=1,
                             type="int",
                             metavar="ENTITIES",
                             help="number of entities to create within a test "
                                  "snippet [default: %default]")
        endurance.add_option("--iterations",
                             dest="iterations",
                             default=1,
                             type="int",
                             metavar="ITERATIONS",
                             help="number of iterations to repeat each test "
                                  "snippet [default: %default]")
        endurance.add_option("--no-restart",
                              dest="no_restart",
                              default=True,
                              action="store_false",
                              help="don't restart the application between "
                                   "tests [default: %default]")
        endurance.add_option("--reserved",
                             dest="reserved",
                             type="string",
                             metavar="RESERVED",
                             help="specify a reserved test to run")

        parser.add_option_group(endurance)

        TestRun.add_options(self, parser)

    def endurance_event(self, obj):
        self.endurance_results.append(obj)

    def run_tests(self):
        """ Execute the endurance tests in sequence. """

        self.endurance_results = []
        self.persisted['endurance'] = {'delay': self.delay,
                                       'iterations': self.options.iterations,
                                       'entities': self.options.entities,
                                       'restart': self.options.restart}

        self.manifest_path = os.path.join('tests', 'endurance')
        if not self.options.reserved:
            self.manifest_path = os.path.join(self.manifest_path,
                                              "manifest.ini")
        else:
            self.manifest_path = os.path.join(self.manifest_path,
                                              'reserved',
                                              self.options.reserved + ".ini")
        TestRun.run_tests(self)


class FunctionalTestRun(TestRun):
    """Class to execute a functional test-run"""

    report_type = "firefox-functional"
    report_version = "2.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

    def run_tests(self):
        """ Execute the functional tests. """

        self.manifest_path = os.path.join('tests',
                                          'functional',
                                          'manifest.ini')
        TestRun.run_tests(self)


class L10nTestRun(TestRun):
    """Class to execute a l10n test-run"""

    report_type = "firefox-l10n"
    report_version = "1.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

    def run_tests(self):
        """ Execute the existent l10n tests in sequence. """

        self.manifest_path = os.path.join('tests',
                                          'l10n',
                                          'manifest.ini')
        TestRun.run_tests(self)


class RemoteTestRun(TestRun):
    """Class to execute a remote testrun"""

    report_type = "firefox-remote"
    report_version = "1.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)

    def run_tests(self):
        """ Execute the normal and restart tests in sequence. """

        self.manifest_path = os.path.join('tests',
                                          'remote',
                                          'manifest.ini')
        TestRun.run_tests(self)


class UpdateTestRun(TestRun):
    """Class to execute a software update testrun"""

    report_type = "firefox-update"
    report_version = "1.0"

    def __init__(self, *args, **kwargs):
        TestRun.__init__(self, *args, **kwargs)
        self.options.restart = True

        self.results = [ ]

        # Download of updates normally take longer than 60 seconds
        # Soft-timeout is 360s so make the hard-kill timeout 5s longer
        self.timeout = 365

    def add_options(self, parser):
        update = optparse.OptionGroup(parser, "Update options")
        update.add_option("--channel",
                          dest="channel",
                          metavar="CHANNEL",
                          help="update channel")
        update.add_option("--no-fallback",
                          dest="no_fallback",
                          default=False,
                          action="store_true",
                          help="do not perform a fallback update")
        update.add_option("--target-buildid",
                          dest="target_buildid",
                          metavar="TARGET_ID",
                          help="expected build id of the updated build")
        parser.add_option_group(update)

        TestRun.add_options(self, parser)

    def prepare_application(self, binary):
        TestRun.prepare_application(self, binary)

        # If a fallback update has to be performed, create a second copy
        # of the application to avoid running the installer twice
        if not self.options.no_fallback:
            self._backup_folder = tempfile.mkdtemp(".binary_backup")

            print "Create backup: %s" % self._backup_folder
            shutil.rmtree(self._backup_folder)
            shutil.copytree(self._folder, self._backup_folder)

    def prepare_channel(self):
        update_channel = application.UpdateChannel(self._application)

        if not self.options.channel:
            self.channel = update_channel.channel
        else:
            update_channel.channel = self.options.channel
            self.channel = self.options.channel

    def restore_application(self):
        """ Restores the backup of the application binary. """
        timeout = time.time() + 15

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

        self.prepare_channel()

        self.persisted["channel"] = self.channel
        if self.options.target_buildid:
            self.persisted["targetBuildID"] = self.options.target_buildid

        # Run direct update test
        self.run_update_tests(False)

        # Run fallback update test
        if not self.options.no_fallback:
            # Restore backup of original application version first
            self.restore_application()

            self.run_update_tests(True)

    def run_update_tests(self, is_fallback):
        try:
            type = 'testFallbackUpdate' if is_fallback else 'testDirectUpdate'
            self.manifest_path = os.path.join('tests',
                                              'update',
                                              type,
                                              'manifest.ini')
            TestRun.run_tests(self)
        except Exception, e:
            print "Execution of test-run aborted: %s" % str(e)
        finally:
            try:
                path = self._mozmill.persisted["updateStagingPath"]
                print "Remove updates staging folder: %s" % path
                shutil.rmtree(path)
            except Exception, e:
                print "Failed to remove the update staging folder: " + str(e)
                self.last_exception = e


def exec_testrun(cls):
    try:
        cls().run()
    except errors.TestFailedException:
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
