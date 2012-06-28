# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mozmill.report import Report

class DashboardReport(Report):

    def __init__(self, report, testrun):
        Report.__init__(self, report)
        self.testrun = testrun

    def get_report(self, results):
        """ Customize the report data. """
        report = Report.get_report(self, results)

        report['report_type'] = self.testrun.report_type
        report['report_version'] = self.testrun.report_version
        report['tests_repository'] = self.testrun._repository.url
        report['tests_changeset'] = self.testrun._repository.changeset

        if self.testrun.options.tags:
            report['tags'] = self.testrun.options.tags

        # Optional information received by Python callbacks
        if self.testrun.graphics:
            report['system_info']['graphics'] = self.testrun.graphics
        return report
