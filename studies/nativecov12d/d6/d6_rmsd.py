import re, json, numpy as np
from scipy.optimize import linear_sum_assignment
M={'A':'C','C':'C','N':'N','NA':'N','OA':'O','O':'O'}
models,en,cur,ce=[],[],[],None
for l in open('d6_7kx5.dlg'):
    if not l.startswith('DOCKED: '): continue
    s=l[8:]
    if s.startswith('MODEL'): cur=[]
    elif 'Estimated Free Energy of Binding' in s: ce=float(re.search(r'=\s*(-?[0-9.]+)\s*kcal',s).group(1))
    elif s.startswith(('ATOM','HETATM')):
        t=s.split()[-1]
        if t in M: cur.append((M[t],np.array([float(s[30:38]),float(s[38:46]),float(s[46:54])])))
    elif s.startswith('ENDMDL'): models.append(cur); en.append(ce)
ref=[]
for l in open('../../../data/raw/7KX5.pdb'):
    if l.startswith('HETATM') and l[17:20].strip()=='X7V' and l[21]=='A':
        e=l[76:78].strip().upper()
        if e!='H': ref.append((e,np.array([float(l[30:38]),float(l[38:46]),float(l[46:54])])))
def arm(p):
    tot=n=0
    for e in 'CNO':
        R=np.array([x[1] for x in ref if x[0]==e]); P=np.array([x[1] for x in p if x[0]==e])
        assert len(R)==len(P),(e,len(R),len(P))
        d=((R[:,None]-P[None])**2).sum(-1); r,c=linear_sum_assignment(d); tot+=d[r,c].sum(); n+=len(R)
    return (tot/n)**.5
o=sorted(range(len(en)),key=lambda i:en[i]); rm=[arm(m) for m in models]
res={'top1_energy':en[o[0]],'top1_rmsd':round(rm[o[0]],3),'min_rmsd':round(min(rm),3),'n_le_2':int(sum(r<=2 for r in rm)),'n_models':len(rm),'pipeline_ok':bool(rm[o[0]]<=2.0),'ref_atoms':len(ref),'dlg_run_time_s':6965.343,'rmsd':'element-matched Hungarian assignment, heavy atoms, A->C typing map'}
json.dump(res,open('../../../results/native_covalent_12d_d6.json','w'),indent=1); print(res)
