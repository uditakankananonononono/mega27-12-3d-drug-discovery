from drugdisc.denovo import enumerate_candidates, complexity_score, tanimoto_to_set


def test_enumeration_passes_filters():
    cands = enumerate_candidates()
    assert len(cands) >= 20
    assert all(c["mw"] <= 550.0 and c["rotatable"] <= 12 for c in cands)
    smiles = [c["smiles"] for c in cands]
    assert len(set(smiles)) == len(smiles)  # deduplicated


def test_complexity_orders_simple_below_complex():
    assert complexity_score("CCO") < complexity_score("O=C(NC(c1ccc2ccccc2c1)c1ccncc1)c1ccco1")


def test_tanimoto_self_vs_distinct():
    assert tanimoto_to_set("CCO", ["CCO"]) == 1.0
    assert tanimoto_to_set("c1ccccc1", ["CCO"]) < 0.3
