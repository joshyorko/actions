from contextlib import contextmanager
import pytest
from contract_tests.test_generic_projection import case as case, projection, mutate
from actions.server.run_outputs.service import AccessDenied
pytest_plugins=['action_server_tests.foundry_fixtures']

def test_terminal_source_identity_change_during_read_must_deny(case,monkeypatch):
    c=case
    run,fence,_=c.publish()
    mutate(c,run,lambda value:value['result'].update(sourceArtifactDigest='sha256:'+'a'*64))
    original=c.provider.open
    @contextmanager
    def mutate_after_read(*args):
        with original(*args) as reader:
            yield reader
        mutate(c,run,lambda value:value['result'].update(sourceArtifactDigest='sha256:'+'b'*64))
    monkeypatch.setattr(c.provider,'open',mutate_after_read)
    with pytest.raises((AccessDenied,ValueError)):
        projection(c,run,fence)
