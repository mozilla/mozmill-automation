# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mozinfo
import os
import re
import shutil
import urlparse

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
            name = urlparse.urlparse(self.url).path.rstrip('/').rsplit('/')[-1]
            self.path = os.path.join(os.getcwd(), name)

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
