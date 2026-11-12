"""Compatibility entrypoint for the retired CDN frontend build collection."""

from invoke import Context, task


@task
def build_frontend_from_cdn(ctx: Context, version: str = "latest"):
    """Reject upstream executable extraction before any build side effects."""
    raise RuntimeError(
        "CDN frontend extraction is retired. Use inv build-frontend to build "
        "both Runtime and Canvas entrypoints from this checkout and its lockfile. "
        "An upstream executable is not an owned frontend build input."
    )
