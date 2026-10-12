import hashlib, io, json, pathlib, posixpath, struct, subprocess, tarfile, zipfile

ROOT = pathlib.Path(__file__).parent
SOURCE = '65c0cb832e43f31d908aa3991e6c38d01ff964a9'
def sha(data):
    return hashlib.sha256(data).hexdigest()

def safe_name(name):
    p = pathlib.PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
    return name

results = []
for platform, provenance, ui, wrapper_id, expected_zip in [
    ('macos', '11689509792', '11689584989', '11689684579', 'ad92a5cb1d9e2f5e77d5aac625f92226650e5c0b155d7cba5a8f0ed57a85002e'),
    ('windows', '11690323645', '11689474294', '11689644046', '93cfc84ec64e22389d781fd2bcccbc3fe5c1a41d6e1538cc381ca52b7de758f0'),
]:
    zip_bytes = (ROOT / f'artifact-{provenance}.zip').read_bytes()
    assert sha(zip_bytes) == expected_zip
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        assert z.namelist() == ['native-artifact-provenance.tar']
        tar_bytes = z.read(z.namelist()[0])
    manifest_bytes = (ROOT / ui / 'native-artifact-manifest.json').read_bytes()
    inventory_bytes = (ROOT / ui / 'native-artifact-tree-inventory.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    inventory = json.loads(inventory_bytes)
    assert manifest['source_sha'] == SOURCE
    inv = {entry['path']:entry for entry in inventory}
    assert len(inv) == len(inventory)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as t:
        members = {safe_name(m.name):m for m in t.getmembers()}
        assert len(members) == len(t.getmembers())
        assert set(members) == {'dist/action-server', 'output/native-artifact-manifest.json', 'output/native-artifact-tree-inventory.json'} | {'dist/action-server/'+p for p in inv}
        assert t.extractfile(members['output/native-artifact-manifest.json']).read() == manifest_bytes
        assert t.extractfile(members['output/native-artifact-tree-inventory.json']).read() == inventory_bytes
        def resolve(name):
            pieces = name.split('/')
            for i in range(1,len(pieces)+1):
                part = '/'.join(pieces[:i])
                m = members.get(part)
                if m and m.issym():
                    assert not posixpath.isabs(m.linkname) and '\\' not in m.linkname
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(part),m.linkname))
                    assert target.startswith('dist/action-server/')
                    tail = '/'.join(pieces[i:])
                    return resolve(posixpath.join(target,tail) if tail else target)
            return name
        filehashes = {}
        treehash = hashlib.sha256()
        for path in sorted(inv):
            entry = inv[path]
            name = 'dist/action-server/'+path
            m = members[name]
            kind = 'symlink' if m.issym() else 'directory' if m.isdir() else 'file' if m.isfile() else None
            assert kind == entry['kind'] and m.mode == entry['mode'], path
            if kind == 'symlink':
                assert m.linkname == entry['link_target'], path
                resolved = resolve(name)
                assert resolved in members, (path,resolved)
                if members[resolved].isfile():
                    assert sha(t.extractfile(members[resolved]).read()) == entry['content_sha256']
                    filehashes[path] = entry['content_sha256']
            elif kind == 'file':
                digest = sha(t.extractfile(m).read())
                assert digest == entry['content_sha256'], path
                filehashes[path] = digest
            treehash.update(path.encode()+b'\0'+str(m.mode & 0o777).encode()+b'\0')
            if kind == 'symlink': treehash.update(b'link\0'+m.linkname.encode()+b'\0')
            elif kind == 'directory': treehash.update(b'directory\0')
            else: treehash.update(b'file\0'+bytes.fromhex(filehashes[path]))
        assert treehash.hexdigest() == manifest['artifacts']['frozen']['frozen_package_tree_sha256']
        frozen_name = manifest['artifact_downloads']['frozen']['archive_path']
        frozen_digest = sha(t.extractfile(members[frozen_name]).read())
        assert frozen_digest == manifest['artifacts']['frozen']['sha256']
    with zipfile.ZipFile(ROOT / f'artifact-{wrapper_id}.zip') as z:
        assert len(z.namelist()) == 1
        wrapper = z.read(z.namelist()[0])
    assert sha(wrapper) == manifest['artifacts']['go-wrapper']['sha256']
    eocd = wrapper.rfind(b'PK\x05\x06')
    assert eocd >= 0
    fields = struct.unpack_from('<4s4H2IH',wrapper,eocd)
    cdsize,cdoffset,comment_length = fields[5],fields[6],fields[7]
    start = eocd - cdsize - cdoffset
    assets = wrapper[start:eocd+22+comment_length]
    assert assets[:4] == b'PK\x03\x04'
    assert sha(assets) == manifest['artifacts']['go-wrapper']['assets_zip_sha256']
    asset_files = {}
    with zipfile.ZipFile(io.BytesIO(assets)) as z:
        names = [safe_name(n) for n in z.namelist()]
        assert len(names) == len(set(names))
        for name in names:
            if not z.getinfo(name).is_dir(): asset_files[name] = sha(z.read(name))
    assert asset_files == filehashes, (platform,len(asset_files),len(filehashes))
    content_digest = hashlib.sha256()
    for path in sorted(asset_files): content_digest.update(path.encode()+b'\0'+bytes.fromhex(asset_files[path]))
    assert content_digest.hexdigest() == manifest['artifacts']['go-wrapper']['embedded_files_sha256']
    source_digest = hashlib.sha256()
    for path in manifest['artifacts']['go-wrapper']['wrapper_source_files']:
        data = subprocess.check_output(['git','-C','/workspace/engineering/pr310','show','f506a04e240feba048bf10e32bccebf591674f9e:action_server/'+path])
        source_digest.update(path.encode()+b'\0'+hashlib.sha256(data).digest())
    assert source_digest.hexdigest() == manifest['artifacts']['go-wrapper']['wrapper_source_sha256']
    result = {'platform':platform,'source':SOURCE,'provenance_artifact':provenance,'wrapper_artifact':wrapper_id,'tar_sha256':sha(tar_bytes),'manifest_sha256':sha(manifest_bytes),'inventory_sha256':sha(inventory_bytes),'entries':len(inv),'files':len(asset_files),'all_tar_member_mode_kind_link_and_file_hashes':'PASS','frozen_sha256':frozen_digest,'wrapper_sha256':sha(wrapper),'original_embedded_assets_zip_sha256':sha(assets),'embedded_file_set_hash_and_source_digest':'PASS'}
    results.append(result)
    print(json.dumps(result))
(ROOT/'independent-artifact-byte-verification.json').write_text(json.dumps(results,indent=2)+'\n')
