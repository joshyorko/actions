import pathlib,urllib.request,hashlib,zipfile,json
root=pathlib.Path('/workspace/successor-evidence/pr307-packaged')
root.mkdir(mode=0o700,exist_ok=True)
archive=root/'actions-runtime-dist.zip'
with urllib.request.urlopen('REDACTED_EXPIRED_DOWNLOAD_URL',timeout=45) as response, archive.open('xb') as output:
 while data:=response.read(1048576): output.write(data)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest=='85d82c02bcfac718ac822b5f53308f5662dab222a6d97f767ecba4ae86bb106a',digest
with zipfile.ZipFile(archive) as z:
 for info in z.infolist():
  assert len(pathlib.PurePosixPath(info.filename).parts)==1 and not info.is_dir(),info.filename
  assert info.file_size<60000000,info.filename
  (root/info.filename).write_bytes(z.read(info))
print(json.dumps({'archive_sha256':digest,'members':sorted(p.name for p in root.iterdir())},indent=2))
