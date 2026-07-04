"""
Generates synthetic applicant records + multimodal documents (bank statement
text, Emirates ID fields, resume text, assets/liabilities Excel, credit
report fields) so the prototype can be demoed and the ML model trained
without any real applicant data.

Run: python data/synthetic_data_generator.py
Outputs:
  data/synthetic/applicants.csv          -> tabular training data for ML model
  data/synthetic/sample_documents/*.xlsx -> sample assets/liabilities workbook
  data/synthetic/sample_documents/*.txt  -> sample bank statement / resume / credit report text
"""
import os
import random
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

OUT_DIR = os.path.join(os.path.dirname(__file__), "synthetic")
DOC_DIR = os.path.join(OUT_DIR, "sample_documents")
os.makedirs(DOC_DIR, exist_ok=True)

FIRST_NAMES = ["Ahmed", "Fatima", "Mohammed", "Aisha", "Khalid", "Mariam", "Omar",
               "Layla", "Saeed", "Noura", "Hassan", "Salma", "Yousef", "Huda"]
LAST_NAMES = ["Al Mansoori", "Al Suwaidi", "Al Falasi", "Al Nuaimi", "Al Kaabi",
              "Al Shamsi", "Al Marri", "Al Zaabi", "Al Hashimi"]
NATIONALITIES = ["UAE", "Egypt", "Jordan", "India", "Pakistan", "Philippines", "Sudan"]
EMPLOYMENT = ["unemployed", "part_time", "full_time", "self_employed", "retired"]


def rand_emirates_id():
    return f"784-{random.randint(1980,2005)}-{random.randint(1000000,9999999)}-{random.randint(0,9)}"


def make_applicant(i: int) -> dict:
    employment_status = random.choices(EMPLOYMENT, weights=[0.30, 0.20, 0.20, 0.15, 0.15])[0]
    if employment_status == "unemployed":
        income = round(np.random.exponential(400), 2)
    elif employment_status == "part_time":
        income = round(np.random.normal(3500, 1200), 2)
    elif employment_status == "self_employed":
        income = round(np.random.normal(6000, 4000), 2)
    elif employment_status == "retired":
        income = round(np.random.normal(3000, 1000), 2)
    else:
        income = round(np.random.normal(9000, 4000), 2)
    income = max(0, income)

    family_size = np.random.choice([1, 2, 3, 4, 5, 6, 7, 8], p=[0.10, 0.15, 0.18, 0.20, 0.15, 0.12, 0.06, 0.04])
    dependents = max(0, family_size - 1)

    total_assets = round(max(0, np.random.exponential(50000)), 2)
    total_liabilities = round(max(0, np.random.exponential(30000)), 2)
    credit_score = int(np.clip(np.random.normal(650, 120), 300, 900))

    months_employed = 0 if employment_status == "unemployed" else int(np.random.exponential(36))

    # ---- ground-truth eligibility label (rules the synthetic generator itself
    # believes -> used ONLY to create a plausible training label; the ML model
    # then learns a smoother decision boundary from the engineered features) ----
    per_capita_income = income / family_size
    debt_to_asset = total_liabilities / (total_assets + 1)
    needs_support = (
        per_capita_income < 1500
        or employment_status == "unemployed"
        or (debt_to_asset > 1.5 and per_capita_income < 3000)
    )
    # small noise so the boundary isn't perfectly linear / trivially learnable
    flip = np.random.rand() < 0.05
    eligible = needs_support if not flip else (not needs_support)

    dob = date.today() - timedelta(days=random.randint(18, 70) * 365)

    return {
        "applicant_id": f"APP{i:05d}",
        "full_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "emirates_id": rand_emirates_id(),
        "date_of_birth": dob.isoformat(),
        "nationality": random.choice(NATIONALITIES),
        "family_size": int(family_size),
        "dependents": int(dependents),
        "employment_status": employment_status,
        "months_employed": months_employed,
        "monthly_income": income,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "credit_score": credit_score,
        "per_capita_income": round(per_capita_income, 2),
        "debt_to_asset_ratio": round(debt_to_asset, 3),
        "eligible_label": int(eligible),
    }


def generate_applicants(n=2000) -> pd.DataFrame:
    rows = [make_applicant(i) for i in range(1, n + 1)]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_DIR, "applicants.csv"), index=False)
    print(f"Wrote {len(df)} synthetic applicants -> data/synthetic/applicants.csv")
    return df


