# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from setuptools import setup, find_packages

try:
    here = os.path.dirname(os.path.abspath(__file__))
    description = file(os.path.join(here, 'README.md')).read()
except IOError:
    description = None

NAME = 'mozmill-automation'
VERSION = '2.0.10.2'

deps = ['mercurial == 2.6.2',
        'mozfile == 1.1',
        'mozinfo == 0.7',
        'mozinstall == 1.11',
        'mozmill == 2.0.10.2',
        'mozversion == 1.0',

        # It is not considered best practice to use install_requires to pin
        # dependencies to specific versions, or to specify sub-dependencies
        # (i.e. dependencies of your dependencies).
        #
        # But we have to do so to ensure to not run into dep conflicts. More
        # details see bug 1196122.
        'mozdevice < 0.46',
        'mozlog >= 2.0, <3.0',
        'moznetwork < 0.27',
        ]

setup(name=NAME,
      version=VERSION,
      description="Automation scripts for Mozmill test execution",
      long_description=description,
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Environment :: Console',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
                   'Natural Language :: English',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   ],
      keywords='mozilla',
      author='Mozilla Automation and Tools team',
      author_email='tools@lists.mozilla.org',
      url='https://github.com/mozilla/mozmill-automation',
      license='MPL 2.0',
      packages=find_packages(exclude=['legacy']),
      include_package_data=True,
      zip_safe=False,
      install_requires=deps,
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      testrun_addons = mozmill_automation:addons_cli
      testrun_endurance = mozmill_automation:endurance_cli
      testrun_functional = mozmill_automation:functional_cli
      testrun_l10n = mozmill_automation:l10n_cli
      testrun_remote = mozmill_automation:remote_cli
      testrun_update = mozmill_automation:update_cli
      """,
      )
