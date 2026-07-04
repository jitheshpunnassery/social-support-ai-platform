"""
Eligibility Assessment Agent
-----------------------------
Merges form + extracted-document data into the engineered feature vector
expected by the trained scikit-learn model, and produces a calibrated
eligibility probability plus the top contributing factors (for
explainability, shown to both the case officer and the applicant).
"""
import joblib
import numpy as np

from agents.base import BaseAgent
from config import settings

_model_bundle = None


def _get_model_bundle():
    global _model_bundle
    if _model_bundle is None:
        _model_bundle = joblib.load(settings.MODEL_PATH)
    return _model_bundle


class EligibilityAgent(BaseAgent):
    name = "eligibility_agent"

    def run(self, state: dict) -> dict:
        self.think(state, "Merging form data and extracted document data into model features, "
                           "then scoring eligibility with the trained classifier.")
        form = state.get("form_data", {})
        extracted = state.get("extracted_data", {})

        features = self.act(state, "build feature vector", lambda: self._build_features(form, extracted))
        state["eligibility_features"] = features

        score, top_factors = self.act(state, "score with ML model", lambda: self._score(features))
        state["ml_score"] = score
        state["top_factors"] = top_factors

        self.think(state, f"Eligibility probability: {score:.3f}. Top factors: {top_factors}")
        return state

    def _build_features(self, form: dict, extracted: dict) -> dict:
        assets_doc = extracted.get("assets_liabilities") or {}
        credit_doc = extracted.get("credit_report") or {}

        monthly_income = float(form.get("monthly_income") or 0)
        family_size = int(form.get("family_size") or 1)
        total_assets = float(assets_doc.get("total_assets", form.get("total_assets", 0)) or 0)
        total_liabilities = float(assets_doc.get("total_liabilities", form.get("total_liabilities", 0)) or 0)
        credit_score = int(credit_doc.get("credit_score", form.get("credit_score", 650)) or 650)
        months_employed = int(form.get("months_employed") or 0)
        dependents = max(0, family_size - 1)

        per_capita_income = monthly_income / family_size if family_size else monthly_income
        debt_to_asset = total_liabilities / (total_assets + 1)

        return {
            "family_size": family_size,
            "dependents": dependents,
            "months_employed": months_employed,
            "monthly_income": monthly_income,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "credit_score": credit_score,
            "per_capita_income": round(per_capita_income, 2),
            "debt_to_asset_ratio": round(debt_to_asset, 3),
            "employment_status": form.get("employment_status", "unemployed"),
            "nationality": form.get("nationality", "UAE"),
        }

    def _score(self, features: dict):
        bundle = _get_model_bundle()
        model = bundle["model"]
        import pandas as pd
        X = pd.DataFrame([features])[bundle["feature_names"]]
        proba = float(model.predict_proba(X)[0, 1])

        # Simple, transparent "top factors" explanation using domain rules
        # (kept separate from the model's internal tree splits for
        # readability to non-technical case officers).
        factors = []
        if features["per_capita_income"] < 1500:
            factors.append("low per-capita household income")
        if features["employment_status"] == "unemployed":
            factors.append("currently unemployed")
        if features["debt_to_asset_ratio"] > 1.5:
            factors.append("high debt-to-asset ratio")
        if features["credit_score"] < 500:
            factors.append("low credit score")
        if not factors:
            factors.append("overall financial profile within self-sufficiency range")

        return proba, factors
