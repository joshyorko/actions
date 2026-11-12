# Owned documentation adapters

The rendering implementation is derived from the MIT-licensed lazydocs fork at https://github.com/robocorp/lazydocs/commit/3eeda5b5012f698fad0be6272747c40052b3ec12, originally Machine Learning Tooling. Only generation.py is retained: root/namespace and public export rendering, ordered signatures/anchors, enum/exception sections, source links, and mdformat normalization are a cohesive generator; CLI, packaging and upstream dependencies are not copied.

Original generation.py SHA256: 8d946b5db5eb7f93433b41275b7cc1cb3fb9b98750a786c6af94c2ec74536b48. Local changes: owned import namespace, importlib module loading, fail-closed module errors, validation delegated to an owned adapter without shell commands. Historical lazydocs ignore markers and attribution remain compatible.

The owned validation supplement implements D420/D421 behavior from https://github.com/robocorp/pydocstyle/commit/34719279355f6ba934385db21dfb81cdb8a44fcf atop official pydocstyle. Both original MIT notices are retained beside this file. No vendor package import is required.

Runtime tooling dependencies: official pydocstyle6.3.0 and mdformat-gfm (which supplies mdformat). No lazydocs installation is needed. Root owns manifests and task wiring.
