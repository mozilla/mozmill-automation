2.0.8.1 / 2014-09-30
====================

 * Testruns are failing on OS X if real binary or new signed app bundle get specified (#183)
 * UpdateTestrun has to reset update-settings.ini and channel-prefs.js files (#181)
 * Update testruns fail if 'stagingPath' does not exist (#154)
 * Fix updateStagingPath property for new location (#177)
 * Remove handling of update-settings.ini file (#164)

2.0.8 / 2014-09-16
==================

 * Release version 2.0.8 and upgrade to Mozmill 2.0.8 (#173)

2.0.7 / 2014-09-12
==================

 * Release version 2.0.7 and upgrade to Mozmill 2.0.7 (#170)
 * Upgrade mozversion for handling new signed builds on OS X (#166)
 * Pass-through all update settings via persisted.update (#164)
 * Update testrun should leave changes to 'channel-prefs.js' file to the tests (#164)
 * Retrival of application version information broken due to wrong binary specified (#157)
 * Use mozversion to retrieve application information #121

2.0.6.2 / 2014-07-17
====================

 * Add --override-update-url option to the update scripts (#156)

2.0.6.1 / 2014-04-04
====================

 * Add --override-update-chanel parameter to set update channel restrictions (#132)
 * 'filename' should be optional when creating the junit report (#130)

2.0.6 / 2014-03-07
==================

 * Release version 2.0.6 and upgrade to Mozmill 2.0.6 (#128)
 * Use APPLICATION_BINARY_NAMES map for getting the correct binary (#125)

2.0.5 / 2014-02-10
==================

  * Upgrade to Mozmill 2.0.5 and mozdownload 1.11.1 (#122)

2.0.3 / 2013-12-20
==================

  * Upgrade to Mozmill 2.0.3 (#118)

2.0.2 / 2013-12-11
==================

  * Upgrade to Mozmill 2.0.2 to make use of mozfile.remove() for removing files and directories (#113)
  * Download target add-on for addon testrun into workspace (#110)
  * Replace sys.platform with mozinfo.os checks (#25)

2.0.1.1 / 2013-11-28
====================

  * Fallback update tests are failing for non-default update channels (#105)

2.0.1 / 2013-11-21
==================

  * Add workspace folder option for testrun related data (#80)
  * Bump mozdownload to 1.10 and mozmill to 2.0.1 (#102)
  * Add support for other application testruns (#89)
  * Correct detection of remote repository name to not delete CWD in case of failures (#99)
  * Automation scripts should correctly handle exceptions (Bug 853005)

2.0 / 2013-09-24
================

  * Upgrade to Mozmill 2.0 (#84)

2.0rc6 / 2013-09-20
===================

  * Upgrade to Mozmill 2.0rc6 (#81)

2.0rc5.4 / 2013-09-13
=====================

  * Fix broken report generation due to Mercurial changes (#57)

2.0rc5.3 / 2013-09-12
=====================

  * Reintroduce folder scraping for builds (#72)

2.0rc5.2 / 2013-09-11
=====================

  * Added missing dependency for mozdownload (#71)

2.0rc5.1 / 2013-09-11
=====================

  * Use the Mercurial CLI commands and not its internal API (#57)
  * Fixes addons testrun to avoid unecessary execution of finally block (#61)
  * Update ReadMe to reflect new installation workflow in dependencies bump 77a7cc3 (#51)

2.0rc5 / 2013-08-28
===================

  * Update repository URL to the mozilla account (#45)
  * Bump dependencies for mozmill 2.0rc5 release (#47)
  * Remove restrictions on update channels (#42)
