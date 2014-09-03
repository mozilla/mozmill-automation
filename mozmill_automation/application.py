# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import ConfigParser
import os
import re
import sys

import errors


def get_bin_folder(app_folder):
    """ Returns the folder which contains the binaries of the application. """
    if sys.platform in ("darwin"):
        app_folder = os.path.join(app_folder, 'Contents', 'MacOS')
    return app_folder


def get_mozmill_tests_branch(gecko_branch):
    """ Identify the mozmill-tests branch from the application branch. """

    # Retrieve the name of the repository
    branch = re.search('.*/([\S\.]+$)', gecko_branch).group(1)

    # Supported branches: mozilla-aurora, mozilla-beta, mozilla-release, mozilla-esr*
    # All other branches (mozilla-central, mozilla-inbound, birch, elm, oak etc.) should fallback to the 'default' branch
    # This will work with Firefox and Thunderbird
    if not re.match(r'.*/releases/', gecko_branch):
        branch = "default"

    return branch


def is_app_folder(path):
    """ Checks if the folder is an application folder. """
    if sys.platform != "darwin":
        path = os.path.dirname(path)

    file = os.path.join(get_bin_folder(path),
                        "application.ini")

    return os.path.exists(file)


def is_installer(path, application):
    """ Checks if a binary is an installer. """
    try:
        if (os.path.splitext(path)[1] in (".bz2", ".dmg", ".exe")):
            return os.path.basename(path) not in (application + ".exe")
        else:
            return False
    except Exception:
        return False


class UpdateSettingsIni(object):
    """ Class to retrieve and set entries in the update-settings.ini file. """

    def __init__(self, binary):
        self.ini_file = os.path.join(os.path.dirname(binary),
                                     'update-settings.ini')
        self.config = ConfigParser.RawConfigParser()
        self.config.optionxform = str
        self.config.read(self.ini_file)

    def get(self, section, option):
        """ Retrieve the value of an entry. """
        return self.config.get(section, option)

    def set(self, section, option, value):
        """ Set the value of an entry. """
        self.config.set(section, option, value)
        with open(self.ini_file, 'w+') as file:
            self.config.write(file)
