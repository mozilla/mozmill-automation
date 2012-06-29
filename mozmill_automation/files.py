# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import json
import os

import errors


class JSONFile:
    """Class to handle reading and writing of JSON files."""

    def __init__(self, filename):
        self.filename = os.path.abspath(filename)

    def read(self):
        if not os.path.isfile(self.filename):
            raise errors.NotFoundException('Specified file cannot be found.',
                                           self.filename)

        try:
            f = open(self.filename, 'r')
            return json.loads(f.read())
        finally:
            f.close()

    def write(self, data):
        try:
            folder = os.path.dirname(self.filename)
            if not os.path.exists(folder):
                os.makedirs(folder)
            f = open(self.filename, 'w')
            f.write(json.dumps(data))
        finally:
            f.close()


def get_unique_filename(filename, start_index):
    (basename, ext) = os.path.splitext(filename)

    return '%s_%i%s' % (basename, start_index, ext)
