# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import re
import shutil

from mercurial import commands, hg, ui


class Repository(object):
    """ Class to access a Mercurial repository. """

    def __init__(self, url, destination=None):
        self._repository = None
        self._ui = ui.ui()
        self._url = url
        self.destination = destination

    @property
    def exists(self):
        """ Checks if the local copy of the repository exists (read-only). """

        return self._repository is not None

    @property
    def url(self):
        """ Returns the remote location of the repository (read-only). """

        return self._url

    def get_branch(self):
        """ Returns the selected branch. """

        if self._repository:
            return self._repository.dirstate.branch()

    def set_branch(self, value):
        """ Updates the code to the specified branch. """

        self.update(value)

    branch = property(get_branch, set_branch, None)

    def get_changeset(self):
        """ Returns the current changeset of the repository. """

        if self._repository:
            return str(self._repository.parents()[0])

    changeset = property(get_changeset, None, None)

    def get_destination(self):
        """ Returns the local destination of the repository. """

        return self._destination

    def set_destination(self, value):
        """ Sets the location destination of the repository. """

        try:
            self._destination = value
            self._repository = hg.repository(ui.ui(), self._destination)
        except:
            self._repository = None

    destination = property(get_destination, set_destination, None)

    def clone(self, destination=None):
        """ Clone the repository to the local disk. """

        if destination is not None:
            self.destination = destination

        hg.clone(ui.ui(), dict(), self.url, self.destination, True)
        self._repository = hg.repository(ui.ui(), self.destination)

    def identify_branch(self, gecko_branch):
        """ Identify the mozmill-tests branch from the gecko branch. """

        # Retrieve the name of the repository
        branch = re.search('.*/([\S\.]+$)', gecko_branch).group(1)

        # Supported branches: mozilla-aurora, mozilla-beta, mozilla-release, mozilla-esr*
        # All other branches (mozilla-central, mozilla-inbound, birch, elm, oak etc.) should fallback to the 'default' branch
        # This will work with Firefox and Thunderbird
        if not re.match(r'.*/releases/', gecko_branch):
            branch = "default"

        return branch

    def update(self, branch=None):
        """ Update the local repository for recent changes. """

        if branch is None:
            branch = self.branch

        commands.pull(ui.ui(), self._repository, self.url)
        commands.update(ui.ui(), self._repository, None, branch, True)

    def remove(self):
        """ Remove the local version of the repository. """

        shutil.rmtree(self.destination)
        self.destination = None
