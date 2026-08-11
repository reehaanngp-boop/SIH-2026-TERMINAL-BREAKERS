"""Detector base classes and shared result shape.

Every detector returns a plain dictionary with a stable shape so the risk
engine can consume output from different implementations interchangeably:

    {
        "name": str,            # detector identifier, e.g. "asr"
        "status": str,          # "available" | "unavailable" | "error"
        "available": bool,
        "score": float | None,  # 0..1 likelihood of the fraud signal (or None)
        "label": str | None,    # short human label, e.g. "Likely AI-generated"
        "detail": str | None,   # longer explanation
        "metrics": dict,        # optional per-feature values for transparency
    }
"""

from __future__ import annotations

from typing import Any


class BaseDetector:
    """Interface all detectors implement."""

    name: str = "base"
    description: str = ""

    def available(self) -> bool:
        """Whether this detector can produce results right now."""
        raise NotImplementedError

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "available": self.available(),
        }

    @classmethod
    def _result(
        cls,
        status: str = "available",
        *,
        score: float | None = None,
        label: str | None = None,
        detail: str | None = None,
        metrics: dict | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "name": cls.name,
            "status": status,
            "available": status == "available",
            "score": score,
            "label": label,
            "detail": detail,
            "metrics": metrics or {},
            **extra,
        }
