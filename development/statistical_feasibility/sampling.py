"""Predictable sampling policies that have no access to hidden outcomes."""

from __future__ import annotations

import hashlib
import math
import random
from typing import Dict, Mapping, Optional, Sequence, Tuple


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
    if not probabilities:
        raise ValueError("cannot draw from an empty distribution")
    threshold = rng.random()
    cumulative = 0.0
    last_item = ""
    for item_id, probability in probabilities.items():
        last_item = item_id
        cumulative += probability
        if threshold < cumulative:
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
