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

# ---------------------------------------------------------------- APPLY ----
with tab_apply:
    st.subheader("Submit a new application")
    st.write("Fill in your details and attach your supporting documents. "
             "Our AI agents will review everything and, in most cases, give you a decision within minutes.")

    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input("Full name")
        emirates_id = st.text_input("Emirates ID number", placeholder="784-YYYY-XXXXXXX-X")
        date_of_birth = st.date_input("Date of birth", value=None)
        nationality = st.text_input("Nationality", value="UAE")
        phone = st.text_input("Phone number")
    with col2:
        address = st.text_input("Current address")
        family_size = st.number_input("Family size", min_value=1, max_value=20, value=1)
        employment_status = st.selectbox("Employment status",
                                          ["unemployed", "part_time", "full_time", "self_employed", "retired"])
        monthly_income = st.number_input("Monthly income (AED)", min_value=0.0, value=0.0, step=100.0)
        months_employed = st.number_input("Months in current employment", min_value=0, value=0)

    st.markdown("**Supporting documents**")
    d1, d2, d3 = st.columns(3)
    with d1:
        bank_statement = st.file_uploader("Bank statement (.txt/.pdf)", type=["txt", "pdf"])
        emirates_id_doc = st.file_uploader("Emirates ID (.json/.jpg/.png)", type=["json", "jpg", "png"])
    with d2:
        resume = st.file_uploader("Resume (.txt/.pdf)", type=["txt", "pdf"])
        assets_liabilities = st.file_uploader("Assets/liabilities (.xlsx)", type=["xlsx"])
    with d3:
        credit_report = st.file_uploader("Credit report (.txt/.pdf)", type=["txt", "pdf"])

    if st.button("Submit application", type="primary"):
        if not full_name or not emirates_id:
            st.error("Full name and Emirates ID are required.")
        else:
            files = {}
            for key, f in [("bank_statement", bank_statement), ("emirates_id_doc", emirates_id_doc),
                            ("resume", resume), ("assets_liabilities", assets_liabilities),
                            ("credit_report", credit_report)]:
                if f is not None:
                    files[key] = (f.name, f.getvalue())

            data = {
                "full_name": full_name, "emirates_id": emirates_id,
                "date_of_birth": str(date_of_birth) if date_of_birth else "",
                "nationality": nationality, "phone": phone, "address": address,
                "family_size": family_size, "employment_status": employment_status,
                "monthly_income": monthly_income, "months_employed": months_employed,
            }
            with st.spinner("Our AI agents are reviewing your application (extraction → validation → "
                             "eligibility → decision → enablement)..."):
                try:
                    resp = requests.post(f"{API}/applications", data=data, files=files, timeout=120)
                    resp.raise_for_status()
                    result = resp.json()
                    st.session_state["last_result"] = result
                except Exception as e:  # noqa: BLE001
                    st.error(f"Submission failed: {e}. Is the API running at {API}?")
                    result = None

            if result:
                st.success(f"Application ID: `{result['application_id']}`  —  save this to check your status later.")
                decision = result.get("decision")
                badge = {"approved": "✅ Approved", "soft_declined": "⚠️ Soft-declined for direct support",
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

                with st.expander("🔍 Agent reasoning trace (Thought → Action → Observation)"):
                    for step in result.get("trace", []):
                        st.text(f"[{step['agent']}] {step['type'].upper()}: {step['content']}")

                st.caption(f"Processed in {result.get('processing_seconds')}s")

# --------------------------------------------------------------- STATUS ----
with tab_status:
    st.subheader("Check an existing application")
    app_id_lookup = st.text_input("Application ID")
    if st.button("Look up status"):
        try:
            resp = requests.get(f"{API}/applications/{app_id_lookup}", timeout=30)
            if resp.status_code == 200:
                st.json(resp.json())
            else:
                st.error("Application not found.")
        except Exception as e:  # noqa: BLE001
            st.error(f"Lookup failed: {e}")

# ----------------------------------------------------------------- CHAT ----
with tab_chat:
    st.subheader("Ask the assistant")
    st.caption("Ask about eligibility criteria, required documents, or the status of a specific "
               "application (paste the Application ID for personalized context).")

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
                                  timeout=60)
            reply = resp.json().get("reply", "Sorry, I couldn't process that.")
        except Exception as e:  # noqa: BLE001
            reply = f"Chat service unavailable: {e}"
        st.session_state.chat_history.append(("assistant", reply))
        with st.chat_message("assistant"):
            st.write(reply)
