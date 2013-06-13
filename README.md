# mozmill-automation
With the mozmill-automation scripts the [automation development team](https://wiki.mozilla.org/Auto-tools/Automation_Development) at [Mozilla](http://www.mozilla.org/en-US/) runs ui and integration tests for Firefox.

For more information see our project page for automation related topics:
https://wiki.mozilla.org/Auto-tools/Automation_Development/Projects/Mozmill_Automation

## Supported Testruns

### testrun_addons
Script to execute available Mozmill tests for add-ons, which should usually be hosted at http://addons.mozilla.org.

### testrun_endurance
Script to execute endurance tests for Firefox, which are long running tests to measure the memory usage and performance of Firefox.

### testrun_functional
Script to execute functional tests for Firefox, which are ui and integration tests, and are necessary for Mozilla QA for signing of from testing a new Firefox release.

### testrun_l10n
Script to execute localization tests for Firefox, which are used to check that localized builds of Firefox are working as expected in terms of accessibility and graphical output.

### testrun_remote
Script to execute remote tests for Firefox, which are similar to the functional tests but make use of remote test cases to prove the functionaly against real web sites.

### testrun_update
Script to execute update tests for Firefox, which ensures that an update is always correctly performed for Firefox.

### testrun_compat_addons
Special testrun to execute add-on compatibility tests for Firefox, which ensures that major add-ons are still working as expected for a new major release of Firefox.
