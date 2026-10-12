import pytest
from types import SimpleNamespace

@pytest.fixture(autouse=True)
def simulate_windows_missing_posix_constants(request, monkeypatch):
    actual = request.module._harness
    def safe_harness():
        module = actual()
        def reject_kernel(*_args, **_kwargs):
            raise AssertionError("unexpected real process-lifecycle primitive")
        fields = {k: v for k, v in vars(module.os).items() if k != "WNOHANG"}
        fields.update(waitpid=reject_kernel, kill=reject_kernel, killpg=reject_kernel, getpid=lambda: 10001)
        module.os = SimpleNamespace(**fields)
        module._fallback_reap_after_error = reject_kernel
        return module
    monkeypatch.setattr(request.module, "_harness", safe_harness)
