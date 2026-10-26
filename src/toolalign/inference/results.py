"""One pure raw-output gate shared by evaluation and the restricted service."""

from toolalign.contracts import ContractError, canonical_hash
from toolalign.tools._json import clone, parse_action


def gate_output(output, identity):
    result = {"output": output, "raw_text": output["raw_text"],
              "finish_reason": output["finish_reason"], "raw_action": None,
              "raw_action_valid": False, "raw_parse_failure": "invalid_raw_action",
              "token_accounting_complete": False, "status": "infrastructure_error", "reason": None}
    try:
        result.update(raw_action=clone(parse_action(output["raw_text"])),
                      raw_action_valid=True, raw_parse_failure=None)
    except ContractError:
        pass
    counts_valid = all(type(output[k]) is int and output[k] >= 0
                       for k in ("input_tokens", "output_tokens"))
    result["token_accounting_complete"] = counts_valid
    if canonical_hash(output["model_identity"]) != canonical_hash(identity):
        result["reason"] = "model_identity_mismatch"
    elif not counts_valid:
        result["reason"] = "invalid_token_accounting"
    elif output["finish_reason"] in ("timed_out", "cancelled"):
        result.update(status=output["finish_reason"], reason=output["finish_reason"])
    elif output["output_tokens"] > 256 or output["finish_reason"] == "length":
        result.update(status="budget_exhausted", reason="response_token_limit")
    elif output["finish_reason"] != "stop":
        result["reason"] = output.get("parse_failure") or "backend_error"
    elif not result["raw_action_valid"]:
        result.update(status="parse_failure", reason="invalid_raw_action")
    else:
        result.update(status="completed", reason="completed")
    return result
