"""Read-only reproductions against the supplied archive producer patch."""

import argparse
import json
import sys
import tarfile
import tempfile
import types
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--patch", type=Path, default=Path("/workspace/work/native-provenance-archive-fix-f1d84175.patch"))
args = parser.parse_args()
sys.path.insert(0, "/workspace/work/community-resume/workitems-ci/action_server/scripts")
import write_native_artifact_manifest as writer

patch = args.patch.read_text()
section = patch.split("+++ b/action_server/scripts/archive_native_artifact_provenance.py\n", 1)[1].split("\ndiff --git ", 1)[0]
source = "\n".join(line[1:] for line in section.splitlines() if line.startswith("+")) + "\n"
archive = types.ModuleType("archive_patch_review")
exec(compile(source, "<archive-patch-review>", "exec"), archive.__dict__)

with tempfile.TemporaryDirectory(prefix="archive-review-", dir=Path(__file__).parent) as temporary:
    review = Path(temporary).resolve()
    for scenario in (
        "escaping_directory_link", "dangling_escape_link",
        "absolute_internal_file_link", "outside_executable_locator",
        "manifest_drift", "mode_verification",
    ):
        base = review / scenario
        tree = base / "dist/action-server"
        tree.mkdir(parents=True)
        executable = tree / "action-server"
        executable.write_bytes(b"actual frozen executable")
        if scenario == "mode_verification":
            executable.chmod(0o4755)
        outside = base / "outside"
        outside.mkdir()
        (outside / "payload").write_bytes(b"outside payload")
        if scenario == "escaping_directory_link":
            (tree / "link").symlink_to(outside, target_is_directory=True)
        elif scenario == "dangling_escape_link":
            (tree / "link").symlink_to("../../../missing")
        elif scenario == "absolute_internal_file_link":
            (tree / "link").symlink_to(executable)
        metadata = base / "output"
        metadata.mkdir()
        inventory = metadata / "native-artifact-tree-inventory.json"
        inventory.write_text(json.dumps(writer.packaged_tree_inventory(tree)))
        record = {
            "embedded_files_sha256": writer.packaged_files_sha256(tree),
            "frozen_package_tree_sha256": writer.packaged_tree_sha256(tree),
            "frozen_package_tree_inventory_path": archive.INVENTORY_ARCHIVE_PATH,
        }
        locator = "dist/action-server/action-server"
        binary = executable
        if scenario == "outside_executable_locator":
            locator = "dist/action-server/../../outside/payload"
            binary = outside / "payload"
        manifest = {
            "schema_version": 1,
            "source_sha": "a" * 40,
            "artifacts": {"frozen": dict(record, path=locator, sha256=writer.sha256(binary)), "go-wrapper": record},
            "artifact_downloads": {
                "frozen": {"container_archive_path": "native-artifact-provenance.tar", "archive_path": locator, "tree_archive_path": archive.TREE_ARCHIVE_PATH, "inventory_archive_path": archive.INVENTORY_ARCHIVE_PATH},
                "manifest": {"container_archive_path": "native-artifact-provenance.tar", "archive_path": archive.MANIFEST_ARCHIVE_PATH, "inventory_archive_path": archive.INVENTORY_ARCHIVE_PATH},
            },
        }
        manifest_path = metadata / "native-artifact-manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        output = metadata / "native-artifact-provenance.tar"
        original_tar_info = archive._tar_info

        def drift_before_manifest_copy(path, name):
            if name == archive.TREE_ARCHIVE_PATH:
                changed = json.loads(manifest_path.read_text())
                changed["source_sha"] = "b" * 40
                manifest_path.write_text(json.dumps(changed))
            return original_tar_info(path, name)

        if scenario == "manifest_drift":
            archive._tar_info = drift_before_manifest_copy
        try:
            archive.create_archive(tree, manifest_path, inventory, output)
            print(scenario, "producer ACCEPTED")
            if scenario == "mode_verification":
                changed = metadata / "changed.tar"
                with tarfile.open(output) as old, tarfile.open(changed, "w", format=tarfile.PAX_FORMAT) as new:
                    for member in old.getmembers():
                        if member.name == locator:
                            member.mode = 0o755
                        stream = old.extractfile(member) if member.isfile() else None
                        new.addfile(member, stream)
                        if stream:
                            stream.close()
                try:
                    archive._verify_tar(changed, tree, manifest_path, inventory, writer.packaged_tree_inventory(tree), manifest_path.read_bytes(), inventory.read_bytes())
                except ValueError as error:
                    print("  verifier REJECTED mode0755 against04755:", error)
                else:
                    print("  verifier ACCEPTED mode0755; inventory requires04755")
            else:
                with tarfile.open(output) as packaged:
                    if scenario.endswith("link"):
                        try:
                            packaged.extractall(base / "extracted", filter="data")
                        except tarfile.FilterError as error:
                            print("  safe extraction rejects:", type(error).__name__)
                    elif scenario == "outside_executable_locator":
                        print("  declared executable member present:", locator in packaged.getnames())
                    else:
                        captured = json.load(packaged.extractfile(archive.MANIFEST_ARCHIVE_PATH))
                        print("  source_sha changed during archive:", captured["source_sha"] != manifest["source_sha"])
        except ValueError as error:
            print(scenario, "producer REJECTED:", error)
        finally:
            archive._tar_info = original_tar_info
