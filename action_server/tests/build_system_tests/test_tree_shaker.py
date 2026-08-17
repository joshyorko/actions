"""
Unit tests for removed-product import detection.
"""

from pathlib import Path

import pytest

# Import will fail until implementation exists (TDD)
try:
    from tree_shaker import (
        ImportViolation,
        TreeShaker,
        detect_removed_product_imports,
        scan_imports,
    )
except ImportError:
    # Expected to fail initially (TDD)
    pytest.skip("TreeShaker not yet implemented", allow_module_level=True)


class TestScanImports:
    """Test scan_imports() function for AST-based import detection."""

    def test_detect_enterprise_import_in_core_file(self, tmp_path):
        """Test detecting enterprise import in core/ file."""
        # Arrange
        test_file = tmp_path / "Dashboard.tsx"
        test_file.write_text(
            """
import React from 'react';
import { Button } from '@sema4ai/components';  // VIOLATION
import { Table } from '@/core/components/ui/Table';

export function Dashboard() {
    return <div><Button>Click</Button></div>;
}
"""
        )

        # Act
        violations = scan_imports(test_file)

        # Assert
        assert len(violations) == 1
        assert violations[0].file_path == test_file
        assert violations[0].line_number == 3
        assert "@sema4ai/components" in violations[0].import_statement
        assert violations[0].prohibited_module == "@sema4ai/components"
        assert violations[0].severity == "error"

    def test_detect_multiple_enterprise_imports(self, tmp_path):
        """Test detecting multiple enterprise imports in one file."""
        # Arrange
        test_file = tmp_path / "Analytics.tsx"
        test_file.write_text(
            """
import { Button } from '@sema4ai/components';
import { Icon } from '@sema4ai/icons';
import { theme } from '@sema4ai/theme';
"""
        )

        # Act
        violations = scan_imports(test_file)

        # Assert
        assert len(violations) == 3
        prohibited_modules = [v.prohibited_module for v in violations]
        assert "@sema4ai/components" in prohibited_modules
        assert "@sema4ai/icons" in prohibited_modules
        assert "@sema4ai/theme" in prohibited_modules

    def test_detect_enterprise_path_import(self, tmp_path):
        """Test detecting @/enterprise path imports in core/ files."""
        # Arrange
        test_file = tmp_path / "core" / "Dashboard.tsx"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            """
import React from 'react';
import { KBSearch } from '@/enterprise/pages/KnowledgeBase';  // VIOLATION
"""
        )

        # Act
        violations = scan_imports(test_file)

        # Assert
        assert len(violations) == 1
        assert "@/enterprise" in violations[0].import_statement

    def test_no_violation_for_core_imports(self, tmp_path):
        """Test no violations for valid core/ imports."""
        # Arrange
        test_file = tmp_path / "Dashboard.tsx"
        test_file.write_text(
            """
import React from 'react';
import { Button } from '@radix-ui/react-button';
import { Table } from '@/core/components/ui/Table';
import { useAPI } from '@/shared/hooks/useAPI';
"""
        )

        # Act
        violations = scan_imports(test_file)

        # Assert
        assert len(violations) == 0

    def test_enterprise_path_does_not_bypass_import_validation(self, tmp_path):
        """Test enterprise paths cannot bypass forbidden import validation."""
        # Arrange
        test_file = tmp_path / "enterprise" / "Analytics.tsx"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            """
import { Button } from '@sema4ai/components';  // ALLOWED
import { Chart } from '@/enterprise/components/Chart';  // ALLOWED
"""
        )

        # Act
        violations = scan_imports(test_file)

        # Assert
        assert len(violations) == 2

    @pytest.mark.parametrize(
        "extension", ["html", "js", "jsx", "ts", "tsx", "mjs", "cjs", "css"]
    )
    def test_scan_directory_scans_shipped_text_extensions(self, tmp_path, extension):
        """Test every shipped source-like extension is scanned for imports."""
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / f"index.{extension}").write_text(
            '"@sema4ai/components"\n', encoding="utf-8"
        )

        violations = TreeShaker(root_dir=tmp_path).scan_directory(dist_dir)

        assert [violation.prohibited_module for violation in violations] == [
            "@sema4ai/components"
        ]

    def test_scan_directory_ignores_non_source_assets(self, tmp_path):
        """Test arbitrary assets and source maps are not import-scanned."""
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "asset.svg").write_text("@sema4ai/components", encoding="utf-8")
        (dist_dir / "index.js.map").write_text("@sema4ai/components", encoding="utf-8")

        assert (
            TreeShaker(root_dir=tmp_path).scan_directory(dist_dir) == []
        )


