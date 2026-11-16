"""Entity-scoped retrieval helpers."""

from ai_insight.common.clustering import Cluster
from ai_insight.common.entity_retrieval import merge_evidence, slug
from ai_insight.common.evidence import EvidenceArticle


def test_slug_macro_name() -> None:
    assert slug("Macro - Nifty 50") == "macro_nifty_50"


def test_merge_evidence_dedupes_url() -> None:
    one = EvidenceArticle("c0", "A", "s", "t", "http://x", "text", 1.0, "Macro", "up", 2)
    two = EvidenceArticle("c1", "B", "s", "t2", "http://x", "text2", 1.0, "Macro", "up", 2)
    three = EvidenceArticle("c2", "C", "s", "t3", "http://y", "text3", 1.0, "Macro", "up", 2)
    merged = merge_evidence([one], [two, three])
    assert len(merged) == 2
    assert merged[0].url == "http://x"
    assert merged[1].url == "http://y"