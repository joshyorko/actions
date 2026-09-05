"""Import detection for removed private product dependencies."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union


SCANNABLE_EXTENSIONS = frozenset(
    {
        ".cjs",
        ".css",
        ".html",
        ".js",
        ".jsx",
        ".mjs",
        ".ts",
        ".tsx",
    }
)


@dataclass
class ImportViolation:
    """Represents a prohibited import detected in code."""

    file_path: Union[str, Path]
    line_number: int
    import_statement: str
    prohibited_module: str
    severity: str = "error"  # "error" or "warning"


def scan_imports(file_path: str) -> list[ImportViolation]:
    """Scan a shipped source-like text file for removed product imports.

    Args:
        file_path: Path to file to scan

    Returns:
        List of import violations found
    """
    violations = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, start=1):
        sema4ai_match = re.search(r'["\'](@sema4ai/[^"\']+)["\']', line)
        if sema4ai_match:
            violations.append(
                ImportViolation(
                    file_path=file_path,
                    line_number=line_num,
                    import_statement=line.strip(),
                    prohibited_module=sema4ai_match.group(1),
                    severity="error",
                )
            )

        enterprise_match = re.search(r'["\'](@/enterprise[^"\']*)["\']', line)
        if enterprise_match:
            violations.append(
                ImportViolation(
                    file_path=file_path,
                    line_number=line_num,
                    import_statement=line.strip(),
                    prohibited_module=enterprise_match.group(1),
                    severity="error",
                )
            )

    return violations


def detect_removed_product_imports(bundle_path: str) -> list[ImportViolation]:
    """Scan a built bundle for removed product imports.

    Args:
        bundle_path: Path to built JavaScript bundle

    Returns:
        List of import violations found
    """
    violations = []

    with open(bundle_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Search for @sema4ai packages in bundle
    for match in re.finditer(r"@sema4ai/[\w-]+", content):
        violations.append(
            ImportViolation(
                file_path=bundle_path,
                line_number=0,  # Bundle is minified, line numbers not meaningful
                import_statement=match.group(0),
                prohibited_module=match.group(0),
                severity="error",
            )
        )

    # Search for removed private frontend path references.
    for match in re.finditer(r"@/enterprise/[\w/-]+", content):
        violations.append(
            ImportViolation(
                file_path=bundle_path,
                line_number=0,
                import_statement=match.group(0),
                prohibited_module=match.group(0),
                severity="error",
            )
        )

    return violations


class TreeShaker:
    """Tree shaker for detecting and enforcing import boundaries."""

    def __init__(self, root_dir: Path):
        """Initialize TreeShaker.

        Args:
            root_dir: Root directory to scan
        """
        self.root_dir = Path(root_dir)

    def scan_directory(self, directory: Path) -> list[ImportViolation]:
        """Scan a directory recursively for import violations.

        Args:
            directory: Directory to scan

        Returns:
            List of import violations found
        """
        violations = []
        dir_path = Path(directory)

        if not dir_path.is_dir():
            raise NotADirectoryError(
                f"Import scan target is not a directory: {dir_path}"
            )

        for file_path in sorted(
            (path for path in dir_path.rglob("*") if path.is_file()),
            key=lambda path: path.as_posix(),
        ):
            if file_path.suffix.lower() in SCANNABLE_EXTENSIONS:
                violations.extend(scan_imports(str(file_path)))

        return violations

    def generate_report(self, violations: list[ImportViolation]) -> str:
        """Generate a human-readable report of violations.

        Args:
            violations: List of import violations

        Returns:
            Formatted report string
        """
        if not violations:
            return "No import violations found."

        report_lines = [f"Found {len(violations)} import violation(s):", ""]

        for violation in violations:
            file_path = violation.file_path
            if isinstance(file_path, Path):
                file_path = str(file_path)

            report_lines.append(
                f"  {file_path}:{violation.line_number} - "
                f"[{violation.severity.upper()}] "
                f"Prohibited import: {violation.prohibited_module}"
            )
            report_lines.append(f"    {violation.import_statement}")
            report_lines.append("")

        return "\n".join(report_lines)
