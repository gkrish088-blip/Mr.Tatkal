# Handoff images, ticket documents and installed Chrome

Implementation commit: `48e204cfb31f3b09d1eb88383d7592901af99ab6`.

Changed files: .env.example, docs/gui-server.md, harness/cli.py, harness/core/macro.py, harness/tools/{__init__,browser}.py, harness/web/{app,manager,settings}.py, harness/web/static/{app.js,chat.css,index.html}, tests/unit/{test_core,test_tools_browser}.py, tests/web/{test_server,test_gui}.py, memory/009-permission-denial.md, timestamped test evidence.

The GUI now renders run-owned handoff images and offers session PDF downloads. Images outside the run are filtered, and PDF serving is limited to steps/downloads, with attachment disposition and existing authentication. Browser tools can capture an observed image/canvas, download a service document into the downloads directory, and print the actual current page to PDF. Installed Chrome is an explicit optional managed-browser channel. Permission denials now also stop macros without model recovery.

Checks: artifact/server/GUI/tools suite: 26 passed, 1 skipped (Windows symlink privilege), 30.45 s, test/20261024T200115743458Z/. Core suite including macro block: 12 passed, 2.79 s, test/20261024T200203440310Z/. Initial artifact test failure (fractional canvas clipping rounded by one pixel) is preserved in test/20261024T200010557107Z/. Fixed the test to account for Chromium clipping; the artifact itself was correct. All checks are local fixtures, not real payments.

Watching-human public probes of the actual service, in bundled Chromium and installed Chrome, both returned an edge error before a login form. Records: test/20261024T195920781471Z-live-public-page/ and test/20261024T200038929102Z-live-chrome-page/. No login credentials were submitted, no payment was created, and no ticket was booked. The owner reports the same error in their usual Chrome. BookMyTrain was subsequently requested as an alternative and its public page also failed to load; the owner then selected MakeMyTrip. No passenger information or credential values are recorded here.

Remaining: regular-ticket skill, local GENERAL-quota flow tests, and authorized live alternative rehearsal. Cross-origin embedded payment frames still require operator assistance; element capture only covers observed images/canvas in the current document. A mock pass cannot establish live login or booking readiness.
