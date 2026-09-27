"""Lane 12 item 5: hydration-aware scoring, per
docs/PREREG_HYDRATION_20260928.md (committed pre-outcome, 57b9d39).

Part A: conserved hydration-site map across 8 public Mpro structures.
Part B: explicit-water redock of X7V/7KX5 (descriptive, n=1).
Part C: gated arm J (mlp7 + h_occ + h_br) vs mlp7 on the committed
ablation poses/splits/statistics. No redocking; no label use in features.
"""
import json
from pathlib import Path
import numpy as np
import torch
from sklearn.metrics import roc_auc_score

import subprocess, sys
from drugdisc.prep import parse_pdb_atoms, hetatm_residues
from drugdisc.dock import dock_ligand
from drugdisc.geometry import parse_pose_pdbqt, assignment_rmsd
from studies.study12_scaffold_split import (load_records, scaffolds,
                                            scaffold_split, delong_p)
from studies.study12_ablation import rdkit7, train_mlp

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
RES = ROOT / "results"
POSES = RES / "ablation_poses"
STRUCTS = ["6LU7", "6YB7", "7BB2", "7BQY", "7KX5", "7RFS", "8HUR", "8V8E"]
OCC_R = 2.5
BR_LO, BR_HI = 2.5, 3.5
MIN_CONS = 3


def kabsch(mobile, ref):
    mc, rc = mobile.mean(0), ref.mean(0)
    H = (mobile - mc).T @ (ref - rc)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
    return R, rc - mc @ R.T


def part_a():
    print("PART A", flush=True)
    atoms7 = parse_pdb_atoms(str(RAW / "7KX5.pdb"))
    lig = np.array([[a["x"], a["y"], a["z"]] for a in atoms7
                    if a["record"] == "HETATM" and a["resname"] == "X7V"
                    and a["chain"] == "A" and a["element"] != "H"])
    prot7 = [a for a in atoms7 if a["record"] == "ATOM" and a["chain"] == "A"]
    site_res = sorted({a["resseq"] for a in prot7
                       if np.min(np.linalg.norm(
                           lig - np.array([a["x"], a["y"], a["z"]]), axis=1)) <= 8.0})
    ca7 = {a["resseq"]: np.array([a["x"], a["y"], a["z"]])
           for a in prot7 if a["name"] == "CA" and a["resseq"] in site_res}
    print(f"binding-site residues: {len(site_res)}, CA anchors: {len(ca7)}", flush=True)
    box = json.loads((RAW / "box_7kx5.json").read_text())
    cen = np.array(box["center"]); half = np.array(box["size"]) / 2
    pts = []  # (structure, xyz)
    align = {}
    for st in STRUCTS:
        atoms = parse_pdb_atoms(str(RAW / f"{st}.pdb"))
        cas = {a["resseq"]: np.array([a["x"], a["y"], a["z"]])
               for a in atoms if a["record"] == "ATOM" and a["chain"] == "A"
               and a["name"] == "CA"}
        matched = sorted(set(ca7) & set(cas))
        if len(matched) < 20:
            print(f"  {st}: SKIPPED ({len(matched)} matched CA)", flush=True)
            align[st] = {"status": "skipped", "matched_ca": len(matched)}
            continue
        ref = np.array([ca7[r] for r in matched])
        mob = np.array([cas[r] for r in matched])
        R, t = kabsch(mob, ref)
        rms = float(np.sqrt(((mob @ R.T + t - ref) ** 2).sum(1).mean()))
        wat = [a for a in atoms if a["record"] == "HETATM"
               and a["resname"] == "HOH" and a["chain"] in ("A", " ")]
        n_in = 0
        for a in wat:
            xyz = np.array([a["x"], a["y"], a["z"]]) @ R.T + t
            if np.all(np.abs(xyz - cen) <= half):
                pts.append((st, xyz)); n_in += 1
        align[st] = {"status": "aligned", "matched_ca": len(matched),
                     "align_rmsd_A": round(rms, 3), "waters_chainA": len(wat),
                     "waters_in_box": n_in}
        print(f"  {st}: {len(matched)} CA, rmsd {rms:.2f} A, {n_in} waters in box", flush=True)
    # greedy seed-based clustering at 1.5 A (locked)
    remaining = list(pts)
    clusters = []
    while remaining:
        counts = {}
        for st, _ in remaining:
            counts[st] = counts.get(st, 0) + 1
        top = max(counts, key=counts.get)
        seed = next(x for s, x in remaining if s == top)
        cl = [(s, x) for s, x in remaining
              if np.linalg.norm(x - seed) <= 1.5]
        remaining = [(s, x) for s, x in remaining
                     if np.linalg.norm(x - seed) > 1.5]
        xyz = np.array([x for _, x in cl])
        clusters.append({"centroid": xyz.mean(0).round(3).tolist(),
                         "n_waters": len(cl),
                         "conservation": len({s for s, _ in cl}),
                         "structures": sorted({s for s, _ in cl})})
    clusters.sort(key=lambda c: -c["conservation"])
    out = {"box": box, "alignment": align, "n_waters_in_box": len(pts),
           "clusters": clusters}
    (RES / "hydration_sites.json").write_text(json.dumps(out, indent=1))
    print(f"  {len(pts)} waters -> {len(clusters)} clusters; "
          f"conservation histogram: "
          f"{ {k: sum(1 for c in clusters if c['conservation'] == k) for k in range(1, 9)} }", flush=True)
    return out


