"""Linear daily graph. Each node is one stage. The graph does not choose its own path."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from news_pipeline.graph.nodes.dedupe_and_alias import dedupe_and_alias
from news_pipeline.graph.nodes.drop_old_points import drop_old_points
from news_pipeline.graph.nodes.embed_upsert import embed_and_upsert
from news_pipeline.graph.nodes.fetch_google_news import fetch_google_news
from news_pipeline.graph.nodes.jev_articles import jev_article_scores
from news_pipeline.graph.nodes.jev_titles import jev_title_screen
from news_pipeline.graph.nodes.load_universe import load_universe
from news_pipeline.graph.nodes.scrape_bodies import scrape_bodies
from news_pipeline.graph.nodes.skip_known_urls import skip_known_urls
from news_pipeline.graph.state import PipelineState
from news_pipeline.graph.timing import timed_node


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("load_universe", timed_node("load_universe", load_universe))
    graph.add_node("fetch_google_news", timed_node("fetch_google_news", fetch_google_news))
    graph.add_node("skip_known_urls", timed_node("skip_known_urls", skip_known_urls))
    graph.add_node("dedupe_and_alias", timed_node("dedupe_and_alias", dedupe_and_alias))
    graph.add_node("jev_title_screen", timed_node("jev_title_screen", jev_title_screen))
    graph.add_node("scrape_bodies", timed_node("scrape_bodies", scrape_bodies))
    graph.add_node("jev_article_scores", timed_node("jev_article_scores", jev_article_scores))
    graph.add_node("embed_and_upsert", timed_node("embed_and_upsert", embed_and_upsert))
    graph.add_node("drop_old_points", timed_node("drop_old_points", drop_old_points))

    graph.set_entry_point("load_universe")
    graph.add_edge("load_universe", "fetch_google_news")
    graph.add_edge("fetch_google_news", "skip_known_urls")
    graph.add_edge("skip_known_urls", "dedupe_and_alias")
    graph.add_edge("dedupe_and_alias", "jev_title_screen")
    graph.add_edge("jev_title_screen", "scrape_bodies")
    graph.add_edge("scrape_bodies", "jev_article_scores")
    graph.add_edge("jev_article_scores", "embed_and_upsert")
    graph.add_edge("embed_and_upsert", "drop_old_points")
    graph.add_edge("drop_old_points", END)
    return graph.compile()
