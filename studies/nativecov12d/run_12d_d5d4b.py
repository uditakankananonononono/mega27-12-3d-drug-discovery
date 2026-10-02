"""12D amendment 1: D5 crystal-in-grid (autodock4 epdb) and D4b rigid alignment + mirror test."""
import sys, os, re, json, subprocess
HERE=os.path.dirname(os.path.abspath(__file__)); A=os.path.join(HERE,'../nativecov12a')
sys.path.insert(0,A)
import numpy as np
from rdkit import Chem
from run_12a import JOBS, build_matcher, lig_names, OUT
import run_12c_lib as L
AD4='/home/sandbox/work/12/bin/ad4/autodock4'
def kabsch(P,Q):  # rotate P onto Q; returns R,t, rmsd
    pc,qc=P.mean(0),Q.mean(0); H=(P-pc).T@(Q-qc); U,S,Vt=np.linalg.svd(H)
    d=np.sign(np.linalg.det(Vt.T@U.T)); D=np.diag([1,1,d]); R=Vt.T@D@U.T
    X=(R@(P-pc).T).T+qc
    return R,pc,qc,float(np.sqrt(((X-Q)**2).sum(1).mean()))
def kabsch_proper(P,Q): return kabsch(P,Q)[3]
def mirror_rmsd(P,Q):  # invert through centroid then proper fit
    pc=P.mean(0); return kabsch(2*pc-P,Q)[3]