class TestDetectRemovedProductImports:
    """Test built-bundle removed-product scanning."""

    def test_detect_sema4ai_import_in_bundle(self, tmp_path):
        """Test detecting @sema4ai imports in built JS bundle."""
        # Arrange
        bundle_file = tmp_path / "index.js"
        bundle_file.write_text(
            """
(function() {
    const Button = require('@sema4ai/components').Button;
    // ... rest of bundle
})();
"""
        )

        # Act
        violations = detect_removed_product_imports(bundle_file)

        # Assert
        assert len(violations) > 0
        assert any("@sema4ai/components" in v.import_statement for v in violations)

    def test_detect_enterprise_path_in_bundle(self, tmp_path):
        """Test detecting @/enterprise imports in built bundle."""
        # Arrange
        bundle_file = tmp_path / "index.js"
        bundle_file.write_text(
            """
import { KBSearch } from '@/enterprise/pages/KnowledgeBase';
"""
        )

        # Act
        violations = detect_removed_product_imports(bundle_file)

        # Assert
        assert len(violations) > 0
        assert any("@/enterprise" in v.import_statement for v in violations)

    def test_no_violation_for_clean_community_bundle(self, tmp_path):
        """Test no violations in clean community bundle."""
        # Arrange
        bundle_file = tmp_path / "index.js"
        bundle_file.write_text(
            """
(function() {
    const Button = require('@radix-ui/react-button').Button;
    const React = require('react');
    // ... rest of bundle
})();
"""
        )

        # Act
        violations = detect_removed_product_imports(bundle_file)

        # Assert
        assert len(violations) == 0

    def test_scan_minified_bundle(self, tmp_path):
        """Test scanning minified bundle (single line)."""
        # Arrange
        bundle_file = tmp_path / "index.min.js"
        bundle_file.write_text(
            'var a=require("@sema4ai/components"),b=require("react");'
        )

        # Act
        violations = detect_removed_product_imports(bundle_file)

        # Assert
        assert len(violations) > 0


class TestImportViolation:
    """Test ImportViolation dataclass."""

    def test_violation_has_required_fields(self):
        """Test ImportViolation contains all required fields."""
        # Act
        violation = ImportViolation(
            file_path=Path("src/core/Dashboard.tsx"),
            line_number=5,
            import_statement="import { Button } from '@sema4ai/components';",
            prohibited_module="@sema4ai/components",
            severity="error",
        )

        # Assert
        assert violation.file_path == Path("src/core/Dashboard.tsx")
        assert violation.line_number == 5
        assert "@sema4ai/components" in violation.import_statement
        assert violation.prohibited_module == "@sema4ai/components"
        assert violation.severity == "error"

    def test_violation_severity_error_or_warning(self):
        """Test violation severity is either 'error' or 'warning'."""
        # Act
        error_violation = ImportViolation(
            file_path=Path("test.tsx"),
            line_number=1,
            import_statement="import foo",
            prohibited_module="foo",
            severity="error",
        )

        warning_violation = ImportViolation(
            file_path=Path("test.tsx"),
            line_number=1,
            import_statement="import foo",
            prohibited_module="foo",
            severity="warning",
        )

        # Assert
        assert error_violation.severity in ["error", "warning"]
        assert warning_violation.severity in ["error", "warning"]


