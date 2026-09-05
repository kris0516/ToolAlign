"""Original v1 examples for independent CPU tokenizer comparisons.

These are synthetic unit fixtures, not ToolACE records, model outputs or BFCL data.
The reference chat view is declared separately from the wire representation.
"""

import copy
import json

from toolalign.contracts import canonical_hash, validate_record

TOOL = {
    "schema_version": "toolalign.tool.v1",
    "name": "read_note",
    "description": 'Read an original note: 中文 & <tags> "quotes" 🌏.',
    "parameters_json_schema": {
        "type": "object",
        "properties": {
            "note_id": {"type": "string", "maxLength": 100},
            "verbose": {"type": "boolean"},
        },
        "required": ["note_id"],
        "additionalProperties": False,
    },
    "tool_version": "fixture-v1",
    "side_effect_class": "sandbox_only",
    "timeout_ms": 1000,
}


def message(role, content, calls=None, call_id=None):
    return {"role": role, "content": content, "tool_calls": calls or [], "tool_call_id": call_id}


def _call(call_id, note_id):
    return {"call_id": call_id, "name": "read_note", "arguments": {"note_id": note_id}}


def cases():
    records = []

    def add(name, messages, *, tools=None, kind="final", content="Original fixture.", calls=None):
        tools = copy.deepcopy(tools or [])
        calls = copy.deepcopy(calls or [])
        example = {
            "schema_version": "toolalign.example.v1",
            "example_id": name,
            "source": "toolalign-original-tokenizer-fixtures",
            "source_revision": "tokenizer-fixtures-v1",
            "license_id": "MIT",
            "source_record_hash": canonical_hash(name),
            "group_id": name,
            "split": "train",
            "messages": messages,
            "tools": tools,
            "expected_action": {"kind": kind, "tool_calls": calls, "content": content},
            "category": "tokenizer_audit",
        }
        validate_record(example)
        # A stable JSON wire round trip models the on-disk examples.jsonl format.
        wire = json.loads(json.dumps(example, ensure_ascii=False, sort_keys=True))
        hf_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters_json_schema"],
                },
            }
            for tool in wire["tools"]
        ]
        hf_messages = []
        for m in wire["messages"]:
            view = {"role": m["role"], "content": m["content"]}
            if m["tool_calls"]:
                view["tool_calls"] = [
                    {
                        "type": "function",
                        "id": c["call_id"],
                        "function": {"name": c["name"], "arguments": c["arguments"]},
                    }
                    for c in m["tool_calls"]
                ]
            if m["tool_call_id"]:
                view["tool_call_id"] = m["tool_call_id"]
            hf_messages.append(view)
        completion = content
        if kind == "tool_calls":
            completion = "\n".join(
                "<tool_call>\n"
                + json.dumps({"name": c["name"], "arguments": c["arguments"]}, ensure_ascii=False)
                + "\n</tool_call>"
                for c in wire["expected_action"]["tool_calls"]
            )
        records.append(
            {
                "id": name,
                "example": example,
                "wire_roundtrip": wire,
                "reference_messages": hf_messages,
                "reference_tools": hf_tools,
                "reference_completion": completion,
            }
        )

    add(
        "single_tool",
        [message("user", "Read note A.")],
        tools=[TOOL],
        kind="tool_calls",
        content="",
        calls=[_call("target-1", "A")],
    )
    add(
        "parallel_tools",
        [message("system", "Use declared fixture tools."), message("user", "Read notes A and B.")],
        tools=[TOOL],
        kind="tool_calls",
        content="",
        calls=[_call("target-1", "A"), _call("target-2", "B")],
    )
    add(
        "observation",
        [
            message("user", "Read note A."),
            message("assistant", "", [_call("history-1", "A")]),
            message("tool", '{"note":"ready"}', call_id="history-1"),
        ],
        tools=[TOOL],
        content="The original note is ready.",
    )
    add(
        "parallel_observations",
        [
            message("user", "Read notes A and B."),
            message("assistant", "", [_call("history-1", "A"), _call("history-2", "B")]),
            message("tool", "A: 中文 é", call_id="history-1"),
            message("tool", 'B: <>& "quote"', call_id="history-2"),
        ],
        tools=[TOOL],
        content="Both notes read.",
    )
    add(
        "conversation_after_final",
        [
            message("user", "Say ready."),
            message("assistant", "Ready."),
            message("user", "Now read note C."),
        ],
        tools=[TOOL],
        kind="tool_calls",
        content="",
        calls=[_call("target-1", "C")],
    )
    add("no_tools", [message("user", "Reply exactly: ready.")], content="ready.")
    add(
        "clarification",
        [message("user", "Read a note without an identifier.")],
        tools=[TOOL],
        kind="clarify",
        content="Which note identifier should I read?",
    )
    add(
        "refusal",
        [message("user", "Use an unavailable production write tool.")],
        kind="refuse",
        content="The requested tool is unavailable.",
    )
    add(
        "chinese_specials",
        [
            message("system", "原始测试：\u2028👩🏽‍💻 & < >"),
            message("user", "读取“组合 é / 中文 / \\n”笔记。"),
        ],
        tools=[TOOL],
        kind="tool_calls",
        content="",
        calls=[_call("target-1", '中文 é 🌏 <>& "q" \\n')],
    )
    add(
        "empty_system_and_user", [message("system", ""), message("user", "")], content="empty input"
    )
    add(
        "leading_tab",
        [message("user", "Reply with a tab then two spaces then a checkmark.")],
        content="\t  ✓",
    )
    add(
        "leading_newline",
        [message("user", "Reply with a newline followed by ready.")],
        content="\nready.",
    )
    add(
        "leading_two_newlines",
        [message("user", "Reply with two newlines followed by ready.")],
        content="\n\nready.",
    )
    add("leading_crlf", [message("user", "Reply with CR LF then ready.\r\n")], content="\r\nready.")
    add(
        "literal_eos",
        [message("user", "Echo the literal control marker as the original fixture.")],
        content="<|im_end|>",
    )
    add(
        "history_reasoning_tag",
        [
            message("user", "Original first turn."),
            message("assistant", "<think>synthetic history</think>\nprior"),
            message("user", "Reply exactly: next."),
        ],
        content="next.",
    )
    return records
