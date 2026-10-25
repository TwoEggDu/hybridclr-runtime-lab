"""Cross-check snapshot buffers with the unmodified Unity Memory Profiler 1.1.0 reader.
Generates only an ignored Editor analysis project; never changes Player inputs.
"""
import argparse,hashlib,io,json,shutil,tarfile,urllib.request
from pathlib import Path
import receipts,lifetime_lab
from prepare import ROOT,tree_digest
from unity_snapshot import Snapshot
URL='https://packages.unity.com/com.unity.memoryprofiler/-/com.unity.memoryprofiler-1.1.0.tgz'
PACKAGE_SHA='c01e96c3da508dc1d37591f0ce47db82dbc316c99154d52d0f114d81cd83b270'
TREE_SHA='0e5290f5b19ec4e07a9bb8779303624ab2fc441b3aad802ab56f1dced9783d93'
ART=ROOT/'artifacts/gc-roots'
def verify():
 data=json.loads((ART/'unity-reader-results.json').read_text())
 expected={p.relative_to(ROOT).as_posix() for p in (ART/'snapshots').rglob('*.snap')}
 if len(expected)!=21 or len(data['entries'])!=189 or {r['file'] for r in data['entries']}!=expected:raise ValueError('Incomplete official reader matrix')
 for name in expected:
  if sorted(r['entry'] for r in data['entries'] if r['file']==name)!=[0,3,4,15,18,19,21,23,29]:raise ValueError('Entry set mismatch')
 for row in data['entries']:
  chunks=Snapshot(ROOT/row['file']).entry(row['entry'])
  if row['count']!=len(chunks) or row['sha256']!=hashlib.sha256(b''.join(chunks)).hexdigest():raise ValueError('Official reader disagreement')
 print('OFFICIAL READER PASS',len(data['entries']),'buffers',flush=True)
def run(editor):
 lock=json.loads((ROOT/'lab-lock.json').read_text());receipts.editor_identity(editor,lock)
 package=ROOT/'.local/memoryprofiler-1.1.0'
 if not package.exists():
  data=urllib.request.urlopen(URL,timeout=60).read()
  if hashlib.sha256(data).hexdigest()!=PACKAGE_SHA:raise ValueError('Package archive hash mismatch')
  package.mkdir(parents=True)
  with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tf:
   for member in tf.getmembers():
    if not member.isfile():continue
    dest=package/Path(member.name).relative_to('package')
    if not dest.resolve().is_relative_to(package.resolve()):raise ValueError('Unsafe package member')
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tf.extractfile(member).read())
 if tree_digest(package)!=TREE_SHA:raise ValueError('Official package source changed')
 project=ROOT/'.local/snapshot-reader-project';assets=project/'Assets/Editor';assets.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(ROOT/'tools/UnitySnapshotCheck.cs',assets/'UnitySnapshotCheck.cs')
 (assets/'SnapshotCheck.asmdef').write_text(json.dumps(dict(name='SnapshotCheck',includePlatforms=['Editor'],allowUnsafeCode=True)))
 packages=project/'Packages';packages.mkdir(exist_ok=True);(packages/'manifest.json').write_text(json.dumps({'dependencies':{'com.unity.memoryprofiler':'file:../../memoryprofiler-1.1.0'}}))
 settings=project/'ProjectSettings';settings.mkdir(exist_ok=True);shutil.copyfile(ROOT/'projects/gc-roots/ProjectSettings/ProjectVersion.txt',settings/'ProjectVersion.txt')
 log=ART/'unity-reader.log';receipts.fresh_log(log)
 pid,code=lifetime_lab.process([editor,'-batchmode','-nographics','-quit','-projectPath',project,'-executeMethod','UnitySnapshotCheck.Run','--lab-root',ROOT,'-logFile',log],600)
 if code or 'GCR_OFFICIAL_READER_PASS entries=189' not in log.read_text(encoding='utf-8-sig'):raise RuntimeError('Official reader failed')
 verify()
 receipts.write(ART/'official-reader-status.json',dict(status='complete',build_id=json.loads((ART/'build-lock.json').read_text())['build_id'],pid=pid,exit_code=code,package_url=URL,package_sha256=PACKAGE_SHA,package_tree_sha256=TREE_SHA,editor_product_version=lock['editor']['product_version'],log_sha256={p.relative_to(ART).as_posix():receipts.sha(p) for p in [log,ART/'unity-reader-results.json']},source_sha256={p.relative_to(ROOT).as_posix():receipts.sha(p) for p in [ROOT/'tools/UnitySnapshotCheck.cs',ROOT/'tools/check_snapshots_unity.py']}))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--editor',type=Path);args=p.parse_args()
 if args.editor:run(args.editor)
 else:verify()
if __name__=='__main__':main()
