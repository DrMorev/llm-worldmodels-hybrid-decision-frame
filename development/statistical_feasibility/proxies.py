"""Observable PPI and confidence-margin plumbing for development Stage 1."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence, Tuple


class InvalidObservableMagnitude(ValueError):
    """An observable confidence magnitude cannot enter the declared score."""


@dataclass(frozen=True)
class StructuralRepresentation:
    """Synthetic representation with an explicit transformable surface field."""

    canonical_state: int
    truth: int
    robust_feature: float
    fragile_surface: Tuple[float, ...]

    def __post_init__(self) -> None:
        if self.canonical_state not in (-1, 1) or self.truth not in (0, 1):
            raise ValueError("canonical state and truth are invalid")
        if not math.isfinite(self.robust_feature):
            raise ValueError("robust feature must be finite")
        if not self.fragile_surface or any(
            not math.isfinite(value) for value in self.fragile_surface
        ):
            raise ValueError("fragile surface must be non-empty and finite")


@dataclass(frozen=True)
class FrozenSurfaceTransformation:
    transformation_id: str
    component_index: int
    magnitude: float

    def apply(self, representation: StructuralRepresentation) -> StructuralRepresentation:
        if not 0 <= self.component_index < len(representation.fragile_surface):
            raise ValueError("transformation component is outside the fragile surface")
        if not math.isfinite(self.magnitude) or self.magnitude <= 0.0:
            raise ValueError("transformation magnitude must be finite and positive")
        values = list(representation.fragile_surface)
        original = values[self.component_index]
        direction = 1.0 if original >= 0.0 else -1.0
        values[self.component_index] = original - direction * self.magnitude
        transformed = StructuralRepresentation(
            canonical_state=representation.canonical_state,
            truth=representation.truth,
            robust_feature=representation.robust_feature,
            fragile_surface=tuple(values),
        )
        if transformed.canonical_state != representation.canonical_state:
            raise AssertionError("transformation changed canonical state")
        if transformed.truth != representation.truth:
            raise AssertionError("transformation changed truth")
        if transformed.robust_feature != representation.robust_feature:
            raise AssertionError("transformation changed robust feature")
        differences = sum(
            left != right
            for left, right in zip(
                representation.fragile_surface, transformed.fragile_surface
            )
        )
        if differences != 1:
            raise AssertionError("transformation must change exactly one surface component")
        if not math.isclose(
            abs(values[self.component_index] - original),
            self.magnitude,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise AssertionError("transformation magnitude changed")
        return transformed


@dataclass(frozen=True)
class FrozenTransformationBank:
    transformations: Tuple[FrozenSurfaceTransformation, ...]
    k4_indices: Tuple[int, ...]
    bank_id: str

    def __post_init__(self) -> None:
        if len(self.transformations) != 8:
            raise ValueError("the Stage 1 bank must contain exactly eight transformations")
        if self.k4_indices != (0, 2, 5, 7):
            raise ValueError("the K=4 sensitivity subset is frozen")
        ids = tuple(item.transformation_id for item in self.transformations)
        components = tuple(item.component_index for item in self.transformations)
        magnitudes = tuple(item.magnitude for item in self.transformations)
        if len(set(ids)) != 8 or len(set(components)) != 8:
            raise ValueError("bank transformations and components must be unique")
        if any(value != magnitudes[0] for value in magnitudes):
            raise ValueError("all transformations must use the same magnitude")

    @property
    def digest(self) -> str:
        payload = {
            "bank_id": self.bank_id,
            "k4_indices": list(self.k4_indices),
            "transformations": [
                {
                    "id": item.transformation_id,
                    "component_index": item.component_index,
                    "magnitude": item.magnitude.hex(),
                }
                for item in self.transformations
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha256(encoded).hexdigest()

    def indices_for_k(self, k: int) -> Tuple[int, ...]:
        if k == 8:
            return tuple(range(8))
        if k == 4:
            return self.k4_indices
        raise ValueError("PPI K must be 8 or 4")

    def identity(self, representation: StructuralRepresentation) -> StructuralRepresentation:
        """Separate identity sentinel; never part of the ordered bank."""

        return representation


def frozen_transformation_bank(magnitude: float = 0.80) -> FrozenTransformationBank:
    transformations = tuple(
        FrozenSurfaceTransformation(f"surface_component_{index}", index, magnitude)
        for index in range(8)
    )
    return FrozenTransformationBank(
        transformations=transformations,
        k4_indices=(0, 2, 5, 7),
        bank_id="ppi-stage1-surface-bank-v1",
    )


@dataclass(frozen=True)
class ObservableCaseOutputs:
    """All and only observable values required to reproduce Stage 1 scores."""

    item_id: str
    original_primary_output: int
    original_verifier_output: int
    original_primary_magnitude: float
    original_verifier_magnitude: float
    transformed_primary_outputs: Tuple[int, ...]
    transformed_verifier_outputs: Tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("observable output item ID must be non-empty")
        outputs = (
            self.original_primary_output,
            self.original_verifier_output,
            *self.transformed_primary_outputs,
            *self.transformed_verifier_outputs,
        )
        if any(value not in (0, 1) for value in outputs):
            raise ValueError("component outputs must be binary")
        if len(self.transformed_primary_outputs) != 8 or len(
            self.transformed_verifier_outputs
        ) != 8:
            raise ValueError("observable outputs must cover the frozen K=8 bank")
        if not all(
            math.isfinite(value)
            for value in (
                self.original_primary_magnitude,
                self.original_verifier_magnitude,
            )
        ):
            raise InvalidObservableMagnitude("original decision magnitudes must be finite")


@dataclass(frozen=True)
class PPIResult:
    score: float
    primary_flip_rate: float
    verifier_flip_rate: float
    perturbed_disagreement_rate: float
    stable_count: int
    k: int


def compute_ppi(
    original_primary_output: int,
    original_verifier_output: int,
    transformed_primary_outputs: Sequence[int],
    transformed_verifier_outputs: Sequence[int],
    selected_indices: Sequence[int],
) -> PPIResult:
    """Compute PPI solely from original/transformed observable outputs."""

    if original_primary_output not in (0, 1) or original_verifier_output not in (0, 1):
        raise ValueError("original outputs must be binary")
    if original_primary_output != original_verifier_output:
        raise ValueError("PPI is defined only inside the original agreement region")
    if len(transformed_primary_outputs) != len(transformed_verifier_outputs):
        raise ValueError("transformed output vectors must have equal length")
    indices = tuple(int(index) for index in selected_indices)
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("PPI indices must be non-empty and unique")
    if any(index < 0 or index >= len(transformed_primary_outputs) for index in indices):
        raise ValueError("PPI index is outside the transformed output bank")
    original = original_primary_output
    stable_count = sum(
        transformed_primary_outputs[index]
        == transformed_verifier_outputs[index]
        == original
        for index in indices
    )
    primary_flips = sum(
        transformed_primary_outputs[index] != original for index in indices
    )
    verifier_flips = sum(
        transformed_verifier_outputs[index] != original for index in indices
    )
    disagreements = sum(
        transformed_primary_outputs[index] != transformed_verifier_outputs[index]
        for index in indices
    )
    k = len(indices)
    score = (k - stable_count) / k
    if not 0.0 <= score <= 1.0 or not math.isclose(
        score * k, round(score * k), rel_tol=0.0, abs_tol=1e-12
    ):
        raise AssertionError("PPI score is outside its exact finite grid")
    return PPIResult(
        score=score,
        primary_flip_rate=primary_flips / k,
        verifier_flip_rate=verifier_flips / k,
        perturbed_disagreement_rate=disagreements / k,
        stable_count=stable_count,
        k=k,
    )


def ppi_from_observable_outputs(
    outputs: ObservableCaseOutputs,
    bank: FrozenTransformationBank,
    k: int,
) -> PPIResult:
    return compute_ppi(
        outputs.original_primary_output,
        outputs.original_verifier_output,
        outputs.transformed_primary_outputs,
        outputs.transformed_verifier_outputs,
        bank.indices_for_k(k),
    )


def compute_confidence_margin(
    primary_magnitude: float,
    verifier_magnitude: float,
    tau_primary: float,
    tau_verifier: float,
    normalization_primary: float,
    normalization_verifier: float,
) -> float:
    values = (
        primary_magnitude,
        verifier_magnitude,
        tau_primary,
        tau_verifier,
        normalization_primary,
        normalization_verifier,
    )
    if any(not math.isfinite(value) for value in values):
        raise InvalidObservableMagnitude("confidence-margin inputs must be finite")
    if normalization_primary <= tau_primary or normalization_verifier <= tau_verifier:
        raise InvalidObservableMagnitude("each normalization must exceed its threshold")

    def normalized(magnitude: float, threshold: float, maximum: float) -> float:
        return max(0.0, min(1.0, (abs(magnitude) - threshold) / (maximum - threshold)))

    primary = normalized(primary_magnitude, tau_primary, normalization_primary)
    verifier = normalized(verifier_magnitude, tau_verifier, normalization_verifier)
    result = 1.0 - min(primary, verifier)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise InvalidObservableMagnitude("confidence-margin score is invalid")
    return result


def observable_outputs_digest(records: Sequence[ObservableCaseOutputs]) -> str:
    payload = [
        {
            "item_id": record.item_id,
            "original_primary_output": record.original_primary_output,
            "original_verifier_output": record.original_verifier_output,
            "original_primary_magnitude": record.original_primary_magnitude.hex(),
            "original_verifier_magnitude": record.original_verifier_magnitude.hex(),
            "transformed_primary_outputs": list(record.transformed_primary_outputs),
            "transformed_verifier_outputs": list(record.transformed_verifier_outputs),
        }
        for record in records
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def score_channel_digest(scores: Mapping[str, float]) -> str:
    encoded = json.dumps(
        [(item_id, float(value).hex()) for item_id, value in scores.items()],
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
