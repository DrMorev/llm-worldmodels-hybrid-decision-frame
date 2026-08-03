"""Predictable control variates and fixed-lambda wealth inversion."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Sequence, Tuple


class ControlledNumericalFailure(RuntimeError):
    """A numerical condition that invalidates one development run."""


class MonotonicityFailure(ControlledNumericalFailure):
    """Monotonicity was evaluated and failed."""


class EmptyConfidenceSet(ControlledNumericalFailure):
    """The inverted confidence set is empty; this is a coverage event, not a bound."""


class SupportAdmissibilityFailure(ControlledNumericalFailure):
    """A possible next observation has a negative wealth factor."""

    def __init__(
        self,
        step_number: int,
        item_id: str,
        outcome: int,
        candidate_g: float,
        multiplier: float,
    ) -> None:
        self.step_number = step_number
        self.item_id = item_id
        self.outcome = outcome
        self.candidate_g = candidate_g
        self.multiplier = multiplier
        super().__init__(
            "support-wide admissibility failure "
            f"step={step_number} item_id={item_id} outcome={outcome} "
            f"candidate_g={candidate_g:.17g} multiplier={multiplier:.17g}"
        )


@dataclass(frozen=True)
class BetaEstimate:
    value: float
    covariance: Optional[float]
    variance: Optional[float]
    warning: Optional[str]


@dataclass(frozen=True)
class SupportTerm:
    """One possible pre-reveal payoff state for a sampled item/outcome pair."""

    item_id: str
    outcome: int
    score: float
    probability: float
    control_value: float
    beta: float
    constant_term: float


@dataclass(frozen=True)
class WealthStep:
    constant_term: float
    logical_complement_lower: float
    support_terms: Tuple[SupportTerm, ...] = ()
    support_minimum: Optional[SupportTerm] = None
    support_term_count: int = 0


@dataclass(frozen=True)
class BoundEvaluation:
    lower_complement_bound: Optional[float]
    upper_error_bound: Optional[float]
    min_multiplier: float
    monotonicity_status: str
    final_log_wealth_g0: object
    final_log_wealth_g1: object
    final_log_wealth_at_bound: object


def estimate_beta(
    prior_observations: Sequence[Tuple[float, float]], ridge: float
) -> BetaEstimate:
    if ridge <= 0.0 or not math.isfinite(ridge):
        raise ValueError("ridge must be finite and positive")
    if len(prior_observations) < 3:
        return BetaEstimate(0.0, None, None, None)
    z_mean = math.fsum(pair[0] for pair in prior_observations) / len(prior_observations)
    u_mean = math.fsum(pair[1] for pair in prior_observations) / len(prior_observations)
    covariance = math.fsum(
        (z_value - z_mean) * (u_value - u_mean)
        for z_value, u_value in prior_observations
    ) / len(prior_observations)
    variance = math.fsum(
        (u_value - u_mean) ** 2 for _, u_value in prior_observations
    ) / len(prior_observations)
    raw_value = -covariance / (variance + ridge)
    if not all(math.isfinite(value) for value in (covariance, variance, raw_value)):
        return BetaEstimate(0.0, covariance, variance, "non-finite beta calculation; used zero")
    return BetaEstimate(max(-1.0, min(1.0, raw_value)), covariance, variance, None)


def wealth_multiplier(
    fixed_lambda: float,
    constant_term: float,
    candidate_g: float,
    tolerance: float = 0.0,
) -> float:
    if tolerance < 0.0 or not math.isfinite(tolerance):
        raise ValueError("admissibility tolerance must be finite and nonnegative")
    multiplier = 1.0 + fixed_lambda * (constant_term - candidate_g)
    if not math.isfinite(multiplier):
        raise ControlledNumericalFailure("non-finite wealth multiplier")
    if multiplier < -tolerance:
        raise ControlledNumericalFailure("negative wealth multiplier")
    # A negative value within the declared numerical tolerance is treated as
    # exact zero before taking a logarithm; values below that are failures.
    return max(0.0, multiplier)


def validate_support_admissibility(
    step_number: int,
    support_terms: Sequence[SupportTerm],
    fixed_lambda: float,
    candidate_g: float,
    tolerance: float,
    precomputed_minimum: Optional[SupportTerm] = None,
) -> float:
    """Check every remaining-item and binary-outcome payoff before inversion."""
    # All support multipliers share the positive fixed lambda and candidate g,
    # so after explicitly enumerating the support, its smallest constant term
    # is the global minimum multiplier for every candidate used by inversion.
    term = precomputed_minimum
    if term is None:
        if not support_terms:
            return math.inf
        term = min(support_terms, key=lambda item: item.constant_term)
    raw_multiplier = 1.0 + fixed_lambda * (term.constant_term - candidate_g)
    if not math.isfinite(raw_multiplier) or raw_multiplier < -tolerance:
        raise SupportAdmissibilityFailure(
            step_number,
            term.item_id,
            term.outcome,
            candidate_g,
            raw_multiplier,
        )
    return max(0.0, raw_multiplier)


def log_wealth(
    steps: Sequence[WealthStep],
    fixed_lambda: float,
    candidate_g: float,
    admissibility_tolerance: float = 0.0,
) -> float:
    if not 0.0 <= candidate_g <= 1.0:
        raise ValueError("candidate complement mean must lie in [0, 1]")
    terms = []
    for step_number, step in enumerate(steps, start=1):
        if step.support_terms or step.support_minimum is not None:
            validate_support_admissibility(
                step_number,
                step.support_terms,
                fixed_lambda,
                candidate_g,
                admissibility_tolerance,
                step.support_minimum,
            )
        multiplier = wealth_multiplier(
            fixed_lambda, step.constant_term, candidate_g, admissibility_tolerance
        )
        if multiplier == 0.0:
            return -math.inf
        terms.append(math.log(multiplier))
    result = math.fsum(terms)
    if math.isnan(result) or result == math.inf:
        raise ControlledNumericalFailure("invalid log wealth")
    return result


def verify_monotonicity(
    steps: Sequence[WealthStep],
    fixed_lambda: float,
    tolerance: float,
    admissibility_tolerance: float = 0.0,
) -> bool:
    previous = log_wealth(steps, fixed_lambda, 0.0, admissibility_tolerance)
    for index in range(1, 65):
        current = log_wealth(
            steps, fixed_lambda, index / 64.0, admissibility_tolerance
        )
        if current > previous + tolerance:
            return False
        previous = current
    return True


def bisect_lower_bound(
    steps: Sequence[WealthStep],
    fixed_lambda: float,
    audit_risk: float,
    tolerance: float,
    admissibility_tolerance: float = 0.0,
) -> float:
    threshold = math.log(1.0 / audit_risk)
    at_zero = log_wealth(steps, fixed_lambda, 0.0, admissibility_tolerance)
    if at_zero < threshold:
        return 0.0
    at_one = log_wealth(steps, fixed_lambda, 1.0, admissibility_tolerance)
    if at_one >= threshold:
        raise EmptyConfidenceSet("confidence set is empty on [0, 1]")
    low = 0.0
    high = 1.0
    while high - low > tolerance:
        midpoint = (low + high) / 2.0
        if log_wealth(
            steps, fixed_lambda, midpoint, admissibility_tolerance
        ) >= threshold:
            low = midpoint
        else:
            high = midpoint
    return low


def _json_number(value: float) -> object:
    if value == math.inf:
        return "Infinity"
    if value == -math.inf:
        return "-Infinity"
    if not math.isfinite(value):
        return "NaN"
    return value


def evaluate_running_bound(
    steps: Sequence[WealthStep],
    fixed_lambda: float,
    audit_risk: float,
    inversion_tolerance: float,
    monotonicity_tolerance: float,
) -> BoundEvaluation:
    if not steps:
        return BoundEvaluation(0.0, 1.0, 1.0, "passed", 0.0, 0.0, 0.0)
    running_lower = 0.0
    min_multiplier = math.inf
    for end in range(1, len(steps) + 1):
        prefix = steps[:end]
        if not verify_monotonicity(
            prefix,
            fixed_lambda,
            monotonicity_tolerance,
            inversion_tolerance,
        ):
            raise MonotonicityFailure("log wealth is not monotone in candidate g")
        try:
            raw_lower = bisect_lower_bound(
                prefix,
                fixed_lambda,
                audit_risk,
                inversion_tolerance,
                inversion_tolerance,
            )
        except EmptyConfidenceSet as error:
            raise EmptyConfidenceSet(f"{error}; prefix_step={end}") from error
        logical_lower = prefix[-1].logical_complement_lower
        running_lower = max(running_lower, raw_lower, logical_lower)
        candidate_min = wealth_multiplier(
            fixed_lambda, prefix[-1].constant_term, 1.0, inversion_tolerance
        )
        if prefix[-1].support_terms or prefix[-1].support_minimum is not None:
            candidate_min = min(
                candidate_min,
                validate_support_admissibility(
                    end,
                    prefix[-1].support_terms,
                    fixed_lambda,
                    1.0,
                    inversion_tolerance,
                    prefix[-1].support_minimum,
                ),
            )
        min_multiplier = min(min_multiplier, candidate_min)
    final_g0 = log_wealth(steps, fixed_lambda, 0.0, inversion_tolerance)
    final_g1 = log_wealth(steps, fixed_lambda, 1.0, inversion_tolerance)
    final_bound = log_wealth(
        steps, fixed_lambda, running_lower, inversion_tolerance
    )
    return BoundEvaluation(
        lower_complement_bound=running_lower,
        upper_error_bound=1.0 - running_lower,
        min_multiplier=min_multiplier,
        monotonicity_status="passed",
        final_log_wealth_g0=_json_number(final_g0),
        final_log_wealth_g1=_json_number(final_g1),
        final_log_wealth_at_bound=_json_number(final_bound),
    )
