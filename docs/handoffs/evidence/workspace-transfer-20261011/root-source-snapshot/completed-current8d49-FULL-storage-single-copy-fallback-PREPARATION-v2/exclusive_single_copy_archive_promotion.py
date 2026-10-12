"""One exclusive same-filesystem promotion; no second data copy."""
from pathlib import Path
import os,stat

def promote_verified_archive(source,destination,*,expected_sha,sha,fsync_path):
    source,destination=Path(source),Path(destination)
    meta=source.lstat()
    assert stat.S_ISREG(meta.st_mode) and not source.is_symlink() and meta.st_nlink==1
    assert stat.S_IMODE(meta.st_mode)==0o600 and meta.st_uid==os.getuid() and meta.st_gid==os.getgid()
    assert not destination.exists() and not destination.is_symlink()
    assert destination.parent.is_dir() and not destination.parent.is_symlink()
    assert meta.st_dev==destination.parent.stat().st_dev,'CROSS_FILESYSTEM_PROMOTION_REFUSED'
    assert sha(source)==expected_sha
    os.link(source,destination,follow_symlinks=False)  # Exclusive atomic name creation, no overwrite.
    new=destination.lstat();old=source.lstat()
    assert (new.st_dev,new.st_ino)==(old.st_dev,old.st_ino)==(meta.st_dev,meta.st_ino)
    assert new.st_nlink==old.st_nlink==2 and stat.S_IMODE(new.st_mode)==0o600
    assert (new.st_uid,new.st_gid,new.st_size,new.st_mtime_ns)==(meta.st_uid,meta.st_gid,meta.st_size,meta.st_mtime_ns)
    assert sha(destination)==expected_sha
    fsync_path(destination);fsync_path(destination.parent)
    source.unlink();fsync_path(source.parent)
    assert not source.exists() and not source.is_symlink()
    new=destination.lstat();assert new.st_nlink==1 and sha(destination)==expected_sha
    return str(destination)
