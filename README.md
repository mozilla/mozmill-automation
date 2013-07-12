# Mozmill Automation
With the mozmill-automation scripts the [automation development team][team]
at [Mozilla][mozilla] runs UI and integration tests for Firefox.

For more information see our [project page][project] for automation
related topics.

[team]: https://wiki.mozilla.org/Auto-tools/Automation_Development/
[mozilla]: http://www.mozilla.org/
[project]: https://wiki.mozilla.org/Auto-tools/Automation_Development/Projects/Mozmill_Automation

## Installation
The scripts can be installed by running the following commands:

    python setup.py develop
    pip install -r requirements.txt

## Addons
The `testrun_addons` script executes available Mozmill tests for add-ons,
which should usually be hosted at http://addons.mozilla.org.

The `testrun_compat_addons` script is a special testrun to execute add-on
compatibility tests for Firefox, which ensures that major add-ons are still
working as expected for a new major release of Firefox.

## Endurance
The `testrun_endurance` script executes the endurance tests for Firefox,
which are long running tests to measure the memory usage and performance of
Firefox.

## Functional
The `testrun_functional` script executes functional tests for Firefox, which
are UI and integration tests, and are necessary for Mozilla QA for signing
off from testing a new Firefox release.

## Localization
The `testrun_l10n` script executes localization tests for Firefox, which are
used to check that localized builds of Firefox are working as expected in
terms of accessibility and graphical output.

## Remote
The `testrun_remote` script executes remote tests for Firefox, which are
similar to the functional tests but make use of remote test cases to prove
the functionality against real web sites.

## Update
The `testrun_update` script executes update tests for Firefox, which ensures
that an update is always correctly performed for Firefox.

When running update tests, you have the option of providing an update
channel. The valid update channels are:

* nightly
* nightlytest
* aurora
* auroratest
* beta
* betatest
* release
* releasetest
* esr
* esrtest
* esr[VERSION]-nightly (for example esr17-nightly)
