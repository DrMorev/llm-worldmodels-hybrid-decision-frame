"""Predictable sampling policies that have no access to hidden outcomes."""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


def _require_remaining(remaining_ids: Sequence[str]) -> None:
    if not remaining_ids:
        raise ValueError("remaining population is empty")
    if len(set(remaining_ids)) != len(remaining_ids):
        raise ValueError("remaining item IDs contain duplicates")


def validate_probabilities(
    probabilities: Mapping[str, float],
    remaining_ids: Sequence[str],
    tolerance: float = 1e-12,
) -> None:
    _require_remaining(remaining_ids)
    if tuple(probabilities) != tuple(remaining_ids):
        raise ValueError("probability keys/order do not match remaining IDs")
    values = tuple(probabilities.values())
    if any((not math.isfinite(value) or value <= 0.0) for value in values):
        raise ValueError("all sampling probabilities must be finite and positive")
    total = math.fsum(values)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=tolerance):
        raise ValueError(f"sampling probabilities sum to {total!r}, not one")


def uniform_probabilities(remaining_ids: Sequence[str]) -> Dict[str, float]:
    _require_remaining(remaining_ids)
    probability = 1.0 / len(remaining_ids)
    result = {item_id: probability for item_id in remaining_ids}
    validate_probabilities(result, remaining_ids)
    return result


def score_informed_probabilities(
    remaining_ids: Sequence[str],
    scores: Mapping[str, float],
    gamma: float,
) -> Tuple[Dict[str, float], float]:
    _require_remaining(remaining_ids)
    if not 0.0 < gamma <= 1.0 or not math.isfinite(gamma):
        raise ValueError("gamma must be finite and lie in (0, 1]")
    try:
        weights = tuple(float(scores[item_id]) for item_id in remaining_ids)
    except KeyError as error:
        raise ValueError(f"missing score for {error.args[0]}") from error
    if any((not math.isfinite(weight) or not 0.0 <= weight <= 1.0) for weight in weights):
        raise ValueError("scores must be finite and lie in [0, 1]")
    score_sum = math.fsum(weights)
    if score_sum == 0.0 or all(weight == weights[0] for weight in weights):
        return uniform_probabilities(remaining_ids), score_sum
    uniform_component = gamma / len(remaining_ids)
    result = {
        item_id: uniform_component + (1.0 - gamma) * weight / score_sum
        for item_id, weight in zip(remaining_ids, weights)
    }
    validate_probabilities(result, remaining_ids)
    return result, score_sum


def policy_probabilities(
    policy: str,
    remaining_ids: Sequence[str],
    scores: Mapping[str, float],
    gamma: Optional[float],
) -> Tuple[Dict[str, float], float]:
    if policy == "uniform":
        return uniform_probabilities(remaining_ids), float(len(remaining_ids))
    if policy == "score_informed":
        if gamma is None:
            raise ValueError("score-informed sampling requires gamma")
        return score_informed_probabilities(remaining_ids, scores, gamma)
    raise ValueError(f"unknown sampling policy: {policy}")


def draw_item(probabilities: Mapping[str, float], rng: random.Random) -> str:
    """Draw from one recorded pre-reveal uniform variate."""

    return select_item_from_variate(probabilities, rng.random())


def select_item_from_variate(
    probabilities: Mapping[str, float], uniform_variate: float
) -> str:
    """Select using left-closed/right-open cumulative intervals.

    An internal cumulative-boundary variate selects the following item.
    """

    if not probabilities:
        raise ValueError("cannot draw from an empty distribution")
    if not math.isfinite(uniform_variate) or not 0.0 <= uniform_variate < 1.0:
        raise ValueError("uniform variate must be finite and in [0, 1)")
    cumulative = 0.0
    last_item = ""
    for item_id, probability in probabilities.items():
        last_item = item_id
        cumulative += probability
        if uniform_variate < cumulative:
            return item_id
    if not last_item:
        raise ValueError("distribution had no items")
    return last_item


