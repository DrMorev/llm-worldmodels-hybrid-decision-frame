"""Deterministic synthetic development fixtures; not models of verifier behavior."""

from __future__ import annotations

import random
from typing import Tuple

from .core import FinitePopulation, PopulationItem, stable_seed


ORDINARY_FIXTURES: Tuple[str, ...] = (
    "constant_score",
    "independent_score",
    "informative_score",
    "anti_informative_score",
    "tied_score",
)
DETERMINISTIC_FIXTURES: Tuple[str, ...] = ("all_correct", "all_error")
ALL_FIXTURES = ORDINARY_FIXTURES + DETERMINISTIC_FIXTURES


def _bernoulli(rng: random.Random, probability: float) -> int:
    return int(rng.random() < probability)


def generate_fixture(name: str, population_size: int, seed: int) -> FinitePopulation:
    if name not in ALL_FIXTURES:
        raise ValueError(f"unknown fixture: {name}")
    if population_size <= 0:
        raise ValueError("population_size must be positive")
    score_rng = random.Random(stable_seed(seed, name, "scores"))
    outcome_rng = random.Random(stable_seed(seed, name, "outcomes"))
    items = []
    for index in range(population_size):
        if name == "constant_score":
            score = 0.5
            probability = 0.10
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "independent_score":
            score = score_rng.random()
            probability = 0.10
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "informative_score":
            score = score_rng.random()
            probability = 0.02 + 0.46 * score
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "anti_informative_score":
            score = score_rng.random()
            probability = 0.02 + 0.46 * (1.0 - score)
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "tied_score":
            score = (0.0, 0.25, 0.5, 0.75, 1.0)[score_rng.randrange(5)]
            probability = 0.10
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "all_correct":
            score = score_rng.random()
            outcome = 0
        else:
            score = score_rng.random()
            outcome = 1
        items.append(
            PopulationItem(
                item_id=f"item-{index:04d}",
                score=score,
                outcome=outcome,
                scenario_label=f"development-only:{name}",
            )
        )
    return FinitePopulation(name, tuple(items))
