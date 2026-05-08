from app.prompting.fim_prompt import build_fim_prompt
from app.services.context_engine import build_context
import asyncio


def test_fim_prompt_format():
    prompt = build_fim_prompt("a=1", "print(a)", {"k": "v"})
    assert "<fim_prefix>" in prompt
    assert "<fim_suffix>" in prompt
    assert "<fim_middle>" in prompt


def test_context_budget_and_truncation():
    prefix = "x" * 2000
    suffix = "y" * 2000
    context = asyncio.run(build_context(prefix, suffix, "python"))
    assert context["budget"] == 3000
    assert len(context["prefix_tail"]) == 1200
    assert len(context["suffix_head"]) == 800
