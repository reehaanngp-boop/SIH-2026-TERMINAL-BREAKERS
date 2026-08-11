"""Train the scam-script text classifier.

A TF-IDF pipeline over *word and character n-grams* plus a Logistic
Regression head. Character n-grams make the model work across English,
Devanagari and romanised Hindi without language-specific tokenisation.

The saved artifact is a plain ``sklearn.pipeline.Pipeline`` whose public API
(``predict_proba``, ``classes_``) the runtime detector consumes directly.

Pipeline:
    FeatureUnion(word tfidf, char tfidf) -> LogisticRegression(multinomial)

Run:  uv run python ml/train_classifier.py
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "data" / "datasets" / "scam_dataset.jsonl"
OUT_MODEL = PROJECT_ROOT / "data" / "models" / "scam_classifier.joblib"


def _vectorizers() -> FeatureUnion:
    # Language-agnostic: char_wb n-grams capture subword morphology for both
    # Devanagari and romanised text; word n-grams add exact-script cues.
    return FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    sublinear_tf=True, min_df=2, ngram_range=(1, 2), analyzer="word"
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    sublinear_tf=True, min_df=2, ngram_range=(3, 6), analyzer="char_wb"
                ),
            ),
        ]
    )


def load_dataset(path: Path) -> tuple[list[str], list[str]]:
    import json

    texts: list[str] = []
    labels: list[str] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            texts.append(row["text"])
            labels.append(row["label"])
    return texts, labels


def main() -> None:
    texts, labels = load_dataset(DATASET)
    print(f"Loaded {len(texts)} samples across {sorted(set(labels))}")

    # Stratified split so every category appears in both train and test.
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )

    pipeline = Pipeline(
        [
            ("features", _vectorizers()),
            (
                "clf",
                LogisticRegression(
                    C=4.0,
                    max_iter=1200,
                    solver="lbfgs",
                    random_state=42,
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)

    pred = pipeline.predict(X_test)
    acc = (pred == np.asarray(y_test)).mean()
    print(f"\nAccuracy (held-out): {acc:.4f}")
    print("\nClassification report:\n", classification_report(y_test, pred))
    print("\nConfusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(y_test, pred, labels=pipeline.classes_.tolist()))

    OUT_MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, OUT_MODEL)
    print(f"\nSaved pipeline -> {OUT_MODEL}")


if __name__ == "__main__":
    main()
