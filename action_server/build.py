import logging
import os
import platform
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# No real build, just download RCC at this point.

# Note: referenced here and in sema4ai.action_server._download_rcc
RCC_VERSION = "20.1.1"


CURDIR = Path(__file__).parent.absolute()


def _download_with_resume(url: str, target: Path) -> Path:
    import stat

    log.info(f"Downloading '{url}' to '{target}'")

    chunk_size = 1024 * 5
    with _open_urllib(url) as response:
        content_size = int(response.getheader("Content-Length") or -1)
        try:
            with open(target, "wb") as stream:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        # Note: in a bad connection it can return an empty chunk
                        # even before finishing (so, we resume it afterward if
                        # that was the case).
                        break
                    stream.write(chunk)
        except Exception:
            # Non-resumable case, just raise.
            if content_size <= 0:
                raise
            # Otherwise, keep on going to resume the download if it still
            # hasn't finished.

    MAX_TRIES = 10
    for i in range(MAX_TRIES):
        curr_file_size = _get_file_size(target)

        if content_size > 0:
            # It can be resumed.
            if content_size > curr_file_size:
                log.info(
                    f"Resuming download of '{url}' to '{target}' (downloaded {curr_file_size} of {content_size} (bytes))"
                )
                try:
                    _resume_download(url, target, chunk_size)
                except Exception:
                    if i == MAX_TRIES - 1:
                        raise
            else:
                break
        else:
            # It cannot be resumed: raise if everything wasn't downloaded.
            if content_size > curr_file_size:
                raise RuntimeError(
                    f"Unable to download {url} to {target}. Please retry later."
                )

    st = os.stat(target)
    os.chmod(target, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return target


def _open_urllib(url: str, headers=None):
    import urllib.request

    # Cloudflare seems to be blocking "User-Agent: Python-urllib/3.9".
    # Use a different one as that must be sorted out.
    use_headers = {"User-Agent": "Mozilla"}
    if headers:
        use_headers.update(headers)
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=use_headers), timeout=20
    )


def _get_file_size(filename: str | Path) -> int:
    # Check if file already exists and get downloaded size (if any)
    file_size = 0
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            file_size = os.fstat(f.fileno()).st_size
    return file_size


def _resume_download(url: str, filename: str | Path, chunk_size: int = 1024):
    """Downloads a file in chunks with resume support.

    Args:
        url: The URL of the file to download.
        filename: The filename to save the downloaded file.
        chunk_size: The size of each chunk to download (in bytes).
    """
    downloaded_size = _get_file_size(filename)
    # Set headers for resume download
    headers = {}
    if downloaded_size > 0:
        headers["Range"] = f"bytes={downloaded_size}-"

    with _open_urllib(url, headers) as response, open(filename, "ab") as stream:
        content_size = response.getheader("Content-Length")

        if not content_size:
            raise RuntimeError("Resuming downloads is not supported.")

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            stream.write(chunk)


def _download_rcc():
    """
    Downloads RCC in the place where the action server expects it.
    """

    if sys.platform == "win32":
        rcc_path = (
            CURDIR
            / "src"
            / "sema4ai"
            / "action_server"
            / "bin"
            / f"rcc-{RCC_VERSION}.exe"
        )
    else:
        rcc_path = (
            CURDIR / "src" / "sema4ai" / "action_server" / "bin" / f"rcc-{RCC_VERSION}"
        )

    machine = platform.machine()
    is_64 = not machine or "64" in machine

    if sys.platform == "win32":
        if is_64:
            relative_path = "/windows64/rcc.exe"
        else:
            raise RuntimeError("Unsupported platform (windows 32 bits)")

    elif sys.platform == "darwin":
        if machine == "arm64":
            relative_path = "/macos-arm64/rcc"
        else:
            relative_path = "/macos64/rcc"

    else:
        if is_64:
            relative_path = "/linux64/rcc"
        else:
            relative_path = "/linux32/rcc"

    prefix = f"https://cdn.sema4.ai/rcc/releases/v{RCC_VERSION}"
    rcc_url = prefix + relative_path

    print(f"Downloading '{rcc_url}' to '{rcc_path}'")
    return _download_with_resume(rcc_url, rcc_path)


def build(*args, **kwarg):
    if os.environ.get("ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD", "").lower().strip() in (
        "1",
        "true",
    ):
        return

    _download_rcc()


if __name__ == "__main__":
    build()
