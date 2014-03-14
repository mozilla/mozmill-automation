# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class InvalidBinaryException(Exception):
    """Class for a resource not being found exception."""

    def __init__(self, binary):
        Exception.__init__(self, ': '.join(["Invalid binary specified", binary]))


class NotFoundException(Exception):
    """Class for a resource not being found exception."""

    def __init__(self, message, location):
        self.location = location
        Exception.__init__(self, ': '.join([message, location]))

class NotSupportedTestrunException(Exception):
    """Class for a testrun not being supported exception."""

    def __init__(self, testrun):
        Exception.__init__(self, 'Testrun not supported: %s' % testrun.__class__.__name__)

class UpdateSettingsChangedException(Exception):
    """ Exception for not persisted settings."""
    def __init__(self, previous, current):
        Exception.__init__(self, 'Unexpected change to update settings '
                                 'from %s to %s' % (previous, current))

class TestFailedException(Exception):
    """ Exception for failed tests. """
    def __init__(self):
        Exception.__init__(self, "Some tests have failed.")

class TestrunAbortedException(Exception):
    """ Exception for aborted testrun. """
    def __init__(self, testrun):
        Exception.__init__(self, "Testrun aborted: %s" % testrun.__class__.__name__)