def part_b():
    print("PART B", flush=True)
    lines = []
    for line in open(RAW / "7KX5.pdb"):
        rec = line[:6].strip()
        if (rec == "ATOM" and line[21] == "A") or \
           (rec == "HETATM" and line[17:20].strip() == "HOH"):
            lines.append(line)
    hoh_pdb = RAW / "7KX5_A_protein_hoh.pdb"
    hoh_pdb.write_text("".join(lines) + "TER\nEND\n")
    hoh_pdbqt = RAW / "7KX5_A_receptor_hoh.pdbqt"
    if not hoh_pdbqt.exists():
        # mk_prepare_receptor.py lacks +x here; invoke via the interpreter.
        subprocess.run([sys.executable, "/home/sandbox/.local/bin/mk_prepare_receptor.py",
                        "--read_pdb", str(hoh_pdb), "-o", str(hoh_pdbqt), "-p"],
                       check=True, capture_output=True, text=True, timeout=300)
        if not hoh_pdbqt.exists() and Path(str(hoh_pdbqt) + ".pdbqt").exists():
            Path(str(hoh_pdbqt) + ".pdbqt").rename(hoh_pdbqt)
    box = json.loads((RAW / "box_7kx5.json").read_text())
    result, pose = dock_ligand(str(hoh_pdbqt), str(RAW / "X7V_ligand.pdbqt"),
                               box["center"], box["size"],
                               ligand_name="JUN8-76-3A", exhaustiveness=16,
                               n_poses=9, cpu=2)
    (RAW / "X7V_redock_pose_hoh.pdbqt").write_text(pose)
    ref_atoms = hetatm_residues(str(RAW / "7KX5.pdb"), "X7V", "A")
    ref_coords = np.array([[a["x"], a["y"], a["z"]] for a in ref_atoms])
    ref_elements = [a["element"].capitalize() for a in ref_atoms]
    mob_coords, mob_elements = parse_pose_pdbqt(pose)
    rmsd = assignment_rmsd(ref_coords, ref_elements, mob_coords, mob_elements)
    apo = json.loads((RES / "redock_7KX5.json").read_text())
    out = {"best_affinity_kcal_mol": result.best_affinity,
           "all_affinities": result.all_affinities, "rmsd_A": rmsd,
           "apo_rmsd_A": apo["rmsd_A"],
           "apo_best_affinity_kcal_mol": apo["best_affinity_kcal_mol"],
           "note": "n=1 descriptive; no statistical claim"}
    print(f"  explicit-water redock rmsd {rmsd:.3f} A (apo {apo['rmsd_A']:.3f}), "
          f"aff {result.best_affinity} (apo {apo['best_affinity_kcal_mol']})", flush=True)
    return out