class TestFeatureBoundaryEnforcement:
    """Test feature boundary enforcement with feature-boundaries.json."""

    def test_enforce_boundaries_blocks_enterprise_in_core(self, tmp_path):
        """Test feature boundaries block enterprise imports in core files."""
        # Arrange
        test_file = tmp_path / "core" / "Dashboard.tsx"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            """
import { Button } from '@sema4ai/components';  // VIOLATION
"""
        )

        # Act
        violations = scan_imports(test_file)

        # Assert
        assert len(violations) > 0
        assert any(
            "design_system" in str(v) or "@sema4ai" in v.import_statement
            for v in violations
        )

    def test_enterprise_features_are_not_exempt_in_enterprise_dir(self, tmp_path):
        """Test enterprise paths do not exempt forbidden imports."""
        # Arrange
        test_file = tmp_path / "enterprise" / "Analytics.tsx"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            """
import { Button } from '@sema4ai/components';  // ALLOWED
"""
        )

        # Act
        violations = scan_imports(test_file)

        # Assert
        assert len(violations) == 1


class TestTreeShakerIntegration:
    """Integration tests for TreeShaker with real-world scenarios."""

    def test_scan_entire_core_directory(self, tmp_path):
        """Test scanning entire core/ directory for violations."""
        # Arrange
        core_dir = tmp_path / "src" / "core"
        core_dir.mkdir(parents=True)

        # Create multiple files with violations
        (core_dir / "Dashboard.tsx").write_text(
            """
import { Button } from '@sema4ai/components';  // VIOLATION
"""
        )
        (core_dir / "Actions.tsx").write_text(
            """
import { Table } from '@radix-ui/react-table';  // OK
"""
        )
        (core_dir / "Logs.tsx").write_text(
            """
import { KBSearch } from '@/enterprise/pages/KB';  // VIOLATION
"""
        )

        # Act
        shaker = TreeShaker(root_dir=tmp_path)
        violations = shaker.scan_directory(core_dir)

        # Assert
        assert len(violations) == 2  # Dashboard.tsx and Logs.tsx

    def test_generate_violation_report(self, tmp_path):
        """Test generating human-readable violation report."""
        # Arrange
        violations = [
            ImportViolation(
                file_path=Path("src/core/Dashboard.tsx"),
                line_number=3,
                import_statement="import { Button } from '@sema4ai/components';",
                prohibited_module="@sema4ai/components",
                severity="error",
            )
        ]

        # Act
        shaker = TreeShaker(root_dir=tmp_path)
        report = shaker.generate_report(violations)

        # Assert
        assert "src/core/Dashboard.tsx:3" in report
        assert "@sema4ai/components" in report
        assert "error" in report.lower()

    def test_scan_directory_reports_prohibited_imports_in_built_tree(self, tmp_path):
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        bundle = dist_dir / "index.js"
        bundle.write_text("import '@sema4ai/theme';")

        shaker = TreeShaker(root_dir=tmp_path)

        violations = shaker.scan_directory(dist_dir)

        assert [violation.prohibited_module for violation in violations] == [
            "@sema4ai/theme"
        ]

    def test_detect_removed_product_imports_does_not_swallow_read_errors(
        self, tmp_path, monkeypatch
    ):
        bundle = tmp_path / "index.js"
        bundle.write_text("import '@sema4ai/theme';", encoding="utf-8")

        def fail_read(*args, **kwargs):
            raise PermissionError("permission denied")

        monkeypatch.setattr("builtins.open", fail_read)

        with pytest.raises(PermissionError, match="permission denied"):
            detect_removed_product_imports(bundle)

    def test_scan_directory_does_not_swallow_read_errors(self, tmp_path, monkeypatch):
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        bundle = dist_dir / "index.js"
        bundle.write_text("import '@sema4ai/theme';")

        import builtins

        original_open = builtins.open

        def fail_for_bundle(path, *args, **kwargs):
            if Path(path) == bundle:
                raise PermissionError("permission denied")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", fail_for_bundle)
        shaker = TreeShaker(root_dir=tmp_path)

        with pytest.raises(PermissionError, match="permission denied"):
            shaker.scan_directory(dist_dir)
