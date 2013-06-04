#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import optparse

from libs.compat_by_default import CompatibleByDefault


def main():
    usage = "usage: %prog [options] config-file"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--repository',
                      dest='repository',
                      help='URL of a remote or local mozmill-test repository.')
    (options, args) = parser.parse_args()

    if not len(args) is 1:
        parser.error('A configuration file has to be specified.')

    cbd = CompatibleByDefault(args[0], options.repository)
    cbd.run()

if __name__ == '__main__':
    main()
