"""Post-outcome paired DeLong normal CIs for four predeclared seed-0 contrasts.

Same 14 pose-available held-out compounds (9 positive, 5 negative) as the
four paired tests in the preregistered study12_ablation.py. Does not change
that study's gates. These are exploratory single-split intervals, NOT CIs
for the five-split AUROC means or for all conceivable arm comparisons.
"""
import json
from pathlib import Path
import numpy as np
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[1]
j=json.loads((ROOT/'results/ablation.json').read_text())
s=j['seed0_scores'];y=np.array(s['y_pose'],bool)
assert len(y)==14 and int(y.sum())==9
pairs={
 'gnnpose_vs_gnn2d':('gnnpose','gnn2d_pose_subset'),
 'gnnpose_vs_gnnrand':('gnnpose','gnnrand'),
 'fusion_vs_gnnpose':('fusion','gnnpose'),
 'gnnpose_vs_gnnpose_shuf':('gnnpose','gnnpose_shuf'),
}
def placements(score):
    pos,neg=score[y],score[~y]
    c=(pos[:,None]>neg[None,:]).astype(float)+.5*(pos[:,None]==neg[None,:])
    return c.mean(1),c.mean(0)
out={'design':__doc__.strip(),'n_test':len(y),'n_positive':int(y.sum()),'n_negative':int((~y).sum()),'comparisons':{}}
for name,(a,b) in pairs.items():
    va,na=placements(np.array(s[a],float));vb,nb=placements(np.array(s[b],float))
    diff=float(va.mean()-vb.mean())
    variance=float(np.var(va-vb,ddof=1)/y.sum()+np.var(na-nb,ddof=1)/(~y).sum())
    se=float(np.sqrt(variance));ci=[diff-1.96*se,diff+1.96*se]
    p=float(2*norm.sf(abs(diff)/se)) if se>0 else (1. if diff==0 else 0.)
    assert abs(p-j['delong_seed0'][name])<1e-10,(name,p,j['delong_seed0'][name])
    out['comparisons'][name]={'arm_a':a,'arm_b':b,'auroc_a':float(va.mean()),'auroc_b':float(vb.mean()),
        'difference':diff,'se':se,'ci95_normal_unbounded':ci,'p_two_sided':p}
(ROOT/'results/ablation_delong_intervals.json').write_text(json.dumps(out,indent=1)+'\n')
print(json.dumps(out['comparisons'],indent=1))
