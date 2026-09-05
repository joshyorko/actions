from pathlib import Path


def pre_find_module_path(api):
    """Expose the in-tree server package beneath actions-core's pkgutil package."""
    api.search_dirs = [str(Path.cwd() / "src" / "actions")]
