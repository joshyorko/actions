from pathlib import Path
OUT=Path(__file__).parent
s=(OUT/'preserve_exact_pytest38_once_v2.py').read_text()
s=s.replace("        os.fsync(stream.fileno())\n\n\ndef meta", "        os.fsync(stream.fileno())\n    directory_fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)\n    try:os.fsync(directory_fd)\n    finally:os.close(directory_fd)\n\n\ndef meta",1)
s=s.replace("need(int(Decimal(member.pax_headers['mtime']) * 1000000000) == row['mtime_ns']", "need(Decimal(member.pax_headers['mtime']) * 1000000000 == row['mtime_ns']")
p=OUT/'preserve_exact_pytest38_once_v3.py';p.open('x').write(s);p.chmod(0o600)
t=(OUT/'test_pytest38_archiver_controls_v2.py').read_text().replace("HERE/'preserve_exact_pytest38_once_v2.py'","HERE/'preserve_exact_pytest38_once_v3.py'")
t+='''\n
def test_sub_ns_metadata_is_not_silently_truncated(sample):
    entries,path=archive_changed(sample,lambda rows:rows[0][0].pax_headers.update(mtime='1700000000.0000000011'))
    with pytest.raises(RuntimeError,match='ARCHIVE_EXACT_MTIME'):m.verify_archive(path,entries)

def test_index_file_and_directory_fsynced_before_remove(sample,tmp_path,monkeypatch):
    root,entries,archive=sample;m.create_archive(archive,entries);events=[];original=m.os.fsync
    def sync(fd):events.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file');original(fd)
    monkeypatch.setattr(m.os,'fsync',sync)
    def remove():assert events==['file','directory']
    m.index_before_remove(tmp_path/'index',entries,archive,lambda:None,remove)
'''
p=OUT/'test_pytest38_archiver_controls_v3.py';p.open('x').write(t);p.chmod(0o600)
