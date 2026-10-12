import toolkit
# HELD: run only on distinct root serialization/capacity release.
toolkit.poetry("devutils","run","python","-m","pytest","-q","tests","-n","2")
toolkit.poetry("action_server","run","invoke","test-not-integration")
