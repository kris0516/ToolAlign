"""The same 12 original/public fixtures as the preserved proposal, without engines."""

import copy
import json
from pathlib import Path

SPECIAL_STRINGS = [
    "<|endoftext|>", "<|im_start|>", "<|im_end|>", "<|object_ref_start|>",
    "<|object_ref_end|>", "<|box_start|>", "<|box_end|>", "<|quad_start|>",
    "<|quad_end|>", "<|vision_start|>", "<|vision_end|>", "<|vision_pad|>",
    "<|image_pad|>", "<|video_pad|>",
]

def message(role, content, calls=None, call_id=None):
    return {
        "role": role,
        "content": content,
        "tool_calls": calls or [],
        "tool_call_id": call_id,
    }

def action(kind, content, calls=None):
    return {"kind": kind, "content": content, "tool_calls": calls or []}

def original_cases(public_example, special_strings):
    cases = [("public_contract_tool_call", copy.deepcopy(public_example))]

    def add(name, target, messages=None, tools=None):
        item = copy.deepcopy(public_example)
        item["expected_action"] = target
        if messages is not None:
            item["messages"] = messages
        if tools is not None:
            item["tools"] = tools
        cases.append((name, item))

    same = 'OUTPUT_ONLY_SENTINEL_42: 请提供 "版本"。\n第二行：café 😀'
    for kind in ("final", "clarify", "refuse"):
        add("same_content_" + kind, action(kind, same), tools=[])
    add("leading_newlines", action("final", "\n\n原创回答\n"), tools=[])
    add("whitespace_content", action("clarify", " \t\n"), tools=[])

    string_schema = {"type": "string", "maxLength": 2048}
    parameters = {
        "type": "object",
        "properties": {
            "payload": {
                "type": "object",
                "properties": {
                    "text": string_schema,
                    "count": {"type": "integer"},
                    "ratio": {"type": "number"},
                    "enabled": {"type": "boolean"},
                    "nothing": {"type": "null"},
                    "tags": {"type": "array", "items": string_schema, "maxItems": 4},
                    'key<angle>"': string_schema,
                },
                "required": ["text", "count", "ratio", "enabled", "nothing", "tags"],
                "additionalProperties": False,
            }
        },
        "required": ["payload"],
        "additionalProperties": False,
    }
    tools = []
    for name in ("inspect_alpha", "inspect_beta"):
        tool = copy.deepcopy(public_example["tools"][0])
        tool.update(name=name, description='原创只读工具 "甲"\n保留 <tag>。')
        tool["parameters_json_schema"] = copy.deepcopy(parameters)
        tools.append(tool)
    arguments = {
        "payload": {
            "text": '非ASCII "引号"\n字面 \\u003c 与 < 不是同一字符串',
            "count": 2,
            "ratio": -0.5,
            "enabled": False,
            "nothing": None,
            "tags": ["a", "中文", ""],
            'key<angle>"': "值 >",
        }
    }
    calls = [
        {"call_id": "new-1", "name": tools[0]["name"], "arguments": arguments},
        {"call_id": "new-2", "name": tools[1]["name"], "arguments": arguments},
    ]
    add("nested_two_tools", action("tool_calls", "同时检查两项。\n", calls), tools=tools)
    history_calls = copy.deepcopy(calls)
    history_calls[0]["call_id"] = "history-1"
    history_calls[1]["call_id"] = "history-2"
    history = [
        message("system", "Task constraint: read only. Use tool-call JSON format."),
        message("user", "检查两个原创对象。"),
        message("assistant", "历史说明", history_calls),
        message("tool", '{"second": "先返回"}', call_id="history-2"),
        message("tool", '{"first": "后返回"}', call_id="history-1"),
    ]
    add("history_observations_reversed", action("tool_calls", "再检查", calls), history, tools)
    history_no_kind = [
        message("user", "先前的问题。"),
        message("assistant", "同一历史文本，没有 kind。"),
        message("user", "继续。"),
    ]
    add("history_without_kind", action("final", "现在的回答。"), history_no_kind, [])
    think_history = [
        message("user", "保留字面标记。"),
        message("assistant", "KEEP_PREFIX<think>字面</think>\nKEEP_SUFFIX"),
        message("user", "继续并保留原文。"),
    ]
    add("literal_think_history", action("final", "<think>原文</think>"), think_history, [])
    controls = " | ".join(special_strings) + ' | </think> <tool_call> \\u003c \\n "\n'
    add(
        "literal_control_tokens",
        action("final", controls),
        [message("system", controls), message("user", controls)],
        [],
    )
    add(
        "legitimate_metadata_words",
        action("final", "这些单词保留为用户数据。"),
        [message("user", '解释 JSON 字段名 "expected_action"、"oracle"、"split"。')],
        [],
    )
    return cases

def public_example():
    return json.loads((Path(__file__).resolve().parents[1] / "fixtures/contracts/example.json").read_text())


def cases():
    return original_cases(public_example(), SPECIAL_STRINGS)
