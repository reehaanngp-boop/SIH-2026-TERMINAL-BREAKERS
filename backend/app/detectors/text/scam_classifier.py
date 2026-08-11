"""Scam-script text classifier.

Wraps the scikit-learn model produced by ``backend/ml/train_classifier.py``
(a TF-IDF + logistic-regression pipeline over multilingual synthetic scam
scripts). Labels the transcript into fraud categories and returns class
probabilities so the risk engine can decide how strongly to flag.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.detectors.base import BaseDetector

# Category identifiers used by the training script and mapped to red flags by
# the risk engine. Keep in sync with backend/ml/build_dataset.py.
CATEGORIES = ["digital_arrest", "fake_courier", "otp_phishing", "kin_emergency", "other_fraud", "benign", "neutral"]

# Minimum probability for the top class to be trusted.
CONFIDENCE_FLOOR = 0.5

# A fraud category is only trusted when it clearly beats the benign/neutral
# classes. Without this, an ambiguous transcript was forced into the closest
# fraud bucket at low confidence and flagged a benign call.
BENIGN_MARGIN = 0.15

# Longest transcript we will classify (characters) — protects against
# pathological inputs in the classifier's vector space.
MAX_LEN = 20_000


class ScamClassifierDetector(BaseDetector):
    name = "text"
    description = "Known scam-script language-pattern detection (TF-IDF + logistic regression)"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.model_path = self.settings.model_dir / "scam_classifier.joblib"
        self._pipeline: Any = None
        self._load_error: str | None = None

    def available(self) -> bool:
        return self._ensure_pipeline() is not None

    def _ensure_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        if not self.model_path.exists():
            self._load_error = f"model not found at {self.model_path}"
            return None
        try:
            import joblib

            self._pipeline = joblib.load(str(self.model_path))
            return self._pipeline
        except Exception as exc:
            self._load_error = str(exc)
            return None

    def classify(self, text: str) -> dict[str, Any]:
        pipeline = self._ensure_pipeline()
        if pipeline is None:
            return self._result(
                "unavailable",
                detail=f"Scam classifier unavailable: {self._load_error}",
            )
        if not text or not text.strip():
            return self._result("available", score=None, label="no-text", detail="No text to classify.")

        cleaned = text[:MAX_LEN]
        try:
            proba = pipeline.predict_proba([cleaned])[0]
            classes = [str(c) for c in pipeline.classes_]  # native str for JSON
            probs = {c: float(p) for c, p in zip(classes, proba)}
            best_idx = int(proba.argmax())
            best_class = classes[best_idx]
            best_prob = float(proba[best_idx])

            # Trust a fraud category only if it beats benign/neutral by a real
            # margin; otherwise leave the verdict "uncertain" (the risk engine
            # then contributes no text signal at all).
            non_scam = max(probs.get("benign", 0.0), probs.get("neutral", 0.0))
            confident = best_prob >= CONFIDENCE_FLOOR and (
                best_class in ("benign", "neutral") or best_prob - non_scam >= BENIGN_MARGIN
            )
            return self._result(
                "available",
                score=best_prob,
                label=best_class if confident else "uncertain",
                detail=(
                    f"Most likely pattern: {best_class} ({best_prob:.0%})."
                    if confident
                    else "No scam pattern matched with sufficient confidence."
                ),
                metrics={
                    "category": best_class,
                    "probabilities": probs,
                    "top_probability": best_prob,
                    "confident": confident,
                },
            )
        except Exception as exc:
            return self._result("error", detail=f"Classification failed: {exc}")
