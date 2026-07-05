import os
import sys
import requests
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings  # noqa: E402

st.set_page_config(page_title="Social Support AI", page_icon="🤝", layout="wide")
API = settings.API_BASE_URL

st.title("🤝 Social Support & Economic Enablement — AI Assistant")
st.caption("Prototype: multi-agent GenAI workflow for social support application intake, "
           "validation, eligibility assessment, and decisioning.")

tab_apply, tab_status, tab_chat = st.tabs(["📝 New Application", "📋 Check Status", "💬 Chat with the Assistant"])

GENDER_OPTIONS = ["Select...", "Male", "Female"]
MARITAL_STATUS_OPTIONS = ["Select...", "Single", "Married", "Divorced", "Widowed"]
EMIRATE_OPTIONS = ["Select...", "Abu Dhabi", "Dubai", "Sharjah", "Ajman",
                    "Umm Al Quwain", "Ras Al Khaimah", "Fujairah"]
RESIDENCY_STATUS_OPTIONS = ["Select...", "UAE National", "GCC National",
                              "Resident Expatriate", "Visit Visa", "Other"]

with tab_apply:
    st.subheader("Submit a new application")
    st.caption("All personal information fields below are required.")

    with st.form("application_form", clear_on_submit=False):
        st.markdown("**Personal Information**")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name *")
            emirates_id = st.text_input("Emirates ID Number *", placeholder="784-YYYY-XXXXXXX-X")
            date_of_birth = st.date_input("Date of Birth *", value=None, min_value=None)
            gender = st.selectbox("Gender *", GENDER_OPTIONS)
            nationality = st.text_input("Nationality *")
            marital_status = st.selectbox("Marital Status *", MARITAL_STATUS_OPTIONS)
        with col2:
            mobile_number = st.text_input("Mobile Number *", placeholder="+971 5X XXX XXXX")
            email = st.text_input("Email Address *", placeholder="name@example.com")
            address = st.text_input("Current Residential Address *")
            emirate = st.selectbox("Emirate *", EMIRATE_OPTIONS)
            residency_status = st.selectbox("Residency Status *", RESIDENCY_STATUS_OPTIONS)

        st.markdown("**Household & Employment**")
        col3, col4 = st.columns(2)
        with col3:
            family_size = st.number_input("Family size", min_value=1, max_value=20, value=1)
            employment_status = st.selectbox("Employment status",
                                              ["unemployed", "part_time", "full_time", "self_employed", "retired"])
        with col4:
            monthly_income = st.number_input("Monthly income (AED)", min_value=0.0, value=0.0, step=100.0)
            months_employed = st.number_input("Months in current employment", min_value=0, value=0)

        st.markdown("**Supporting documents**")
        d1, d2, d3 = st.columns(3)
        with d1:
            bank_statement = st.file_uploader("Bank statement (.pdf/.doc/.docx/.txt)",
                                                type=["pdf", "doc", "docx", "txt"])
            emirates_id_doc = st.file_uploader("Emirates ID (.pdf/.doc/.docx/.json)",
                                                 type=["pdf", "doc", "docx", "json"])
        with d2:
            resume = st.file_uploader("Resume (.pdf/.doc/.docx/.txt)",
                                        type=["pdf", "doc", "docx", "txt"])
            assets_liabilities = st.file_uploader("Assets/liabilities (.xlsx)", type=["xlsx"])
        with d3:
            credit_report = st.file_uploader("Credit report (.pdf/.doc/.docx/.txt)",
                                               type=["pdf", "doc", "docx", "txt"])

        submitted = st.form_submit_button("Submit application", type="primary")

    if submitted:
        full_name = (full_name or "").strip()
        emirates_id = (emirates_id or "").strip()
        nationality = (nationality or "").strip()
        mobile_number = (mobile_number or "").strip()
        email = (email or "").strip()
        address = (address or "").strip()

        missing = []
        if not full_name:
            missing.append("Full Name")
        if not emirates_id:
            missing.append("Emirates ID Number")
        if not date_of_birth:
            missing.append("Date of Birth")
        if gender == "Select...":
            missing.append("Gender")
        if not nationality:
            missing.append("Nationality")
        if marital_status == "Select...":
            missing.append("Marital Status")
        if not mobile_number:
            missing.append("Mobile Number")
        if not email:
            missing.append("Email Address")
        if not address:
            missing.append("Current Residential Address")
        if emirate == "Select...":
            missing.append("Emirate")
        if residency_status == "Select...":
            missing.append("Residency Status")

        if missing:
            st.error("Please complete the following required field(s): " + ", ".join(missing))
        elif "@" not in email or "." not in email.split("@")[-1]:
            st.error("Please enter a valid email address.")
        else:
            files = {}
            for key, f in [("bank_statement", bank_statement), ("emirates_id_doc", emirates_id_doc),
                            ("resume", resume), ("assets_liabilities", assets_liabilities),
                            ("credit_report", credit_report)]:
                if f is not None:
                    files[key] = (f.name, f.getvalue())

            data = {
                "full_name": full_name, "emirates_id": emirates_id,
                "date_of_birth": str(date_of_birth), "gender": gender,
                "nationality": nationality, "marital_status": marital_status,
                "mobile_number": mobile_number, "email": email, "address": address,
                "emirate": emirate, "residency_status": residency_status,
                "family_size": family_size, "employment_status": employment_status,
                "monthly_income": monthly_income, "months_employed": months_employed,
            }
            with st.spinner("Our AI agents are reviewing your application..."):
                try:
                    resp = requests.post(f"{API}/applications", data=data, files=files,
                                          timeout=settings.REQUEST_TIMEOUT_SECONDS)
                    resp.raise_for_status()
                    result = resp.json()
                except Exception as e:  # noqa: BLE001
                    st.error(f"Submission failed: {e}. Is the API running at {API}?")
                    result = None

            if result:
                st.success(f"Application ID: `{result['application_id']}`")
                decision = result.get("decision")
                badge = {"approved": "✅ Approved", "soft_declined": "⚠️ Soft-declined",
                         "needs_human_review": "🕵️ Routed to human case officer"}.get(decision, decision)
                st.metric("Decision", badge)
                if result.get("ml_score") is not None:
                    st.progress(min(1.0, result["ml_score"]), text=f"Eligibility score: {result['ml_score']:.2f}")
                st.write(result.get("decision_reason", ""))

                if result.get("enablement_recommendations"):
                    st.markdown("**Recommended enablement programmes:**")
                    for rec in result["enablement_recommendations"]:
                        st.write(f"- {rec['name']} (matched on: {', '.join(rec['matched_on'])})")
                    if result.get("enablement_narrative"):
                        st.info(result["enablement_narrative"])

                if result.get("validation_report", {}).get("flags"):
                    with st.expander("⚠️ Data consistency flags"):
                        for flag in result["validation_report"]["flags"]:
                            st.write(f"**{flag['field']}** ({flag['severity']}): {flag['detail']}")

                with st.expander("🔍 Agent reasoning trace"):
                    for step in result.get("trace", []):
                        st.text(f"[{step['agent']}] {step['type'].upper()}: {step['content']}")

