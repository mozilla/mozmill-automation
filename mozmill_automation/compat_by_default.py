# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import copy
import shutil
import sys
import tempfile
import optparse
from urlparse import urlsplit

from mozdownload import ReleaseScraper

import application
import errors
from install import Installer
from json_file import JSONFile
from testrun import *


class CompatibleByDefault:
    """Class to run the add-ons compatible by default tests."""

    def __init__(self, config_file, repository=None):
        self._config = JSONFile(config_file).read()
        self._repository = repository

        self.staging_path = os.path.abspath(self._config['settings']['staging_path'])


    @property
    def platform(self):
        if sys.platform in ['darwin']:
            return sys.platform
        elif sys.platform in ['win32', 'cygwin']:
            return 'winnt'
        elif sys.platform in ['linux2', 'linux3']:
            return 'linux'


    def _run_tests(self, build, default_testrun_options):
        """Execute the tests for the given build"""

        cur_index = 0
        firstrun = True
        addons = self._config['addons']

        # Iterate in chunks over all extended add-ons
        while cur_index < len(addons['extended']):
            try:
                addon_set = copy.copy(addons['default'])
                if firstrun:
                    # For the first run we do only install the default add-ons
                    firstrun = False
                else:
                    # Otherwise retrieve the next number of extended add-ons
                    max_index = cur_index + self._config['settings']['addons_per_run']
                    addons_extended = addons['extended'][cur_index:max_index]
                    addon_set.extend(addons_extended)
                    cur_index += len(addons_extended)

                # Build testrun options for add-ons to test
                addon_options = [ ]
                tags = [ ]

                for addon in addon_set:
                    addon_options.append('--addons=%s' % addon['local_url'])
                    tags.append('--tag=%s' % addon['name'])

                # Install the specified build so we don't have to do it for
                # each individual testrun.
                install_path = tempfile.mkdtemp('.binary')
                folder = Installer().install(build, install_path)
                binary = application.get_binary('firefox', folder)

                # Setup all necessary testrun options to test the build
                testrun_options = copy.copy(default_testrun_options)
                testrun_options.append(binary)
                testrun_options.extend(addon_options)
                testrun_options.extend(tags)

                # Setup profile for testing
                profile_path = tempfile.mkdtemp(suffix='profile')
                testrun_options.append('--profile=' + profile_path)

                # Execute testruns
                self.execute_testrun(EnduranceTestRun, testrun_options)
                self.execute_testrun(UpdateTestRun, testrun_options, ['--no-fallback'])
                self.execute_testrun(EnduranceTestRun, testrun_options)

                # Ensure to remove the temporarily created profile
                shutil.rmtree(profile_path, True)

            finally:
                install.Installer().uninstall(folder)


    def download_addon(self, url, target_path):
        """Download an add-on given by the URL."""
        try:
            filename = urlsplit(url).path.rsplit('/')[-1]
            target_path = os.path.join(target_path, filename)
            if not os.path.exists(target_path):
                urllib.urlretrieve(url, target_path)

            return target_path
        except Exception, e:
            raise errors.NotFoundException("Add-on cannot be downloaded: %s" % str(e),
                                           url)


    def execute_testrun(self, testrun, options, extra_options=None):
        """Execute the specified testrun with the given options."""

        testrun_options = copy.copy(options)
        if isinstance(extra_options, list):
            testrun_options.extend(extra_options)

        try:
            testrun(testrun_options).run()
        except Exception, e:
            self._exceptions.append(e)


    def run(self):
        """Execute the compatible by default testrun."""

        # Stage builds and add-ons required by the testrun
        self.stage_addons()
        self.stage_builds()

        # Setup the default options for the testruns from the config
        config_options = self._config['settings']['testrun_options']
        default_testrun_options = [option for option in config_options]

        self._exceptions = [ ]
        for build in self._local_builds:
            self._run_tests(build, default_testrun_options)

        # Always clean-up the staging folder
        print "Clean-up staging folder."
        shutil.rmtree(self.staging_path, True)

        # If test failures have been reported simply throw the last raised
        # exception. It also ensures a correct exit code.
        if self._exceptions:
            raise self._exceptions[-1]


    def stage_addons(self):
        """Stage add-ons under test as specified in the config file."""

        if not os.path.exists(self.staging_path):
            os.mkdir(self.staging_path)

        for addon_type in ['default', 'extended']:
            removable_addons = [ ]

            # Iterate over each add-on and download if it matches the platform.
            for addon in self._config['addons'][addon_type]:
                if 'platforms' in addon and not self.platform in addon['platforms']:
                    print 'Skip: Add-on "%s" not available on %s' % (addon['name'],
                                                                     self.platform)
                    removable_addons.append(addon)
                    continue

                print 'Staging add-on "%s" (%s)' % (addon['name'], addon['url'])
                addon['local_url'] = self.download_addon(addon['url'],
                                                         self.staging_path)

            # Remove not testable add-ons
            for addon in removable_addons:
                self._config['addons'][addon_type].remove(addon)


    def stage_builds(self):
        self._local_builds = [ ]

        for build in self._config['settings']['builds']:
            scraper = ReleaseScraper(directory=self.staging_path,
                                     version=build)
            scraper.download()
            self._local_builds.append(scraper.target)


def compat_addons_cli():
    usage = "usage: %prog [options] config-file"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--repository',
                      dest='repository',
                      help='URL of a remote or local mozmill-test repository.')
    (options, args) = parser.parse_args()

    if not len(args) is 1:
        parser.error('A configuration file has to be specified.')

    cbd = CompatibleByDefault(args[0], options.repository)
    cbd.run()
