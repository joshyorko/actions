# Combined archived frontend qualification

Exact source: a5eaa1cb0be6dcde2d509f2babbb486d9195ccc1. Waited for clean archive build/consumer install to complete. Used that archive's existing node_modules with pinned toolkit Node20.19.3/npm10.8.2. No installs, source changes, browser harness, or candidate rebuild.

npm test: exit0; Runtime32files/287passed; Canvas11files/72passed/1skipped. Total359passed/1skipped. The skip is CanvasContractRoundTrip.test.tsx "validates Python JSON and writes its typed TypeScript round trip": explicit interchange input/output paths were not configured. Do not claim cross-language round-trip or browser/host acceptance.

npm run test:quality: exit0; ESLint, TypeScript and Prettier passed. Topology filtered subset6passed/281skipped (31files skipped due explicit name filter); UI-system subset6passed. These are repeated subset checks, not12additional unique tests; topology's filter skips are distinct from the full Canvas suite's one conditional skip.

receipt.json retains commands, exact cwd, versions, exit statuses, durations/counts. tests.log/quality.log are bounded original logs. artifacts-before.json and artifacts-after.json hash dist/dist-canvas, packaged static contents, lockfile and wheels: unchanged. Source archive's generated _static_contents.py modification and untracked _oauth2_config.py predate these tests as build outputs. No other tracked source changes observed.

Upstream disposition:none.
