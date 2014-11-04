# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import re

import mozinfo


def get_mozmill_tests_branch(gecko_branch):
    """ Identify the mozmill-tests branch from the application branch. """

    # If no branch information is available assume we have a release build.
    # All binaries on Ubuntu and maybe other distributions don't have it set.
    if not gecko_branch:
        return 'mozilla-release'

    # Retrieve the name of the repository
    branch = re.search('.*/([\S\.]+$)', gecko_branch).group(1)

    # Supported branches: mozilla-aurora, mozilla-beta, mozilla-release,
    #                     mozilla-esr*
    # All other branches (mozilla-central, mozilla-inbound, ux etc.)
    # should fallback to the 'default' branch
    if not re.match(r'.*/releases/', gecko_branch):
        branch = 'default'

    return branch


def is_application(path, application):
    """Check if the path is a supported application"""
    if path.endswith('.app'):
        path = os.path.join(path, 'Contents', 'MacOS')
    else:
        path = os.path.dirname(path)

    if mozinfo.isWin:
        application += '.exe'

    return os.path.exists(os.path.join(path, application))


def is_installer(path, application):
    """ Checks if a binary is an installer. """
    try:
        if (os.path.splitext(path)[1] in (".bz2", ".dmg", ".exe")):
            return os.path.basename(path) not in (application + ".exe")
        else:
            return False
    except Exception:
        return False
