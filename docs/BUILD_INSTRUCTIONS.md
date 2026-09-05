# Action Server Build Instructions

## Quick Build

This builds the open-source Runtime and Canvas frontends from public dependencies.

### Prerequisites

- Python 3.12+
- Node.js 20.x
- Go 1.23+
- uv (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Build Steps (exactly as CI does)

```bash
# 1. Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install devutils requirements
cd action_server
uv run --no-project --python 3.12 python -m pip install --break-system-packages -r ../devutils/requirements.txt

# 3. Install project dependencies (this installs all monorepo packages)
uv run --no-project --python 3.12 inv install

# 4. Build the public frontend
uv run --no-project --python 3.12 inv build-frontend
# Output: frontend/dist/index.html (single-file, ~291 KB)

# 5. Build OAuth2 config
uv run --no-project --python 3.12 inv build-oauth2-config

# 6. Build final executable
uv run --no-project --python 3.12 poetry run inv build-executable --go-wrapper
# Output: dist/final/action-server (Linux)
#         dist/final/action-server.exe (Windows)
```

### Test the Binary

```bash
# Check version
./dist/final/action-server version

# Start server (needs a package.yaml with actions)
./dist/final/action-server start --port=8080
```

## What Gets Built

### Frontend
- **Runtime and Canvas**: built from the single public manifest and lockfile
  - UI: Radix UI primitives + Tailwind CSS
  - Features: Action execution, logs, artifacts, run history
  - Dependencies: Public npm packages only
  - Size: ~291 KB (single HTML file)

### Backend
- Python action execution engine
- FastAPI server
- Embedded frontend HTML
- RCC integration (downloaded on first run)
- Go wrapper executable

## Directory Structure

```
dist/
├── action-server/          # PyInstaller output
│   ├── action-server       # Python executable
│   └── _internal/          # Dependencies
└── final/                  # Go wrapper (FINAL OUTPUT)
    └── action-server       # ← THIS IS WHAT YOU DISTRIBUTE
```

## Build Artifacts

After successful build:
- `dist/final/action-server` - Final distributable binary (Linux/macOS)
- `dist/final/action-server.exe` - Final distributable binary (Windows)
- `frontend/dist/index.html` - Standalone frontend (for debugging)
- `src/actions/server/_static_contents.py` - Embedded frontend Python module

## Verification

```bash
# 1. Binary exists and is executable
ls -lh dist/final/action-server
# Expected: ~150-200 MB executable

# 2. Version check works
./dist/final/action-server version
# Expected: 2.16.1 (or current version)

# 3. Help command works
./dist/final/action-server --help
# Expected: CLI help output

# 4. Server can start (will fail without actions - that's OK)
./dist/final/action-server start
# Expected: Initializes DB, downloads RCC, fails on missing package.yaml
```

## Common Issues

### Issue: "No module named pytest"
**Solution**: Run `inv install` first - it installs all dependencies

### Issue: "Go executable not found"
**Solution**: Install Go 1.23+ and add to PATH

### Issue: "dist/final/ doesn't exist"
**Solution**: You must use `--go-wrapper` flag for final build

### Issue: "Removed product imports detected"
**Solution**: Build from the checked-in public manifest and remove the reported private import.

## CI/CD

The CI workflow (`.github/workflows/action_server_binary_release.yml`) builds:
- **4 platforms**: ubuntu-22.04, windows-2022, macos-13, macos-15
- **One public Runtime/Canvas build** with no registry credentials

Artifacts are uploaded to S3 and GitHub Releases.
