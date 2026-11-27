import logging
import platform
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Note: also referenced in action_server/build.py
# Using joshyorko/rcc open-source version
RCC_VERSION = "18.19.12"


def get_default_rcc_location() -> Path:
    CURDIR = Path(__file__).parent.absolute()
    if sys.platform == "win32":
        rcc_path = CURDIR / "bin" / f"rcc-{RCC_VERSION}.exe"
    else:
        rcc_path = CURDIR / "bin" / f"rcc-{RCC_VERSION}"
    return rcc_path


def download_rcc(
    target: Optional[str] = None,
    force=False,
) -> Path:
    """
    Downloads RCC in the place where the action server expects it.
    """
    import os

    from actions.server._rcc_platform import expected_sha256, rcc_asset_name, verify_rcc

    asset_name = rcc_asset_name(sys.platform, platform.machine())
    expected_sha256(RCC_VERSION, asset_name)

    from actions.server._common.system_mutex import timed_acquire_mutex

    if target:
        rcc_path = Path(target)
    else:
        rcc_path = get_default_rcc_location()

    if not force:
        if rcc_path.exists():
            verify_rcc(rcc_path, RCC_VERSION, asset_name)
            return rcc_path

        log.info(f"RCC not available at: {rcc_path}. Downloading.")

    rcc_path.parent.mkdir(parents=True, exist_ok=True)

    # GitHub releases URL format
    rcc_url = f"https://github.com/joshyorko/rcc/releases/download/v{RCC_VERSION}/{asset_name}"

    timeout = 300.0

    if "ACTIONS_RUNTIME_RCC_DOWNLOAD_TIMEOUT" in os.environ:
        # Users can override timeout by setting the environment variable.
        timeout = float(os.environ["ACTIONS_RUNTIME_RCC_DOWNLOAD_TIMEOUT"])

    with timed_acquire_mutex(
        "action_server_rcc_download", timeout=timeout, raise_error_on_timeout=True
    ):
        if not force and rcc_path.exists():
            # It was downloaded by some other process while we were waiting for the mutex.
            verify_rcc(rcc_path, RCC_VERSION, asset_name)
            return rcc_path

        import actions_http

        temporary = rcc_path.with_name(rcc_path.name + ".download")
        try:
            status = actions_http.download_with_resume(
                rcc_url, temporary, make_executable=True, overwrite_existing=True
            )
            if status.status in (
                actions_http.DownloadStatus.HTTP_ERROR,
                actions_http.DownloadStatus.PARTIAL,
            ):
                raise RuntimeError(f"Failed to download RCC: {status.status}")
            verify_rcc(temporary, RCC_VERSION, asset_name)
            temporary.replace(rcc_path)
        finally:
            temporary.unlink(missing_ok=True)

    return rcc_path


if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("Logging setup")

    ret = download_rcc(
        target="/tmp/actions-runtime/bin/rcc-17.28.4",
        force=True,
    )
    log.info("Downloaded: %s", ret)
