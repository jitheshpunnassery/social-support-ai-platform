"""
Economic Enablement Recommendation Agent
-------------------------------------------
Runs for every applicant (not just declines) to suggest upskilling,
training, job-matching, or career-counseling pathways, using resume-
extracted skills/education plus employment status. Combines a curated
programme catalog (rule-based matching -> deterministic, auditable) with
an LLM pass that turns the matches into a friendly, personalized narrative.
"""
from agents.base import BaseAgent
from agents.llm_client import llm_client

PROGRAM_CATALOG = [
    {"name": "Digital Skills Bootcamp", "target_skills": ["IT Support", "Excel"], "for_status": ["unemployed", "part_time"]},
    {"name": "Vocational Trades Certification", "target_skills": ["Construction", "Driving"], "for_status": ["unemployed"]},
    {"name": "Healthcare Support Training", "target_skills": ["Nursing Aide"], "for_status": ["unemployed", "part_time"]},
    {"name": "Retail & Customer Service Pathway", "target_skills": ["Retail", "Customer Service"], "for_status": ["unemployed", "part_time"]},
    {"name": "Small Business / Self-Employment Accelerator", "target_skills": [], "for_status": ["self_employed", "unemployed"]},
    {"name": "Career Counseling & Job Matching Service", "target_skills": [], "for_status": ["unemployed", "part_time", "retired"]},
]


class EnablementAgent(BaseAgent):
    name = "enablement_agent"

    def run(self, state: dict) -> dict:
        self.think(state, "Matching applicant skills/employment status against the enablement "
                           "programme catalog to recommend upskilling and job-matching support.")
        form = state.get("form_data", {})
        resume = (state.get("extracted_data") or {}).get("resume") or {}
        employment_status = form.get("employment_status", "unemployed")
        skills = resume.get("skills", []) or []

        matches = self.act(state, "match programmes",
                            lambda: self._match_programs(employment_status, skills))
        state["enablement_recommendations"] = matches

        if matches:
            narrative = llm_client.chat(
                "You are a career counselor. Write a warm, encouraging 2-3 sentence summary "
                "recommending these programmes to an applicant.",
                f"Programmes: {[m['name'] for m in matches]}. Applicant skills: {skills}. "
                f"Employment status: {employment_status}.",
            )
            state["enablement_narrative"] = narrative
        else:
            state["enablement_narrative"] = "No additional enablement programmes matched at this time."

        self.think(state, f"Matched {len(matches)} enablement programme(s).")
        return state

    def _match_programs(self, employment_status: str, skills: list) -> list:
        matches = []
        for program in PROGRAM_CATALOG:
            status_ok = employment_status in program["for_status"]
            skill_overlap = set(skills) & set(program["target_skills"])
            if status_ok and (skill_overlap or not program["target_skills"]):
                matches.append({"name": program["name"],
                                 "matched_on": list(skill_overlap) or ["employment status"]})
        return matches[:3]
