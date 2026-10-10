# PR273 macOS wheel failure diagnosis

- Workflow run: `38022353591`
- Failed job: `build-wheels (macos-15)`, job `114125869416`
- Tested merge checkout: `b20fc815aee5a4a303c7b90d6823b2351c30d452`
- PR head in that merge: `d8dc7a6cd27efd5b460976300e12633b93d3a8dd`
- Merge base: `6d438feb6c92f8bb01428f665ac423fb101b4017`
- Other job results: Ubuntu wheel and sdist passed; Windows wheel job was cancelled after the macOS failure.

The candidate Core and Helper wheel steps passed, and the Runtime CPython 3.12
wheel was created. The CPython 3.13 wheel then failed during its build hook,
before wheel creation. The hook called `action_server/build.py::_download_rcc`
for the pinned RCC 18.19.3 macOS asset. Its `urllib.request.urlopen` connection
exceeded the existing 20-second timeout and raised `TimeoutError`, wrapped as
`urllib.error.URLError`. This is a download transport timeout, not evidence of a
watcher shutdown or wheel contents failure.

Comparison run `38021120824` attempt 2, macOS job `114122362527`, checked out
merge `ccf6e06487a5f9a285d29b55a06fb175b72ca087` with parent PR head
`6ece09c439d12e02bcbde9dcd2164956b97829e2`. That job downloaded the same RCC
asset for both CPython 3.12 and 3.13 and completed the Runtime wheel and
published-dependency verification steps. Thus the current failed stage is
consistent with a transient upstream download timeout; one retry is still
needed to establish the wheel gate for the newer head.

No signed URLs, credentials, or response bodies are included in this receipt.
