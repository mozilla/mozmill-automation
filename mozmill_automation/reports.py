# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mozmill.report import Report

import testrun


class DashboardReport(Report):

    def __init__(self, report, testrun):
        Report.__init__(self, report)

        self.testrun = testrun

    def _calculate_endurance_stats(self, data, keys):
        """Calculates the min/max/average of each key in data"""

        stats = { }
        for key in keys:
            stats[key] = {'average' : sum(data[key]) / len(data[key]),
                          'min' : min(data[key]),
                          'max' : max(data[key])}
        return stats

    def _populate_endurance_metrics(self, dict, keys, data):
        for key in keys:
            _data = data[key]
            if not isinstance(_data, list):
                _data = [_data]
            dict.setdefault(key, []).extend(_data)

    def get_report(self, results):
        """ Customize the report data. """
        report = Report.get_report(self, results)

        report['report_type'] = self.testrun.report_type
        report['report_version'] = self.testrun.report_version
        report['tests_repository'] = self.testrun._repository.url
        report['tests_changeset'] = self.testrun._repository.changeset
        report['tags'] = self.testrun.options.tags or [ ]

        # Include graphic card related information if present
        if self.testrun.graphics:
            report['system_info']['graphics'] = self.testrun.graphics

        # Endurance Testrun
        if isinstance(self.testrun, testrun.EnduranceTestRun):
            self.get_endurance_results(report, results)

        return report

    def get_endurance_results(self, report, results):
        blacklist = ('timestamp', 'label')
        metrics = []

        report['endurance'] = self.testrun._mozmill.persisted['endurance']
        report['endurance']['results'] = self.testrun.endurance_results

        all_metrics = {}
        for test in report['endurance']['results']:
            test_metrics = {}

            for iteration in test['iterations']:
                iteration_metrics = {}

                for checkpoint in iteration['checkpoints']:
                    if not metrics:
                        metrics = [key for key in checkpoint.keys() if not key in blacklist]

                    self._populate_endurance_metrics(iteration_metrics, metrics, checkpoint)

                iteration['stats'] = self._calculate_endurance_stats(iteration_metrics, metrics)
                self._populate_endurance_metrics(test_metrics, metrics, iteration_metrics)

            test['stats'] = self._calculate_endurance_stats(test_metrics, metrics)
            self._populate_endurance_metrics(all_metrics, metrics, test_metrics)

            report['endurance']['stats'] = self._calculate_endurance_stats(all_metrics, metrics)

        return report
