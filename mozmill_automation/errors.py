# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class NotFoundException(Exception):
    """Class for a resource not being found exception."""

    def __init__(self, message, location):
        self.location = location
        Exception.__init__(self, ': '.join([message, location]))

class NotSupportedTestrunException(Exception):
    """Class for a testrun not being supported exception."""

    def __init__(self, testrun):
        Exception.__init__(self, 'Testrun not supported: %s' % testrun.__class__.__name__)

class TestFailedException(Exception):
    """Class for tests failing during a testrun exception"""

    def __init__(self):
        Exception.__init__(self, 'Some tests have been failed.')
