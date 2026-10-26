"""Task-specific observation dependencies layered on the unchanged semantic v1."""

from __future__ import annotations

from dataclasses import replace

from toolalign.contracts import ContractError
from toolalign.contracts.interfaces import TaskScore
from toolalign.tools._json import clone

from .semantic import ORACLE_VERSION, SemanticOracle

OBSERVATION_ORACLE_VERSION = "toolalign.semantic-observation.v1"


def _semantic_task(task, payload, strategies=None):
    return replace(task, oracle_payload={
        "version": ORACLE_VERSION,
        "answers": payload["answers"],
        "strategies": payload["strategies"] if strategies is None else strategies,
    })


def validate_observation_task(task):
    """Return copied valid truth, or raise ValueError; no execution is performed.

    `strategies` retains the v1 step lists; `after_observation` has one edge list
    per strategy. Edge [i, j] requires call j to come from a new model decision
    after the observation for call i; indices refer to steps, not decisions.
    Empty edges permit independent calls in the same model decision.
    """
    try:
        payload = clone(task.oracle_payload)
        if (type(payload) is not dict or set(payload) != {"version", "answers", "strategies", "after_observation"}
                or payload["version"] != OBSERVATION_ORACLE_VERSION
                or type(payload["strategies"]) is not list or not payload["strategies"]
                or type(payload["after_observation"]) is not list
                or len(payload["after_observation"]) != len(payload["strategies"])):
            raise ValueError("Unsupported or missing observation oracle truth")
        for strategy, dependencies in zip(payload["strategies"], payload["after_observation"]):
            if type(strategy) is not list or type(dependencies) is not list:
                raise ValueError("Unsupported observation strategy truth")
            for edge in dependencies:
                if (type(edge) is not list or len(edge) != 2
                        or any(type(index) is not int for index in edge)
                        or not 0 <= edge[0] < edge[1] < len(strategy)):
                    raise ValueError("Invalid observation dependency indices")
        # v1 owns answer/step truth validation. An empty execution may fail its
        # task, but only unknown denotes malformed truth for this validation call.
        validation = SemanticOracle().score(_semantic_task(task, payload), [], None)
        if validation.outcome == "unknown":
            raise ValueError(validation.reason)
        return payload
    except (ContractError, KeyError, TypeError) as error:
        raise ValueError("Invalid observation oracle truth") from error


def _after_observation(events, executions, observations, before, after):
    source, observed, successor = executions[before], observations[before], executions[after]
    source_budget = source["budget_consumed"]
    observed_budget = observed["budget_consumed"]
    successor_budget = successor["budget_consumed"]
    if any(source_budget[key] != observed_budget[key] for key in ("model_decisions", "tool_rounds")):
        return False
    # generating is emitted before incrementing model_decisions; parsing is
    # emitted after the model returns, before incrementing the next tool round.
    between = events[observed["event_index"] + 1:successor["event_index"]]
    decisions = [event for event in between if event["event"] in ("generating", "parsing")]
    if len(decisions) < 2 or [event["event"] for event in decisions[-2:]] != ["generating", "parsing"]:
        return False
    generating, parsing = (event["budget_consumed"] for event in decisions[-2:])
    return (
        1 <= observed_budget["model_decisions"] < successor_budget["model_decisions"]
        and 1 <= observed_budget["tool_rounds"] < successor_budget["tool_rounds"]
        and generating["model_decisions"] + 1 == parsing["model_decisions"]
        == successor_budget["model_decisions"]
        and generating["tool_rounds"] == parsing["tool_rounds"]
        == successor_budget["tool_rounds"] - 1
    )


class ObservationOracle:
    version = OBSERVATION_ORACLE_VERSION

    def score(self, task, trace, final_result):
        try:
            payload = validate_observation_task(task)
            events = list(trace)
            semantic = SemanticOracle()
            base = semantic.score(_semantic_task(task, payload), events, final_result)
            if base.outcome != "success":
                return replace(base, oracle_version=self.version)
            # v1 has validated every event, trace identity, pending execution /
            # observation binding, and the full truth before any alternative wins.
            executions = [event for event in events if event["event"] == "tool_execution"]
            observations = [event for event in events if event["event"] == "observing"]
            for strategy, dependencies in zip(payload["strategies"], payload["after_observation"]):
                matched = semantic.score(_semantic_task(task, payload, [strategy]),
                                         events, final_result)
                if matched.outcome == "success" and all(
                    _after_observation(events, executions, observations, before, after)
                    for before, after in dependencies
                ):
                    return TaskScore("success", "Semantic answer, strategy and observation dependencies agree",
                                     self.version)
            return TaskScore("failure", "Required observation did not precede the successor model decision",
                             self.version)
        except (ContractError, KeyError, TypeError, ValueError):
            return TaskScore("unknown", "Invalid observation oracle or trace data", self.version)


class _UnsupportedOracle:
    version = "toolalign.unsupported-oracle.v1"

    def score(self, task, trace, final_result):
        return TaskScore("unknown", "Unsupported or missing oracle version", self.version)


def select_oracle(task):
    """Select only named versions; unknown versions never fall back to v1."""
    payload = task.oracle_payload
    version = payload.get("version") if type(payload) is dict else None
    if version == ORACLE_VERSION:
        return SemanticOracle()
    if version == OBSERVATION_ORACLE_VERSION:
        return ObservationOracle()
    return _UnsupportedOracle()
