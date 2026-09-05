"""32 original synthetic training-only smoke cases, unrelated to P02/test/BFCL."""

from __future__ import annotations

from .core import EncodedExample


def smoke_samples() -> list[dict]:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "add",
                "description": "Add two small integers without side effects.",
                "parameters": {
                    "type": "object",
                    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                    "required": ["a", "b"],
                    "additionalProperties": False,
                },
            },
        }
    ]
    result = []
    for i in range(32):
        kind = ("call", "observation", "no_tool", "clarify")[i % 4]
        prefix = [
            {"role": "system", "content": "Use only the declared tool when needed. Be concise."}
        ]
        if kind == "call":
            prefix += [{"role": "user", "content": f"Use add to calculate {i} plus 2."}]
            answer = f'<tool_call>\n{{"name":"add","arguments":{{"a":{i},"b":2}}}}\n</tool_call>'
        elif kind == "observation":
            prefix += [
                {"role": "user", "content": f"Use add to calculate {i} plus 2."},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {"name": "add", "arguments": {"a": i, "b": 2}},
                        }
                    ],
                },
                {"role": "tool", "content": str(i + 2)},
            ]
            answer = str(i + 2)
        elif kind == "no_tool":
            prefix += [{"role": "user", "content": f"Reply exactly: smoke-{i}"}]
            answer = f"smoke-{i}"
        else:
            prefix += [{"role": "user", "content": f"Add an unspecified number to {i}."}]
            answer = "Which number should I add?"
        result.append(
            {
                "id": f"p01-smoke-{i:02d}",
                "split": "train",
                "kind": kind,
                "messages": prefix,
                "tools": tools,
                "completion": answer,
            }
        )
    return result


def encode_sample(tokenizer, sample: dict, limit: int) -> EncodedExample:
    """Render the input prefix with the actual non-thinking template.

    One supervised assistant decision per prefix, including after tool observations.
    The template-inserted empty thinking block belongs to the prompt. Completion
    begins immediately afterwards. Assert the token prefix survives concatenation.
    """
    prefix = tokenizer.apply_chat_template(
        sample["messages"],
        tools=sample["tools"],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    p = tokenizer.encode(prefix, add_special_tokens=False)
    full = tokenizer.encode(prefix + sample["completion"], add_special_tokens=False)
    if full[: len(p)] != p:
        raise ValueError("Tokenizer merged across prompt/completion boundary")
    full.append(tokenizer.eos_token_id)
    row = EncodedExample(
        tuple(full), (0,) * len(p) + (1,) * (len(full) - len(p)), len(p), tokenizer.eos_token_id
    )
    row.validate(limit)
    return row
