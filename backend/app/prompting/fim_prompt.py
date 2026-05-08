def build_fim_prompt(prefix: str, suffix: str, context: dict) -> str:
    return (
        "<fim_prefix>\n"
        f"{prefix}\n"
        "\n# Context\n"
        f"{context}\n"
        "<fim_suffix>\n"
        f"{suffix}\n"
        "<fim_middle>"
    )
