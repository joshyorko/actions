# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Actions is a Python framework for extending AI agent capabilities through MCP Tools and Actions. It enables developers to create Python functions that can be called by AI agents through MCP and HTTP APIs.

The key abstraction is the `@tool` or `@action` decorator that turns Python functions into AI-callable endpoints. Type hints and docstrings are used to describe parameters to AI agents.

## Repository Structure

This is a monorepo with several Python packages:

- `action_server/` - The main Action Server that hosts and exposes actions via HTTP/MCP
- `actions/` - Core `actions-core` library with `@action` decorator and MCP v2 surface
- `mcp/` - MCP protocol implementation with `@tool`, `@resource`, `@prompt` decorators
- `common/` - Shared utilities across packages
- `build_common/` - Shared build utilities
- `actions-http-helper/` - HTTP helper utilities
- `templates/` - Project templates for `action-server new`

## Development Commands

### Prerequisites
- Python 3.11+
- Node.js 20.x LTS
- Poetry and Invoke: `pip install -r devutils/requirements.txt`

### Per-Package Development
Navigate to a package directory (e.g., `action_server/`, `actions/`, `mcp/`) and run:

```bash
inv install      # Install dependencies and create virtual environment
inv test         # Run tests with pytest
inv test -t path/to/test.py::test_name  # Run specific test
inv lint         # Run linter (ruff)
inv pretty       # Auto-format code
inv typecheck    # Run type checking
inv check-all    # Run lint, typecheck, and tests
inv docs         # Generate documentation
```

### Repository Toolkit
From repository root, use the RCC-owned task boundary:

```bash
rcc run -r developer/toolkit.yaml --dev -t Doctor
rcc run -r developer/toolkit.yaml --dev -t CheckAll
rcc run -r developer/toolkit.yaml --dev -t FrontendTest
rcc run -r developer/toolkit.yaml --dev -t InstallCommunity
```

### Frontend Build (Action Server)
```bash
cd action_server/frontend
npm ci && npm run build      # Production build

# Or via invoke:
cd action_server
inv build-frontend                    # Build and embed Runtime
inv build-frontend --debug            # Debug build (not minified)

# Verify the separate Canvas artifact:
cd frontend && npm run build:canvas
```

### Frontend Development
```bash
cd action_server/frontend
npm run dev          # Start dev server with hot reload
npm test             # Run tests
npm run test:lint    # Run linter
npm run test:types   # TypeScript type checking
```

### Building Executable
```bash
cd action_server
inv build-frontend           # Build frontend first
inv build-executable         # Build PyInstaller binary
inv build-executable --sign  # Build and sign
inv test-binary              # Test the built binary
```

## Architecture Notes

### Action/Tool Pattern
Functions become AI-callable through decorators:

```python
from actions.mcp import tool

@tool
def greeting(name: str) -> str:
    """
    Greets the user

    Args:
        name: The user name

    Returns:
        Final user greeting
    """
    return f"Hello {name}!"
```

### Environment Management
Python environments are defined via `package.yaml` files (not requirements.txt). The RCC tool manages reproducible environments.

### Frontend Boundary
Runtime and Canvas are separate Vite roots backed by one public manifest and
lockfile. The build has no product tier, private registry, or vendored product
package mode. Project creation is embedded-only and exposes exactly the four
manifest-owned community templates.

### Testing Structure
- Unit tests: `inv test`
- Integration tests: `inv test-binary` (uses built executable)
- Tests use pytest with markers like `@pytest.mark.integration_test`