def vector_digest(probabilities: Mapping[str, float]) -> str:
    digest = hashlib.sha256()
    for item_id, probability in probabilities.items():
        digest.update(item_id.encode("utf-8"))
        digest.update(b"=")
        digest.update(probability.hex().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def score_digest(remaining_ids: Sequence[str], scores: Mapping[str, float]) -> str:
    digest = hashlib.sha256()
    for item_id in remaining_ids:
        digest.update(item_id.encode("utf-8"))
        digest.update(b"=")
        digest.update(float(scores[item_id]).hex().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def remaining_digest(remaining_ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(remaining_ids).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReplayResult:
    """Result of reconstructing one draw from its serialized artifact."""

    passed: bool
    reason: Optional[str] = None
    reconstructed_item_id: Optional[str] = None


def _float_token(value: Optional[float]) -> Optional[str]:
    return None if value is None else float(value).hex()


def serialized_pre_reveal_digest(record: Mapping[str, Any]) -> str:
    """Return the unkeyed integrity digest for one serialized draw record."""
    normalization = record["normalization"]
    payload = repr(
        (
            int(record["step"]),
            tuple(record["remaining_item_ids"]),
            tuple(_float_token(value) for value in record["remaining_scores"]),
            record["sampling_policy"],
            _float_token(record["gamma"]),
            (
                int(normalization["remaining_count"]),
                _float_token(normalization["score_sum"]),
                _float_token(normalization["policy_value"]),
            ),
            tuple(_float_token(value) for value in record["q_vector"]),
            _float_token(record["draw_uniform"]),
            record["selected_item_id"],
            _float_token(record["selected_q"]),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def serialize_pre_reveal_draw(
    *,
    step: int,
    remaining_item_ids: Sequence[str],
    scores: Mapping[str, float],
    sampling_policy: str,
    gamma: Optional[float],
    probabilities: Mapping[str, float],
    normalization: float,
    draw_uniform: float,
    selected_item_id: str,
) -> Dict[str, Any]:
    """Serialize all values needed to replay a draw before outcome reveal."""

    ordered_ids = list(remaining_item_ids)
    ordered_scores = [float(scores[item_id]) for item_id in ordered_ids]
    record: Dict[str, Any] = {
        "step": int(step),
        "remaining_item_ids": ordered_ids,
        "remaining_scores": ordered_scores,
        "sampling_policy": sampling_policy,
        "gamma": gamma,
        "normalization": {
            "remaining_count": len(ordered_ids),
            "score_sum": math.fsum(ordered_scores),
            "policy_value": float(normalization),
        },
        "q_vector": [float(probabilities[item_id]) for item_id in ordered_ids],
        "draw_uniform": float(draw_uniform),
        "selected_item_id": selected_item_id,
        "selected_q": float(probabilities[selected_item_id]),
    }
    record["integrity_digest"] = serialized_pre_reveal_digest(record)
    return record


def _numbers_match(left: float, right: float, tolerance: float) -> bool:
    return math.isfinite(left) and math.isfinite(right) and math.isclose(
        left, right, rel_tol=tolerance, abs_tol=tolerance
    )


def replay_pre_reveal_draw(
    record: Mapping[str, Any], tolerance: float = 1e-12
) -> ReplayResult:
    """Replay only from serialized pre-reveal fields, without hidden outcomes."""

    try:
        required = {
            "step", "remaining_item_ids", "remaining_scores", "sampling_policy",
            "gamma", "normalization", "q_vector", "draw_uniform",
            "selected_item_id", "selected_q", "integrity_digest",
        }
        missing = sorted(required.difference(record))
        if missing:
            return ReplayResult(False, f"missing serialized fields: {', '.join(missing)}")
        if record["integrity_digest"] != serialized_pre_reveal_digest(record):
            return ReplayResult(False, "serialized pre-reveal integrity digest mismatch")
        item_ids = list(record["remaining_item_ids"])
        score_values = list(record["remaining_scores"])
        q_vector = list(record["q_vector"])
        if not item_ids or len(item_ids) != len(score_values) or len(item_ids) != len(q_vector):
            return ReplayResult(False, "serialized vector lengths are inconsistent")
        if len(set(item_ids)) != len(item_ids):
            return ReplayResult(False, "serialized remaining IDs are not unique")
        scores = {item_id: float(score) for item_id, score in zip(item_ids, score_values)}
        probabilities, normalization = policy_probabilities(
            str(record["sampling_policy"]), item_ids, scores, record["gamma"]
        )
        recorded_normalization = record["normalization"]
        if int(recorded_normalization["remaining_count"]) != len(item_ids):
            return ReplayResult(False, "remaining-count normalization mismatch")
        if not _numbers_match(
            float(recorded_normalization["score_sum"]), math.fsum(float(v) for v in score_values), tolerance
        ):
            return ReplayResult(False, "score-sum normalization mismatch")
        if not _numbers_match(
            float(recorded_normalization["policy_value"]), normalization, tolerance
        ):
            return ReplayResult(False, "policy normalization mismatch")
        for item_id, recorded_q in zip(item_ids, q_vector):
            if not _numbers_match(float(recorded_q), probabilities[item_id], tolerance):
                return ReplayResult(False, f"q-vector mismatch for {item_id}")
        selected = select_item_from_variate(probabilities, float(record["draw_uniform"]))
        if selected != record["selected_item_id"]:
            return ReplayResult(False, "selected item mismatch", selected)
        if not _numbers_match(float(record["selected_q"]), probabilities[selected], tolerance):
            return ReplayResult(False, "selected q mismatch", selected)
        return ReplayResult(True, reconstructed_item_id=selected)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return ReplayResult(False, f"invalid serialized pre-reveal record: {exc}")
