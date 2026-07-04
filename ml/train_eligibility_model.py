"""
Trains the eligibility classifier used by the Eligibility Assessment Agent.

Model choice rationale (see solution summary doc for full justification):
  - Gradient Boosted Trees (HistGradientBoostingClassifier) chosen over
    logistic regression / plain decision tree / SVM because:
      * The feature set mixes skewed continuous variables (income, assets,
        liabilities) with categorical variables (employment status) and
        non-linear interactions (e.g. per-capita income thresholds combined
        with debt ratios) -> tree ensembles capture this without heavy
        feature engineering or scaling.
      * Native handling of missing values (common with partially-extracted
        documents) via HistGradientBoostingClassifier's built-in NaN support.
      * Outputs well-calibrated-enough probabilities for the
        approve / soft-decline / human-review threshold banding.
      * Fast to retrain (~seconds) on modest data volumes and cheap to run
        locally with no GPU, matching the "locally hosted" requirement.
  - A plain interpretable LogisticRegression is also trained and stored
    alongside as a fallback / explainability baseline (coefficients are
    reported to case officers for the "why" behind borderline decisions).

Run: python ml/train_eligibility_model.py
Outputs: ml/eligibility_model.pkl (dict with 'model', 'encoder', 'feature_names', 'metrics')
"""
import os
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "synthetic", "applicants.csv")
MODEL_PATH = os.path.join(BASE_DIR, "eligibility_model.pkl")

NUMERIC_FEATURES = [
    "family_size", "dependents", "months_employed", "monthly_income",
    "total_assets", "total_liabilities", "credit_score",
    "per_capita_income", "debt_to_asset_ratio",
]
CATEGORICAL_FEATURES = ["employment_status", "nationality"]
TARGET = "eligible_label"


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    model = HistGradientBoostingClassifier(
        max_depth=6, learning_rate=0.08, max_iter=250, random_state=42,
        l2_regularization=0.1,
    )
    return Pipeline([("prep", preprocessor), ("clf", model)])


def build_baseline_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    return Pipeline([("prep", preprocessor), ("clf", LogisticRegression(max_iter=1000))])


def main():
    df = pd.read_csv(DATA_PATH)
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    proba = pipeline.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)

    auc = roc_auc_score(y_test, proba)
    report = classification_report(y_test, preds, output_dict=True)
    cm = confusion_matrix(y_test, preds).tolist()

    baseline = build_baseline_pipeline()
    baseline.fit(X_train, y_train)
    baseline_auc = roc_auc_score(y_test, baseline.predict_proba(X_test)[:, 1])

    metrics = {
        "primary_model": "HistGradientBoostingClassifier",
        "roc_auc": round(float(auc), 4),
        "baseline_logreg_roc_auc": round(float(baseline_auc), 4),
        "confusion_matrix": cm,
        "classification_report": report,
        "n_train": len(X_train),
        "n_test": len(X_test),
    }

    joblib.dump({
        "model": pipeline,
        "baseline_model": baseline,
        "feature_names": NUMERIC_FEATURES + CATEGORICAL_FEATURES,
        "metrics": metrics,
    }, MODEL_PATH)

    print(json.dumps(metrics, indent=2))
    print(f"\nSaved model -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
