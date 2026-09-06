"""Standard-library analytic reference; no ToolAlign, MLX, NumPy or Torch imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

ATOL = 2e-6
CASES_SHA = "df4b87001074e9fab6c3a330cf516dca17cfab1bb7505d97025ceeb31d3b5b47"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode())


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def original_definition():
    cases = []
    for index in range(13):
        prompt_size, completion_size = 2 + index % 3, 1 + index % 4
        prompt = [1 + (index + position) % 6 for position in range(prompt_size)]
        completion = [1 + (index * 3 + position) % 6 for position in range(completion_size)]
        sequence = prompt + completion + [7]
        length = len(sequence)
        ids = sequence + [0] * (16 - length)
        mask = [0] * prompt_size + [1] * (completion_size + 1) + [0] * (16 - length)
        cases.append([index + 1, {"sequence_ids": ids, "loss_mask": mask,
            "attention_mask": [1] * length + [0] * (16 - length), "bucket": 16,
            "causal_input_ids": ids[:-1], "causal_target_ids": ids[1:],
            "causal_loss_mask": mask[1:], "effective_supervised_targets": completion_size + 1,
            "first_supervised_causal_position": prompt_size - 1,
            "last_supervised_causal_position": length - 2, "pad_token_id": 0, "unpadded_length": length}])
    table = [[f32((row * 8 + column - 31) / 97) for column in range(8)] for row in range(8)]
    return cases, table


def ce_gradient(table, rank, extra_padding=False):
    # Independent from the serialized masks and consumer's Batch boundaries.
    index = rank - 1
    prompt = [1 + (index + j) % 6 for j in range(2 + index % 3)]
    completion = [1 + (index * 3 + j) % 6 for j in range(1 + index % 4)]
    sequence = prompt + completion + [7]
    pairs = list(zip(sequence[len(prompt) - 1:-1], sequence[len(prompt):], strict=True))
    if extra_padding:
        pairs.append((7, 0))
    grad, ce = [[0.0] * 8 for _ in range(8)], 0.0
    for previous, target in pairs:
        logits = table[previous]
        maximum = max(logits)
        exponents = [math.exp(value - maximum) for value in logits]
        denominator = math.fsum(exponents)
        ce += maximum + math.log(denominator) - logits[target]
        for token in range(8):
            grad[previous][token] += (exponents[token] / denominator - int(token == target)) / len(pairs)
    return ce / len(pairs), grad, len(pairs)


def difference(left, right):
    if isinstance(left, list):
        assert isinstance(right, list) and len(left) == len(right)
        return max((difference(a, b) for a, b in zip(left, right, strict=True)), default=0.0)
    assert type(left) in (int, float) and type(right) in (int, float)
    assert math.isfinite(left) and math.isfinite(right)
    return abs(left - right)


def close(left, right):
    error = difference(left, right)
    assert error <= ATOL, error
    return error


def checkpoint(path):
    raw = path.read_bytes()
    size = struct.unpack("<Q", raw[:8])[0]
    header = json.loads(raw[8:8 + size])
    assert set(header) == {"__metadata__", "table"} and header["__metadata__"] is None, header
    assert header["table"] == {"dtype": "F32", "shape": [8, 8], "data_offsets": [0, 256]}
    data = raw[8 + size:]
    assert len(data) == 256
    flat = struct.unpack("<64f", data)
    table = [list(flat[i:i + 8]) for i in range(0, 64, 8)]
    return table, sha(raw), canonical([["table", "mlx.core.float32", [8, 8], sha(data)]])


def audit_run(root, cases, initial, references):
    def read(name):
        return json.loads((root / name).read_text())
    result = read("result.json")
    errors = []
    for rank, batch in cases:
        raw = read(f"case-{rank:02d}-arrays.json")
        assert raw["batch"] == batch and raw["rank"] == rank
        ce, gradient, tokens = ce_gradient(initial, rank)
        assert raw["mlx_denominator"] == raw["torch_denominator"] == raw["unpadded_mlx_denominator"] == tokens
        loss_error = max(close(raw[key], ce) for key in
                         ("mlx_ce", "torch_ce", "unpadded_mlx_ce", "ignored_changed_ce"))
        gradient_error = max(close(raw[key], gradient) for key in
                             ("mlx_gradient", "torch_gradient", "unpadded_mlx_gradient"))
        original_logits = [initial[token] for token in batch["causal_input_ids"]]
        close(raw["ignored_original_logits"], [original_logits])
        changed = [[f32(value + (0 if mask else token * 10)) for token, value in enumerate(row)]
                   for row, mask in zip(original_logits, batch["causal_loss_mask"], strict=True)]
        close(raw["ignored_changed_logits"], [changed])
        errors.append({"rank": rank, "loss_error": loss_error, "full_gradient_error": gradient_error})
    negative = read("default-padding-negative.json")
    assert negative["correct_tokens"] == 2 and negative["default_tokens"] == 3
    close(negative["correct_ce"], ce_gradient(initial, 1)[0])
    close(negative["default_ce"], ce_gradient(initial, 1, extra_padding=True)[0])
    for step, reference in enumerate(references, 1):
        torch = read(f"torch-update-{step}.json")
        close(torch["parameter"], reference["parameter"])
        close(torch["gradient"], reference["gradient"])
        close(torch["objective"], reference["objective"])
        assert torch["divisor"] == reference["divisor"]
        assert torch["optimizer_step"] == step and torch["processed_microsteps"] == (8 if step == 1 else 13)
        assert torch["validation"]["tokens"] == 44
        close(torch["validation"]["validation_ce"], reference["validation_ce"])
    if result["status"] == "EXPECTED_NEGATIVE":
        assert result["actual_optimizer_updates"] == 1 and result["lost_tail_microsteps"] == 5
        table, file_sha, parameter_sha = checkpoint(root / "TOY_NATIVE_GPU-unsegmented.safetensors")
        close(table, references[0]["parameter"])
        assert difference(table, references[1]["parameter"]) > 0.01
        actual = read("unsegmented-actual-arrays.json")
        assert table == actual["parameter"] and actual["optimizer_step"] == 1
        assert actual["visited"] == result["visited"] == list(range(1, 14))
        assert result["checkpoint_file_sha256"] == file_sha and result["parameter_content_sha256"] == parameter_sha
        score_checks = []
    else:
        assert result["status"] == "PASS" and result["actual_optimizer_updates"] == 2
        assert result["visited"] == list(range(1, 14))
        assert result["states"][0]["model_optimizer_rng_object_ids"] == result["states"][1]["model_optimizer_rng_object_ids"]
        score_checks = []
        selection = canonical(cases)
        validation = canonical(list(range(1, 14)))
        for step, (state, score, reference) in enumerate(zip(result["states"], result["scores"], references, strict=True), 1):
            table, file_sha, parameter_sha = checkpoint(root / "segments" / state["checkpoint"])
            parameter_error = close(table, reference["parameter"])
            raw = read(f"native-update-{step}-arrays.json")
            assert raw["parameter"] == table and raw["score"] == score and raw["state"] == state
            assert score["checkpoint_file_sha256"] == file_sha
            assert state["parameter_content_sha256"] == score["parameter_content_sha256"] == parameter_sha
            assert state["optimizer_step"] == score["optimizer_step"] == step
            assert state["start"] == (0 if step == 1 else 8) and state["stop"] == score["processed_microsteps"] == (8 if step == 1 else 13)
            assert state["actual_divisor"] == reference["divisor"]
            assert score["scope"] == score["profile"] == "TOY_NATIVE_GPU"
            assert score["selection_sha256"] == selection and score["validation_identity_sha256"] == validation
            assert score["supervised_tokens"] == 44 and score["validation_ce"] == score["ce_sum"] / 44
            weighted_ce = math.fsum(ce_gradient(table, rank)[0] * ce_gradient(table, rank)[2] for rank, _ in cases) / 44
            ce_error = close(score["validation_ce"], weighted_ce)
            score_checks.append({"step": step, "parameter_error": parameter_error, "weighted_ce_error": ce_error,
                                 "checkpoint_file_sha256": file_sha, "parameter_content_sha256": parameter_sha})
        assert result["scores"][1]["validation_ce"] < result["scores"][0]["validation_ce"]
        assert result["selected"] == result["scores"][1] == read("reload-arrays.json")["score"]
        assert result["parameter_content_sha256"] == result["selected"]["parameter_content_sha256"]
        assert result["save_reload_exact"] is True and result["wrong_checkpoint_rejected"] == "checkpoint_parameter_content_mismatch"
    return {"root": str(root), "status": result["status"], "per_case": errors, "checkpoints": score_checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert sha(args.cases.read_bytes()) == CASES_SHA
    original = json.loads(args.cases.read_text())
    cases, initial = original_definition()
    assert original["train"] == cases and original["initial_table"] == initial
    assert original["parameters"] == 64 and original["vocabulary"] == 8 and original["unique_examples"] == 13
    assert len({canonical(batch) for _, batch in cases}) == 12 and cases[0][1] == cases[12][1]
    assert sum(ce_gradient(initial, rank)[2] for rank, _ in cases) == 44
    finite_difference_error = 0.0
    for rank, _ in cases:
        _, gradient, _ = ce_gradient(initial, rank)
        for row in range(8):
            for column in range(8):
                plus, minus = [v[:] for v in initial], [v[:] for v in initial]
                plus[row][column] += 1e-5
                minus[row][column] -= 1e-5
                numerical = (ce_gradient(plus, rank)[0] - ce_gradient(minus, rank)[0]) / 2e-5
                finite_difference_error = max(finite_difference_error, abs(numerical - gradient[row][column]))
    assert finite_difference_error < 1e-8
    parameter, references = [row[:] for row in initial], []
    for ranks in (range(1, 9), range(9, 14)):
        results = [ce_gradient(parameter, rank) for rank in ranks]
        gradient = [[math.fsum(value[1][row][column] for value in results) / len(results)
                     for column in range(8)] for row in range(8)]
        objective = math.fsum(value[0] for value in results) / len(results)
        parameter = [[f32(parameter[row][column] - 0.07 * gradient[row][column])
                      for column in range(8)] for row in range(8)]
        val = [ce_gradient(parameter, rank) for rank, _ in cases]
        references.append({"divisor": len(results), "gradient": gradient, "objective": objective,
                           "parameter": parameter, "validation_ce": math.fsum(v[0] * v[2] for v in val) / 44})
    results = [audit_run(path.resolve(), cases, initial, references) for path in args.run]
    output = {"status": "PASS", "reference": "stdlib stable log-sum-exp and analytic full 8x8 gradient; float32 update rounding",
              "case_file_sha256": CASES_SHA, "runs": results, "independent_cases": cases, "initial_table": initial,
              "independent_reference_updates": references, "finite_difference_components": 13 * 64,
              "finite_difference_max_error": finite_difference_error, "supervised_tokens": 44,
              "numeric_absolute_tolerance": ATOL, "framework_imports_or_launches": 0,
              "script_sha256": sha(Path(__file__).read_bytes())}
    save(args.output, output)
    print(json.dumps({"status": "PASS", "runs": len(results), "finite_difference_max_error": finite_difference_error}))


if __name__ == "__main__":
    main()
