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


class ApplicationIni(object):
    """ Class to retrieve entries from the application.ini file. """

    def __init__(self, binary):
        self.ini_file = os.path.join(os.path.dirname(binary),
                                     'application.ini')

        self.config = ConfigParser.RawConfigParser()
        self.config.read(self.ini_file)

    def get(self, section, option):
        """ Retrieve the value of an entry. """
        return self.config.get(section, option)


class UpdateChannel(object):
    """ Class to handle the update channel. """

    pref_regex = "(?<=pref\(\"app\.update\.channel\", \")([^\"]*)(?=\"\))"

    def __init__(self, binary, *args, **kwargs):
        self.folder = os.path.dirname(binary)

    @property
    def channel_prefs_path(self):
        """ Returns the channel prefs path. """
        for pref_folder in ('preferences', 'pref'):
            pref_path = os.path.join(self.folder,
                                     'defaults',
                                     pref_folder,
                                     'channel-prefs.js')
            if os.path.exists(pref_path):
                return pref_path
        raise errors.NotFoundException('Channel prefs not found.', pref_path)

    def _get_channel(self):
        """ Returns the current update channel. """
        try:
            file = open(self.channel_prefs_path, "r")
        except IOError:
            raise
        else:
            content = file.read()
            file.close()

            result = re.search(self.pref_regex, content)
            return result.group(0)

    def _set_channel(self, value):
        """ Sets the update channel. """

        print "Setting update channel to '%s'..." % value

        try:
            file = open(self.channel_prefs_path, "r")
        except IOError:
            raise
        else:
            # Replace the current update channel with the specified one
            content = file.read()
            file.close()

            # Replace the current channel with the specified one
            result = re.sub(self.pref_regex, value, content)

            try:
                file = open(self.channel_prefs_path, "w")
            except IOError:
                raise
            else:
                file.write(result)
                file.close()

                # Check that the correct channel has been set
                if value != self.channel:
                    raise Exception("Update channel wasn't set correctly.")

    channel = property(_get_channel, _set_channel, None)
