import asyncio

from app.inference.vllm_client import GenerationConfig, VLLMClient


def test_vllm_streaming_with_stop_and_speculative():
    client = VLLMClient()
    cfg = GenerationConfig(max_tokens=32, use_speculative=True)

    async def run():
        out = []
        async for tok in client.stream_generate("prompt", cfg):
            out.append(tok)
        return "".join(out)

    text = asyncio.run(run())
    assert "generated" in text
    assert len(text) > 0