with tab_status:
    st.subheader("Check an existing application")
    with st.form("status_lookup_form"):
        app_id_lookup = st.text_input("Application ID")
        lookup_submitted = st.form_submit_button("Look up status")

    if lookup_submitted:
        app_id_lookup = (app_id_lookup or "").strip()
        if not app_id_lookup:
            st.error("Please enter an Application ID.")
        else:
            try:
                resp = requests.get(f"{API}/applications/{app_id_lookup}", timeout=30)
                if resp.status_code == 200:
                    st.json(resp.json())
                else:
                    st.error("Application not found.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Lookup failed: {e}")

with tab_chat:
    st.subheader("Ask the assistant")
    st.caption("Ask about eligibility criteria, required documents, or the status of a specific "
               "application (paste the Application ID for personalized context). Powered by a "
               "locally hosted LLM via Ollama.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_app_id = st.text_input("Application ID (optional, for status-aware answers)", key="chat_app_id")

    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(msg)

    user_msg = st.chat_input("Type your question...")
    if user_msg:
        st.session_state.chat_history.append(("user", user_msg))
        with st.chat_message("user"):
            st.write(user_msg)
        try:
            resp = requests.post(f"{API}/chat", json={"application_id": chat_app_id or None, "message": user_msg},
                                  timeout=settings.REQUEST_TIMEOUT_SECONDS)
            reply = resp.json().get("reply", "Sorry, I couldn't process that.")
        except Exception as e:  # noqa: BLE001
            reply = f"Chat service unavailable: {e}"
        st.session_state.chat_history.append(("assistant", reply))
        with st.chat_message("assistant"):
            st.write(reply)
