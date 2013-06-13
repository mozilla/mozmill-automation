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
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Dave Hunt <dhunt@mozilla.com>
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

from datetime import datetime
import os
import xml.dom.minidom

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class Report(object):
    """ Class to customize the Mozmill report. """

    def __init__(self, raw_report, filename):
        self.raw_report = raw_report
        self.filename = filename
        self._write()

    def _generate(self):
        # Override this method to generate a custom report.
        return raw_report

    def _write(self):
        report = self._generate()
        try:
            file = open(self.filename, 'w')
            file.write(report)
            file.close()
        except IOError, e:
            sys.stderr.write('Failed to write report to file: %s\n' % e)


class JUnitReport(Report):

    def _generate(self):
        testcases = []

        report_type = str(self.raw_report['report_type'])
        time_start = datetime.strptime(self.raw_report['time_start'], DATETIME_FORMAT)
        time_end = datetime.strptime(self.raw_report['time_end'], DATETIME_FORMAT)

        doc = xml.dom.minidom.Document()
        testsuite_element = doc.createElement("testsuite")
        testsuite_element.setAttribute("name", report_type)
        testsuite_element.setAttribute("errors", "0")
        testsuite_element.setAttribute("failures", str(self.raw_report['tests_failed']))
        testsuite_element.setAttribute("skips", str(self.raw_report['tests_skipped']))
        testsuite_element.setAttribute("tests", str(len(self.raw_report['results'])))
        testsuite_element.setAttribute("time", str((time_end - time_start).seconds))

        for result in self.raw_report['results']:
            filename = result['filename']
            root_path = '/'.join(['tests', report_type.split('firefox-')[1]])

            # replace backslashes with forward slashes
            filename = filename.replace('\\', '/')

            # strip temporary and common path elements, and strip trailing forward slash
            class_name = filename.partition(root_path)[2].lstrip('/')

            # strip the file extension
            class_name = os.path.splitext(class_name)[0]

            # replace periods with underscore to avoid them being interpreted as package seperators
            class_name = class_name.replace('.', '_')

            # replace path separators with periods to give implied package hierarchy
            class_name = class_name.replace('/', '.')

            testcase_element = doc.createElement("testcase")
            testcase_element.setAttribute("classname", str(class_name))
            testcase_element.setAttribute("name", str(result['name']).rpartition('::')[2])
            testcase_element.setAttribute("time", "0")  # add test duration. See bug 583834
            if 'skipped' in result and result['skipped']:
                skipped_element = doc.createElement("skipped")
                skipped_element.setAttribute('message', str(result['skipped_reason']))
                skipped_element.appendChild(doc.createTextNode(str(result['skipped_reason'])))
                testcase_element.appendChild(skipped_element)
            elif result['failed']:
                # If result['fails'] is not a list, make it a list of one
                result_failures = result['fails']
                if not isinstance(result_failures, list):
                    result_failures = [result_failures]

                failures = []
                for failure in result_failures:
                    # If the failure is a dict then return the appropriate exception/failure item or return an empty dict
                    failure_data = isinstance(failure, dict) and (
                                       'exception' in failure and failure['exception'] or
                                       'fail' in failure and failure['fail']) or {}
                    message = failure_data.get('message', 'Unknown failure.')
                    stack = failure_data.get('stack', 'Stack unavailable.')
                    failures.append({'message': message, 'stack': stack})

                if len(failures) == 1:
                    (message, body) = failures[0].values()
                else:
                    message = '%d failures' % len(failures)
                    body = '\n\n'.join(['Message: %s\nStack: %s' % (failure['message'], failure['stack']) for failure in failures])
                failed_element = doc.createElement("failure")
                failed_element.setAttribute('message', unicode(message).encode('ascii', 'xmlcharrefreplace'))
                failed_element.appendChild(doc.createTextNode(unicode(body).encode('ascii', 'xmlcharrefreplace')))
                testcase_element.appendChild(failed_element)
            testsuite_element.appendChild(testcase_element)

        doc.appendChild(testsuite_element)
        return doc.toxml(encoding='utf-8')
