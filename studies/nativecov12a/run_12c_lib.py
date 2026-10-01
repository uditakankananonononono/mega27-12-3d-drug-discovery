import re
def all_models(path, names):
    models, energies, cur, cur_e = [], [], [], None
    for line in open(path):
        if not line.startswith('DOCKED: '): continue
        s = line[8:]
        if s.startswith('MODEL'): cur = []; cur_e = None
        elif 'Estimated Free Energy of Binding' in s:
            cur_e = float(re.search(r'=\s*(-?[0-9.eE+-]+?)\s*kcal/mol', s).group(1))
        elif s.startswith(('ATOM', 'HETATM')):
            cur.append((s[12:16].strip(), (float(s[30:38]), float(s[38:46]), float(s[46:54]))))
        elif s.startswith('ENDMDL'): models.append(cur); energies.append(cur_e)
    out = []
    for m, e in zip(models, energies):
        got, k = [], 0
        for nm, xyz in m:
            if k < len(names) and nm == names[k]: got.append(xyz); k += 1
        assert k == len(names)
        out.append(({i + 1: xyz for i, xyz in enumerate(got)}, e))
    return out