def generate_sample_documents(n=5):
    """Writes a handful of illustrative raw 'documents' per data type, mimicking
    what the Data Extraction Agent would receive (used for demo/testing the
    extraction agent's parsing logic)."""
    for i in range(1, n + 1):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        eid = rand_emirates_id()

        # Bank statement (plain text mimicking OCR/PDF-text extraction output)
        lines = [f"BANK STATEMENT - Account Holder: {name}", f"Emirates ID: {eid}", "Period: Jan 2026 - Mar 2026", ""]
        balance = round(np.random.uniform(500, 20000), 2)
        for m in range(3):
            credit = round(np.random.uniform(0, 9000), 2)
            debit = round(np.random.uniform(0, 8000), 2)
            balance = balance + credit - debit
            lines.append(f"2026-0{m+1}-25  SALARY/DEPOSIT  +{credit:.2f}  WITHDRAWALS -{debit:.2f}  BALANCE {balance:.2f}")
        with open(os.path.join(DOC_DIR, f"bank_statement_{i}.txt"), "w") as f:
            f.write("\n".join(lines))

        # Emirates ID (structured fields, mimicking OCR key-value extraction)
        eid_fields = {
            "id_number": eid,
            "name_en": name,
            "nationality": random.choice(NATIONALITIES),
            "date_of_birth": (date.today() - timedelta(days=random.randint(20, 60) * 365)).isoformat(),
            "expiry_date": (date.today() + timedelta(days=random.randint(30, 1500))).isoformat(),
            "sex": random.choice(["M", "F"]),
        }
        with open(os.path.join(DOC_DIR, f"emirates_id_{i}.json"), "w") as f:
            json.dump(eid_fields, f, indent=2)

        # Resume (plain text)
        skills = random.sample(["Excel", "Customer Service", "Driving", "Retail",
                                 "Construction", "Nursing Aide", "IT Support", "Arabic/English Translation"], 3)
        resume = f"""RESUME - {name}
Objective: Seeking employment opportunities to support my family.
Experience: {random.randint(0,15)} years across {random.choice(EMPLOYMENT)} roles.
Skills: {', '.join(skills)}
Education: {random.choice(['Secondary School', 'Diploma', "Bachelor's Degree", 'No formal education'])}
"""
        with open(os.path.join(DOC_DIR, f"resume_{i}.txt"), "w") as f:
            f.write(resume)

        # Assets/liabilities Excel
        assets_df = pd.DataFrame({
            "Item": ["Savings Account", "Property", "Vehicle", "Other Assets"],
            "Value_AED": [round(np.random.uniform(0, 30000), 2), round(np.random.uniform(0, 400000), 2),
                          round(np.random.uniform(0, 80000), 2), round(np.random.uniform(0, 10000), 2)],
        })
        liabilities_df = pd.DataFrame({
            "Item": ["Personal Loan", "Credit Card Debt", "Mortgage", "Other Debt"],
            "Value_AED": [round(np.random.uniform(0, 50000), 2), round(np.random.uniform(0, 20000), 2),
                          round(np.random.uniform(0, 300000), 2), round(np.random.uniform(0, 5000), 2)],
        })
        with pd.ExcelWriter(os.path.join(DOC_DIR, f"assets_liabilities_{i}.xlsx")) as writer:
            assets_df.to_excel(writer, sheet_name="Assets", index=False)
            liabilities_df.to_excel(writer, sheet_name="Liabilities", index=False)

        # Credit report (plain text)
        credit_report = f"""CREDIT BUREAU REPORT
Name: {name}
Emirates ID: {eid}
Credit Score: {int(np.clip(np.random.normal(650, 120), 300, 900))}
Address on file: {random.randint(1,900)} Sheikh Zayed Road, Dubai
Active Loans: {random.randint(0,3)}
Delinquencies (last 24mo): {random.randint(0,2)}
"""
        with open(os.path.join(DOC_DIR, f"credit_report_{i}.txt"), "w") as f:
            f.write(credit_report)

    print(f"Wrote {n} sample multimodal document sets -> data/synthetic/sample_documents/")


if __name__ == "__main__":
    generate_applicants(2000)
    generate_sample_documents(5)
