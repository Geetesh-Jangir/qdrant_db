from news_rag.insight.greeting import (
    CAPABILITIES_REPLY,
    RUPEESTOP_IDENTITY_REPLY,
    greeting_reply,
    identity_reply,
)
from news_rag.insight.memory.prompt import prompt_view


def test_hello_mirrors_greeting():
    assert greeting_reply("hello") == "Hello!"
    assert greeting_reply("Hello!") == "Hello!"
    assert greeting_reply("  hi there  ") == "Hi!"
    assert greeting_reply("good morning") == "Good morning!"


def test_who_are_you_identity():
    assert RUPEESTOP_IDENTITY_REPLY == "I am an AI bot by SUM."
    assert identity_reply("who are you") == CAPABILITIES_REPLY
    assert identity_reply("Who are you?") == CAPABILITIES_REPLY
    assert identity_reply("introduce yourself") == CAPABILITIES_REPLY
    assert identity_reply("what can you do") == CAPABILITIES_REPLY
    assert "I am an AI bot by SUM." in CAPABILITIES_REPLY


def test_fund_question_is_not_greeting_or_identity():
    assert greeting_reply("hello what is nav of hdfc large cap") is None
    assert greeting_reply("compare two funds") is None
    assert identity_reply("who are you and what is nav") is None


def test_main_memory_in_prompt_view():
    view = prompt_view({})
    assert "I am an AI bot by SUM." in view["assistant_main_memory"]["who_are_you"]