res={}
for tag,j in JOBS.items():
    free,amol,q,ref,sdf2name=build_matcher(j)
    X=Chem.MolFromMolFile(j['sdf'],removeHs=True).GetConformer().GetPositions()
    lines=open(f'{OUT}/{tag}_lig_std.pdbqt').read().splitlines(keepends=True)
    atoms=[(i,l) for i,l in enumerate(lines) if l.startswith(('ATOM','HETATM'))]
    P=np.array([[float(l[30:38]),float(l[38:46]),float(l[46:54])] for i,l in atoms])
    perm={}
    for k,(i,l) in enumerate(atoms):
        if l.split()[-1].startswith('H'): continue
        d=np.linalg.norm(X-P[k],axis=1); m=int(d.argmin()); assert d[m]<1e-2; perm[k]=m   # pdbqt atom k -> sdf idx m
    sdf2k={m:k for k,m in perm.items()}
    # matched pairs by first MCS match (pdbqt atom k, crystal xyz)
    fm=free.GetSubstructMatches(q,maxMatches=5000)[0]; am=amol.GetSubstructMatches(q,maxMatches=5000)[0]
    pairs=[(sdf2k[fi],ref[sdf2name[ai]]) for fi,ai in zip(fm,am) if fi in sdf2k and sdf2name.get(ai) in ref]
    ks=[k for k,_ in pairs]; Q=np.array([c for _,c in pairs]); Pm=P[ks]
    R,pc,qc,fit=kabsch(Pm,Q)
    Pall=(R@(P-pc).T).T+qc
    # write fitted pdbqt
    out=lines[:]
    for k,(i,l) in enumerate(atoms):
        x,y,z=Pall[k]; out[i]=l[:30]+'%8.3f%8.3f%8.3f'%(x,y,z)+l[54:]
    d5=os.path.join(HERE,'d5'); open(f'{d5}/{tag}_crystalfit.pdbqt','w').write(''.join(out))
    fld=open(f'{OUT}/{tag}_rec_rigid.maps.fld').read()
    gpf=open(f'{OUT}/{tag}_rec_rigid.gpf').read()
    ltypes=re.search(r'^ligand_types (.*)$',gpf,re.M).group(1)
    maps=re.findall(r'^map (\S+)$',gpf,re.M)
    c=Pall.mean(0)
    dpf=f"""autodock_parameter_version 4.2
outlev 1
parameter_file {OUT}/boron-silicon-atom_par.dat
intelec
seed 12345
ligand_types {ltypes}
fld {OUT}/{tag}_rec_rigid.maps.fld
""" + ''.join(f"map {OUT}/{m}\n" for m in maps) + f"""elecmap {OUT}/{tag}_rec_rigid.e.map
desolvmap {OUT}/{tag}_rec_rigid.d.map
move {d5}/{tag}_crystalfit.pdbqt
about {c[0]:.3f} {c[1]:.3f} {c[2]:.3f}
epdb
"""
    open(f'{d5}/{tag}_epdb.dpf','w').write(dpf)
    r=subprocess.run([AD4,'-p',f'{d5}/{tag}_epdb.dpf','-l',f'{d5}/{tag}_epdb.dlg'],capture_output=True,text=True,cwd=OUT)
    txt=open(f'{d5}/{tag}_epdb.dlg').read() if os.path.exists(f'{d5}/{tag}_epdb.dlg') else r.stdout+r.stderr
    inter=re.search(r'Intermolecular Energy\s*=\s*(-?[0-9.]+)',txt) or re.search(r'intermolecular.*?(-?[0-9.]+)',txt,re.I)
    internal=re.search(r'Internal Energy.*?=\s*(-?[0-9.]+)',txt)
    # docked C1 pooled intermolecular energies
    names=lig_names(f'{OUT}/{tag}_lig_std.pdbqt'); inters=[]
    for s in (0,1,2):
        for l in open(f'{OUT}/dock_{tag}_C1_seed{s}.dlg'):
            m=re.search(r'Final Intermolecular Energy\s*=\s*(-?[0-9.]+)',l)
            if m: inters.append(float(m.group(1)))
    e_in=float(inter.group(1)) if inter else None
    res[tag]={'fit_rmsd_matched_atoms':round(fit,3),'n_matched':len(ks),'epdb_rc':r.returncode,
        'crystalfit_intermolecular':e_in,'docked_C1_inter_best':min(inters),'docked_C1_inter_worst':max(inters),'n_docked':len(inters),
        'crystal_implausible':None if e_in is None else bool(e_in>0 or e_in>max(inters)),'epdb_text_tail':txt[-400:] if e_in is None else ''}
    # D4b with the corrected mapping, all 30 poses per arm
    d4={}
    for arm in ('C1','C2'):
        v='reactive' if arm=='C2' else 'std'
        lines2=[l for l in open(f'{OUT}/{tag}_lig_{v}.pdbqt') if l.startswith(('ATOM','HETATM'))]
        un,mi=[],[]
        for s in (0,1,2):
            for pose,e in L.all_models(f'{OUT}/dock_{tag}_{arm}_seed{s}.dlg',lig_names(f'{OUT}/{tag}_lig_{v}.pdbqt')):
                # pose keyed 1..N heavy order of PDBQT heavy atoms; map via perm (heavy order)
                heavy_k=[k for k in range(len(lines2)) if not lines2[k].split()[-1].startswith('H')]
                Pp=np.array([pose[i+1] for i in range(len(pose))])
                sel=Pp[[hk for hk in ks]] if False else None
                # pose dict is keyed by position among names list; names are PDBQT order incl. polar H's filtered? use same index as ks
                Pk=np.array([pose[k+1] for k in ks])
                un.append(kabsch(Pk,Q)[3]); mi.append(mirror_rmsd(Pk,Q))
        d4[arm]={'unmirrored_min':round(min(un),3),'unmirrored_median':round(float(np.median(un)),3),
                 'mirrored_min':round(min(mi),3),'mirrored_median':round(float(np.median(mi)),3),
                 'flag_mirror':bool(min(mi)<=2.0 and min(un)>3.0)}
    res[tag]['D4b']=d4
json.dump(res,open(os.path.join(HERE,'../../results/native_covalent_12d_d5d4b.json'),'w'),indent=1)
print(json.dumps(res,indent=1))
