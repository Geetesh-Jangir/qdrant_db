from news_rag.fund_catalog import amc_headers_for_hint, amc_planner_lines, bare_amc_name
from news_rag.fund_search import get_fund_index


def test_quant_amc_in_catalog() -> None:
    get_fund_index()._ensure_loaded()
    headers = amc_headers_for_hint("quant")
    bare = {bare_amc_name(h) for h in headers}
    assert "Quant" in bare
    assert not any("Quantum" in b for b in bare)
    lines = amc_planner_lines(["quant"])
    assert lines and "Quant" in lines[0]


def test_quantum_amc_separate_from_quant() -> None:
    get_fund_index()._ensure_loaded()
    q_headers = amc_headers_for_hint("quant")
    qm_headers = amc_headers_for_hint("quantum")
    assert q_headers
    assert qm_headers
    assert not set(q_headers) & set(qm_headers)
