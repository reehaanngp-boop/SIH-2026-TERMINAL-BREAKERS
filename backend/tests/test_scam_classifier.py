"""Tests for the trained scam-script classifier (skipped if model is absent)."""

from __future__ import annotations

import pytest

from app.detectors.text.scam_classifier import ScamClassifierDetector


@pytest.fixture(scope="module")
def detector() -> ScamClassifierDetector:
    d = ScamClassifierDetector()
    if not d.available():
        pytest.skip("scam_classifier.joblib not found — run ml/train_classifier.py first")
    return d


SCAM_CASES = [
    "this is the CBI, you are under digital arrest, stay on the video call, pay the verification fee now",
    "a parcel in your name contains drugs and foreign currency, pay the customs clearance fee to release it",
    "your bank account will be blocked, share the OTP you received to verify your KYC",
    "mama it is me, I am in trouble, the police want bail money, transfer it urgently and do not tell anyone",
    "congratulations you have won a lottery, pay the processing fee to claim your prize",
    "yeh CBI hai, aap digital arrest ho, turant verification fee jama karo",
]


def test_scam_cases_flagged(detector: ScamClassifierDetector):
    for text in SCAM_CASES:
        res = detector.classify(text)
        assert res["status"] == "available", res
        assert res["label"] not in ("benign", "uncertain"), (text, res["label"])


def test_benign_not_flagged(detector: ScamClassifierDetector):
    # Includes transcripts that mention money / courier / banks in a *legit*
    # context — the model must not over-eagerly force these into a fraud bucket.
    benign = [
        "good morning, this is the restaurant calling to confirm your food order",
        "hi dad, I will reach home by evening, no need to worry",
        "the meeting has been moved to three pm today",
        "your food delivery is at the gate, please collect it",
        "your parcel will be delivered tomorrow morning by the courier company",
        "this is the bank calling to confirm you received our new card",
        "your electricity bill for this month has been paid successfully",
        "yeh courier company se bol rahe hain, aapka parcel kal subah deliver hoga",
    ]
    for text in benign:
        res = detector.classify(text)
        assert res["status"] == "available", res
        assert res["label"] == "benign", (text, res["label"])


def test_neutral_not_flagged(detector: ScamClassifierDetector):
    neutral = [
        "hello, sorry I think I dialed the wrong number",
        "are you free this evening to catch up, let me check my calendar",
        "kya aap meri baat sun paa rahe ho, network kamzor hai",
    ]
    for text in neutral:
        res = detector.classify(text)
        assert res["status"] == "available", res
        assert res["label"] == "neutral", (text, res["label"])


def test_missing_text_returns_no_text(detector: ScamClassifierDetector):
    res = detector.classify("   ")
    assert res["label"] == "no-text"


def test_probabilities_sum_to_one(detector: ScamClassifierDetector):
    res = detector.classify(SCAM_CASES[0])
    probs = res["metrics"]["probabilities"]
    assert abs(sum(probs.values()) - 1.0) < 1e-6
