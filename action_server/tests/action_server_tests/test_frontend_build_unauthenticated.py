"""
Contract test: Frontend builds without authentication to private registries.

This test MUST pass for external contributors to build the Action Server.
"""
import os
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration_test


class _RuntimeInlineAssets(HTMLParser):
    """Collect the shipped Runtime HTML's inline assets and external refs."""

    def __init__(self) -> None:
        super().__init__()
        self.inline_javascript: list[str] = []
        self.inline_css: list[str] = []
        self.external_javascript: list[str] = []
        self.external_stylesheets: list[str] = []
        self._active_inline_asset: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script":
            if source := attributes.get("src"):
                self.external_javascript.append(source)
            elif attributes.get("type") == "module":
                self._active_inline_asset = self.inline_javascript
        elif tag == "style":
            self._active_inline_asset = self.inline_css
        elif tag == "link" and attributes.get("rel") == "stylesheet":
            if href := attributes.get("href"):
                self.external_stylesheets.append(href)

    def handle_data(self, data: str) -> None:
        if self._active_inline_asset is not None:
            self._active_inline_asset.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._active_inline_asset = None


class TestUnauthenticatedBuild:
    """Validate frontend builds without private registry credentials."""

    @pytest.fixture(scope="class")
    def clean_frontend_dir(self):
        """Provide a clean frontend directory without node_modules or dist."""
        frontend_dir = Path(__file__).parent.parent.parent / "frontend"

        # Remove any cached dependencies and build outputs
        if (frontend_dir / "node_modules").exists():
            shutil.rmtree(frontend_dir / "node_modules")
        if (frontend_dir / "dist").exists():
            shutil.rmtree(frontend_dir / "dist")

        return frontend_dir

    @pytest.fixture(scope="class")
    def unauthenticated_env(self):
        """Environment without any GitHub Packages authentication."""
        env = os.environ.copy()

        # Remove any authentication tokens
        env.pop("NPM_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
        env.pop("NODE_AUTH_TOKEN", None)

        # Remove npmrc files that might contain credentials
        npmrc_user = Path.home() / ".npmrc"
        npmrc_backup = None
        if npmrc_user.exists():
            npmrc_backup = npmrc_user.read_text()
            npmrc_user.unlink()

        yield env

        # Restore npmrc if it existed
        if npmrc_backup:
            npmrc_user.write_text(npmrc_backup)

    def test_npm_ci_succeeds_without_auth(
        self, clean_frontend_dir, unauthenticated_env
    ):
        """MUST: npm ci completes successfully without authentication."""
        result = subprocess.run(
            ["npm", "ci"],
            cwd=clean_frontend_dir,
            env=unauthenticated_env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"npm ci failed with exit code {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Verify no 401 authentication errors
        assert "401" not in result.stderr, (
            "npm ci attempted to access private registry:\n" + result.stderr
        )
        assert "Unauthorized" not in result.stderr

    def test_npm_build_succeeds_without_auth(
        self, clean_frontend_dir, unauthenticated_env
    ):
        """MUST: npm run build completes successfully without authentication."""
        # First install dependencies
        subprocess.run(
            ["npm", "ci"],
            cwd=clean_frontend_dir,
            env=unauthenticated_env,
            check=True,
            capture_output=True,
        )

        # Then build
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=clean_frontend_dir,
            env=unauthenticated_env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"npm run build failed with exit code {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    def test_build_output_exists(self, clean_frontend_dir, unauthenticated_env):
        """MUST: Build creates dist/ directory with expected files."""
        # Build (assuming npm ci already ran in previous tests)
        subprocess.run(
            ["npm", "ci"],
            cwd=clean_frontend_dir,
            env=unauthenticated_env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["npm", "run", "build"],
            cwd=clean_frontend_dir,
            env=unauthenticated_env,
            check=True,
            capture_output=True,
        )

        dist_dir = clean_frontend_dir / "dist"
        assert dist_dir.exists(), "dist/ directory not created"

        index_html = dist_dir / "index.html"
        assert index_html.exists(), "dist/index.html not created"

        # Runtime intentionally inlines its Vite assets into a single HTML file.
        parser = _RuntimeInlineAssets()
        parser.feed(index_html.read_text(encoding="utf-8"))
        assert any(
            chunk.strip() for chunk in parser.inline_javascript
        ), "No inline Runtime JavaScript found"
        assert any(
            chunk.strip() for chunk in parser.inline_css
        ), "No inline Runtime CSS found"
        assert not parser.external_javascript, (
            "Runtime HTML references external JavaScript: "
            f"{parser.external_javascript}"
        )
        assert not parser.external_stylesheets, (
            "Runtime HTML references external stylesheets: "
            f"{parser.external_stylesheets}"
        )

    def test_no_private_registry_access(self, clean_frontend_dir, unauthenticated_env):
        """MUST: Build does not make network requests to GitHub Packages."""
        # Mock DNS resolution for npm.pkg.github.com to detect access attempts
        # This is a simplified version; a full implementation might use mitmproxy

        result = subprocess.run(
            ["npm", "ci", "--verbose"],
            cwd=clean_frontend_dir,
            env=unauthenticated_env,
            capture_output=True,
            text=True,
        )

        # Verify no requests to GitHub Packages
        assert "npm.pkg.github.com" not in result.stdout
        assert "npm.pkg.github.com" not in result.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
