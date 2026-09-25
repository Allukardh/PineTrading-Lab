#!/usr/bin/env python3
"""Anchor-capability semantics for Suite 0.2 thesis management.

Target and invalidation are independent capabilities. Missing or unusable
geometry is never replaced by a synthetic fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AnchorCapability(str, Enum):
    FULL = "FULL"
    INVALIDATION_ONLY = "INVALIDATION_ONLY"
    TARGET_ONLY = "TARGET_ONLY"
    NONE = "NONE"


@dataclass(frozen=True)
class AnchorResolution:
    capability: AnchorCapability
    target: float | None
    invalidation: float | None
    target_issue: str | None
    invalidation_issue: str | None


def _valid_direction(direction: int) -> bool:
    return direction in (-1, 1)


def target_is_usable(
    direction: int,
    confirm_close: float,
    target: float | None,
) -> bool:
    if target is None or not _valid_direction(direction):
        return False
    return direction * (float(target) - confirm_close) > 0


def invalidation_is_usable(
    direction: int,
    confirm_close: float,
    invalidation: float | None,
) -> bool:
    if invalidation is None or not _valid_direction(direction):
        return False
    return direction * (confirm_close - float(invalidation)) > 0


def resolve_anchors(
    *,
    direction: int,
    confirm_close: float,
    target: float | None,
    invalidation: float | None,
    target_issue_if_missing: str = "TARGET_MISSING",
    invalidation_issue_if_missing: str = "INVALIDATION_MISSING",
) -> AnchorResolution:
    if not _valid_direction(direction):
        raise ValueError("direction must be -1/+1")

    if target is None:
        target_value = None
        target_issue = target_issue_if_missing
    elif target_is_usable(direction, confirm_close, target):
        target_value = float(target)
        target_issue = None
    else:
        target_value = None
        target_issue = "TARGET_INVALID_GEOMETRY"

    if invalidation is None:
        invalidation_value = None
        invalidation_issue = invalidation_issue_if_missing
    elif invalidation_is_usable(direction, confirm_close, invalidation):
        invalidation_value = float(invalidation)
        invalidation_issue = None
    else:
        invalidation_value = None
        invalidation_issue = "INVALIDATION_INVALID_GEOMETRY"

    if target_value is not None and invalidation_value is not None:
        capability = AnchorCapability.FULL
    elif invalidation_value is not None:
        capability = AnchorCapability.INVALIDATION_ONLY
    elif target_value is not None:
        capability = AnchorCapability.TARGET_ONLY
    else:
        capability = AnchorCapability.NONE

    return AnchorResolution(
        capability=capability,
        target=target_value,
        invalidation=invalidation_value,
        target_issue=target_issue,
        invalidation_issue=invalidation_issue,
    )
