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
VERSION = '1.5.22.1'

DEPS = [
        'mercurial==2.6.2',
        'mozdownload==1.9',
        'mozmill==1.5.22'
        ]

setup(name=NAME,
      version=VERSION,
      description='Automation scripts for Mozmill test execution',
      long_description=description,
      classifiers=['Environment :: Console',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
                   'Natural Language :: English',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Libraries :: Python Modules'
                   ],
      keywords='mozilla',
      author='Mozilla Automation and Tools team',
      author_email='tools@lists.mozilla.org',
      url='https://github.com/mozilla/mozmill-automation',
      license='MPL 2.0',
      install_requires=DEPS,
      packages=find_packages(exclude=['legacy']),
      package_data={'mozmill_automation': [
          'configs/testrun_compat_addons.json.example'
      ]},
      zip_safe=False,
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      testrun_addons = mozmill_automation:addons_cli
      testrun_endurance = mozmill_automation:endurance_cli
      testrun_functional = mozmill_automation:functional_cli
      testrun_l10n = mozmill_automation:l10n_cli
      testrun_remote = mozmill_automation:remote_cli
      testrun_update = mozmill_automation:update_cli
      testrun_compat_addons = mozmill_automation:compat_addons_cli
      """
      )
