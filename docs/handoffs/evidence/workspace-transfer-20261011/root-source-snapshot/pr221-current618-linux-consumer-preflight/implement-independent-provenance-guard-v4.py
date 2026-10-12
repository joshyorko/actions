from pathlib import Path
import hashlib
base=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight');old=base/'current-input-admission-v3.py';assert hashlib.sha256(old.read_bytes()).hexdigest()=='7474e6fae0e8d8d8211bfc9376697dcd14546b9c1a4ea5925c4042786720ea25'
s=old.read_text().replace('import io\n','import io\nimport json\n').replace('from pathlib import PurePosixPath','from pathlib import Path, PurePosixPath')
insert='''TRUSTED_QUALIFICATION = Path(
    "/workspace/engineering/pr221-current618-wheel-integrity-owned/OWNERFINAL-current618-partial-distribution-integrity-v2.json"
)
TRUSTED_QUALIFICATION_SHA256 = "9b406fdf505871e6790d7a4233d0b8c075ae6f170f2c5b7a954bbca0f0d46236"


def admit_provenance(manifest):
    """Bind identity labels to qualified original bytes independently of caller labels."""
    body = TRUSTED_QUALIFICATION.read_bytes()
    assert digest(body) == TRUSTED_QUALIFICATION_SHA256
    qualification = json.loads(body.decode("utf-8"))
    reference = qualification["complete_original_member_inventories"]
    inspected = Path(reference["path"]).read_bytes()
    assert len(inspected) == reference["bytes"]
    assert digest(inspected) == reference["sha256"]
    inspection = json.loads(inspected.decode("utf-8"))
    original = manifest["original_archive"]
    artifacts = [
        artifact for artifact in inspection["artifacts"]
        if artifact["file"]["path"] == original["path_private"]
        and artifact["file"]["bytes"] == original["bytes"]
        and artifact["file"]["sha256"] == original["sha256"]
    ]
    assert len(artifacts) == 1
    artifact = artifacts[0]
    expected = {
        "id": artifact["id"],
        "run": qualification["producer"]["run_id"],
        "job": artifact["job_id"],
    }
    assert inspection["run_id"] == expected["run"]
    producer = manifest["producer_tuple"]
    for field, producer_field in [("id", "artifact_id"), ("run", "run_id"), ("job", "job_id")]:
        assert type(original[field]) is int
        assert type(producer[producer_field]) is int
        assert original[field] == producer[producer_field] == expected[field]
    return expected


'''
anchor='def admit(archive_path, wheel_path, manifest, repository):\n';assert anchor in s;s=s.replace(anchor,insert+anchor+'    provenance = admit_provenance(manifest)\n');s=s.replace('"tracked_payload_source_matches": 215,','"tracked_payload_source_matches": 215,\n            "qualified_archive_provenance": provenance,');new=base/'current-input-admission-v4.py';assert not new.exists();new.write_text(s)
manifest=base/'input-and-source-admission-v4.json';runner=base/'installed-consumer-runner-v3.py';assert hashlib.sha256(runner.read_bytes()).hexdigest()=='a7da7760d4b93b1053ca3adef14a7860f61502250962edad130aa4014426e2be';s=runner.read_text().replace('installed-linux-current618-90a785d8-1','installed-linux-current618-90a785d8-2').replace('input-and-source-admission.json','input-and-source-admission-v4.json').replace('094853d8b745dcf1f6e9a6e392f84c7b544ef0899f0afbfd0502463b8f48bd3d',hashlib.sha256(manifest.read_bytes()).hexdigest()).replace('current-input-admission-v3.py','current-input-admission-v4.py').replace('7474e6fae0e8d8d8211bfc9376697dcd14546b9c1a4ea5925c4042786720ea25',hashlib.sha256(new.read_bytes()).hexdigest());newrunner=base/'installed-consumer-runner-v4.py';assert not newrunner.exists();newrunner.write_text(s)
for oldname,newname in [('test_current_input_admission.py','test_current_input_admission_v4.py'),('test_installed_consumer_runner_v3.py','test_installed_consumer_runner_v4.py')]:
 s=(base/oldname).read_text().replace('current-input-admission-v3.py','current-input-admission-v4.py').replace('input-and-source-admission.json','input-and-source-admission-v4.json').replace('installed-consumer-runner-v3.py','installed-consumer-runner-v4.py');p=base/newname;assert not p.exists();p.write_text(s)
print('Namedv4 code/data/controls only; originalv3 untouched')
