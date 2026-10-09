"""Persist completed jobs before the runner advances. Scientific settings are unchanged."""
import pathlib, subprocess, sys
root=pathlib.Path(__file__).resolve().parents[3]
here=pathlib.Path(__file__).resolve().parent
remote_url='git@github.com:uditakankananonononono/mega27-12-3d-drug-discovery.git'
key=sys.argv[1]
def git(*args): return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
files=[here/'dock_status.json',here/'dock.log']+[p for p in here.glob('dock_'+key+'.*') if p.suffix in ('.dlg','.xml')]
git('add','-f',*[str(p.relative_to(root)) for p in files if p.exists()])
if git('diff','--cached','--name-only'):
 git('commit','-m',f'12E-CR recovery checkpoint: {key} completed; no verdict yet')
git('push',remote_url,'HEAD:main')
head=git('rev-parse','HEAD')
remote=git('ls-remote',remote_url,'refs/heads/main').split()[0]
if head!=remote: raise RuntimeError('Checkpoint readback mismatch; stop before next job')
print('CHECKPOINT_PUSHED',key,head,flush=True)