def part_c(sites_json):
    print("PART C", flush=True)
    sites = np.array([c["centroid"] for c in sites_json["clusters"]
                      if c["conservation"] >= MIN_CONS])
    print(f"  conserved sites (>={MIN_CONS}): {len(sites)}", flush=True)
    records = load_records()
    y = np.array([1 if r["label"] == "active" else 0 for r in records])
    scaf = scaffolds(records)
    ok = [i for i, r in enumerate(records)
          if (POSES / f"{r['name']}_pose.pdbqt").exists()]
    hyd = {}
    for i in ok:
        coords, elements = parse_pose_pdbqt(
            (POSES / f"{records[i]['name']}_pose.pdbqt").read_text())
        coords = np.asarray(coords, dtype=float)
        elements = [e.capitalize() for e in elements]
        if len(sites) == 0:
            hyd[i] = (0, 0); continue
        d = np.linalg.norm(coords[None, :, :] - sites[:, None, :], axis=2)
        dmin = d.min(1)
        occ = dmin <= OCC_R
        polar = np.array([e in ("N", "O") for e in elements])
        dp = d[:, polar].min(1) if polar.any() else np.full(len(sites), 1e9)
        br = (~occ) & (dp > BR_LO) & (dp <= BR_HI)
        hyd[i] = (int(occ.sum()), int(br.sum()))
    D7 = np.array([rdkit7(r["smiles"]) for r in records], dtype=np.float32)
    H = np.array([hyd.get(i, (np.nan, np.nan)) for i in range(len(records))],
                 dtype=np.float32)
    D9 = np.hstack([D7, H])
    splits = []
    seed0 = {}
    for seed in range(5):
        tr, te = scaffold_split(scaf, seed)
        trp = [i for i in tr if i in hyd]
        tep = [i for i in te if i in hyd]
        X7 = (D7 - D7[tr].mean(0)) / (D7[tr].std(0) + 1e-9)
        m7 = train_mlp(X7[tr], y[tr], seed)
        with torch.no_grad():
            s7 = torch.sigmoid(m7(torch.from_numpy(X7[tep])).squeeze(-1)).numpy()
        X9 = (D9 - D9[trp].mean(0)) / (D9[trp].std(0) + 1e-9)
        m9 = train_mlp(X9[trp], y[trp], seed)
        with torch.no_grad():
            s9 = torch.sigmoid(m9(torch.from_numpy(X9[tep])).squeeze(-1)).numpy()
        a7 = roc_auc_score(y[tep], s7)
        a9 = roc_auc_score(y[tep], s9)
        splits.append({"seed": seed, "n_test_pose": len(tep),
                       "n_train_pose": len(trp),
                       "auroc_mlp7": float(a7), "auroc_mlp9": float(a9)})
        if seed == 0:
            seed0 = {"y": y[tep].tolist(), "s7": s7.tolist(), "s9": s9.tolist(),
                     "n_pos": int(y[tep].sum()), "n_neg": int((1 - y[tep]).sum())}
        print(f"  split {seed}: mlp7 {a7:.3f} mlp9 {a9:.3f} (n={len(tep)})", flush=True)
    m7m = float(np.mean([s["auroc_mlp7"] for s in splits]))
    m9m = float(np.mean([s["auroc_mlp9"] for s in splits]))
    p = delong_p(np.array(seed0["y"], dtype=bool), seed0["s9"], seed0["s7"])
    gate = bool(m9m > m7m and p < 0.05)
    out = {"n_sites_used": int(len(sites)), "min_conservation": MIN_CONS,
           "occ_radius_A": OCC_R, "bridge_range_A": [BR_LO, BR_HI],
           "splits": splits, "mean_auroc_mlp7": m7m, "mean_auroc_mlp9": m9m,
           "delong_seed0_p_mlp9_vs_mlp7": p, "seed0": seed0,
           "gate_G_hyd": "PASS" if gate else "FAIL",
           "feature_summary": {
               "h_occ_mean": float(np.nanmean(H[:, 0])),
               "h_br_mean": float(np.nanmean(H[:, 1]))}}
    print(f"  mean mlp7 {m7m:.4f} vs mlp9 {m9m:.4f}; DeLong p {p:.4f}; "
          f"G-hyd {out['gate_G_hyd']}", flush=True)
    return out


def main():
    sites = part_a()
    b = part_b()
    c = part_c(sites)
    out = {"prereg": "docs/PREREG_HYDRATION_20260928.md",
           "part_b_explicit_water_redock": b, "part_c_hydration_arm": c,
           "part_a_summary": {"n_waters_in_box": sites["n_waters_in_box"],
                              "n_clusters": len(sites["clusters"]),
                              "alignment": sites["alignment"]}}
    (RES / "hydration.json").write_text(json.dumps(out, indent=1))
    print("wrote results/hydration.json", flush=True)


if __name__ == "__main__":
    main()
