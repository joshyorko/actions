An explicit pytest basetemp isolates scratch files, not plugin logging output.
The pinned robocorp.log_pytest plugin defaults --robocorp-log-output to ./output.
For a preservation-sensitive private run, set a unique absent owned logging
destination as well as basetemp, and verify protected generated-output digests
before and after the run. Tracked Git/source preservation does not establish
ignored log preservation. If an original body was not retained, report it
unavailable; a smaller successor cannot replace its recorded digest.
