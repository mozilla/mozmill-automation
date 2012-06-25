#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from testrun import *


def main():
    try:
        FunctionalTestRun().run()
    except TestFailedException:
        sys.exit(2)

if __name__ == "__main__":
    main()
