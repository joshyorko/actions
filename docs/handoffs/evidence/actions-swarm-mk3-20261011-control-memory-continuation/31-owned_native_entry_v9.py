"""Final independent package-Python boundary; import-only controls never main."""
from v9_entry_bootstrap import main

if __name__ == '__main__':
    raise SystemExit(main())
