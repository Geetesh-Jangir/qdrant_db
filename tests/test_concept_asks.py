from news_rag.insight.concept_asks import (
    apply_concept_example_to_plan,
    asks_concept_with_catalog_example,
    build_concept_example_plan,
)
from news_rag.insight.contracts import ExecutionPlan, ToolCall, Wave2Policy
from news_rag.insight.slot_router import slot_route


def test_fof_name_one_detected():
    q = "what is fof fund and you name any one of them"
    assert asks_concept_with_catalog_example(q)


def test_concept_example_plan_screen_fof():
    q = "what is fof fund and you name any one of them"
    plan = build_concept_example_plan(q)
    assert plan is not None
    assert plan.concept_brief
    assert "Fund of Funds" in plan.concept_brief
    assert plan.requires_compose
    assert plan.tool_names == ["screen_funds_by_exposure"]
    assert plan.tool_calls[0].arguments.get("top_n") == 1


def test_slot_router_fof_concept_path():
    q = "what is fof fund and you name any one of them"
    plan = slot_route(q, confidence_threshold=0.97)
    assert plan is not None
    assert plan.concept_brief
    assert plan.requires_compose
    assert "screen_funds_by_exposure" in plan.tool_names


def test_planner_fixup_adds_concept_and_screen():
    q = "what is fof fund and you name any one of them"
    plan = ExecutionPlan(
        routed_by="planner",
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"direction": "any", "top_n": 5},
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
    )
    out = apply_concept_example_to_plan(q, plan)
    assert out.concept_brief
    assert out.requires_compose
    assert out.tool_calls[0].arguments["top_n"] == 1
