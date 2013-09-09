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
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Henrik Skupin <hskupin@mozilla.com>
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

import mozinfo
import os
import re
import shutil

import process


class MercurialRepository(object):
    """Class to work with a Mercurial repository"""

    def __init__(self, url, path=None, command=None):
        self.url = url

        if command:
            self.command = command
        else:
            # As long as we use the mercurial-python version there is no hg.exe
            # available and we have to fallback to the batch file
            self.command = 'hg.bat' if mozinfo.os == 'win' else 'hg'

        if path:
            self.path = os.path.abspath(path)
        else:
            # If no local path has been specified we generate it from the
            # current working directory and the name of the remote repository
            self.path = os.path.join(os.getcwd(), os.path.basename(url))

    def _exec(self, arguments, is_cloning=False):
        """Execute the given hg command and return the output"""

        command = [self.command]
        command.extend(arguments)
        command.extend(['--cwd', os.getcwd() if is_cloning else self.path])

        return process.check_output(command).strip()

    @property
    def exists(self):
        """Check if the local copy of the repository exists"""

        return os.path.exists(os.path.join(self.path, '.hg'))

    def get_branch(self):
        """Return the selected branch"""

        return self._exec(['branch'])

    def set_branch(self, name):
        """Updates the code to the specified branch."""

        self.update(name)

    branch = property(get_branch, set_branch, None)

    @property
    def changeset(self):
        """Get the rev for the current changeset"""

        return self._exec(['parent', '--template', '{node}'])

    def clone(self, path=None):
        """Clone the remote repository to the local path"""

        if path:
            # A new destination has been specified
            self.path = os.path.abspath(path)

        self._exec(['clone', self.url, self.path], True)

    def update(self, branch=None):
        """ Update the local repository for recent changes. """

        if branch is None:
            branch = self.branch

        self._exec(['update', '-C', branch])

    def remove(self):
        """Remove the repository from the local disk"""

        shutil.rmtree(self.path, True)
