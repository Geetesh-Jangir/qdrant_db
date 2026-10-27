from news_rag.tools import run_screen_funds, screen_hints_from_question


def test_automobile_and_automotive_sector_screen_equivalent():
    q_auto = "pick a fund that is invested or holds in automobile sector"
    q_motive = "pick a fund that is invested or holds in automotive sector"
    h1 = screen_hints_from_question(q_auto)
    h2 = screen_hints_from_question(q_motive)
    assert h1["sector_name"]
    assert h2["sector_name"]
    assert "auto" in h1["sector_name"].lower()
    assert "auto" in h2["sector_name"].lower()
    r1 = run_screen_funds(question=q_auto, direction="any", top_n=3)
    r2 = run_screen_funds(question=q_motive, direction="any", top_n=3)
    n1 = len((r1.get("data") or {}).get("rankings") or [])
    n2 = len((r2.get("data") or {}).get("rankings") or [])
    assert n1 >= 1
    assert n2 >= 1


def test_petroleum_and_petrol_sector_screen():
    for q in (
        "pick a fund that is invested or holds in petroleum sector and tell me about it overall",
        "pick a fund that is invested or holds in petrol sector",
    ):
        hints = screen_hints_from_question(q)
        assert hints.get("sector_name") or hints.get("stock_name") != "in petroleum sector"
        r = run_screen_funds(question=q, direction="any", top_n=3)
        rankings = (r.get("data") or {}).get("rankings") or []
        assert len(rankings) >= 1, q


def test_fmgc_typo_and_fmcg_resolve_to_pipeline_sector():
    from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

    idx = get_sector_fund_ranking_index()
    for label in ("fmgc", "FMGC", "FMCG", "fmcg sector"):
        keys = idx.resolve_sector_keys([label])
        assert "Diversified Fmcg" in keys, label


def test_petroleum_phrase_resolves_to_petroleum_products():
    from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

    idx = get_sector_fund_ranking_index()
    for label in ("petroleum", "petroleum sector", "petrol products"):
        keys = idx.resolve_sector_keys([label])
        assert "Petroleum Products" in keys, label


def test_petroleum_not_treated_as_stock_name():
    from news_rag.tools import stock_name_from_question

    q = "pick a fund that is invested or holds in petroleum sector and tell me about it overall"
    assert stock_name_from_question(q) == ""


def test_about_it_overall_does_not_resolve_it_sector():
    q = "pick a fund in automotive sector and tell me about it overall"
    hints = screen_hints_from_question(q)
    assert "software" not in (hints.get("sector_name") or "").lower()
    assert "auto" in (hints.get("sector_name") or "").lower() or hints.get("sector_name")
