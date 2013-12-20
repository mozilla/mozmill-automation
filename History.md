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
