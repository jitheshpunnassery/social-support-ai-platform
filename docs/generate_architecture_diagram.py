import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(13, 9.5))
ax.set_xlim(0, 130)
ax.set_ylim(0, 95)
ax.axis("off")

COLORS = {
    "ui": "#CECBF6", "api": "#B5D4F4", "agent": "#9FE1CB", "orch": "#5DCAA5",
    "data": "#FAC775", "ml": "#F0997B", "obs": "#B4B2A9", "ext": "#F4C0D1",
}
EDGE = "#3C3489"


def box(x, y, w, h, text, color, fontsize=9, textcolor="#1a1a1a", weight="bold"):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2",
                           linewidth=1.1, edgecolor="#444441", facecolor=color, zorder=2)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
             color=textcolor, weight=weight, zorder=3, wrap=True)


def arrow(x1, y1, x2, y2, color="#5F5E5A", style="-|>", lw=1.3, ls="solid"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                         color=color, linewidth=lw, linestyle=ls, zorder=1)
    ax.add_patch(a)


# Title
ax.text(65, 92.5, "Social Support AI Workflow — High-Level Architecture", ha="center",
        fontsize=15, weight="bold")

# --- Layer 1: Front-end / interaction ---
box(3, 82, 26, 7, "Applicant / Case Officer\n(Streamlit Chat UI)", COLORS["ui"])
box(33, 82, 26, 7, "REST API\n(FastAPI, /applications /chat)", COLORS["api"])
box(63, 82, 26, 7, "API Gateway concerns:\nAuthN, rate limiting, CORS", COLORS["ext"], fontsize=8)
box(93, 82, 30, 7, "Langfuse\n(Agent Observability)", COLORS["obs"])

arrow(29, 85.5, 33, 85.5)
arrow(93, 85.5, 89, 85.5)

# --- Layer 2: Master Orchestrator ---
box(30, 70, 40, 8, "Master Orchestrator\n(LangGraph StateGraph, ReAct)", COLORS["orch"], fontsize=10)
arrow(46, 82, 48, 78)

# --- Layer 3: Specialist Agents ---
agent_y = 55
agent_w = 22
agents = [
    ("Data Extraction\nAgent", 3),
    ("Data Validation\nAgent", 27),
    ("Eligibility\nAssessment Agent", 51),
    ("Decision\nRecommendation Agent", 75),
    ("Economic Enablement\nAgent", 99),
]
for label, x in agents:
    box(x, agent_y, agent_w, 10, label, COLORS["agent"], fontsize=8.5)

# orchestrator to each agent
for label, x in agents:
    arrow(50, 70, x + agent_w / 2, agent_y + 10, color="#0F6E56", lw=1)

# sequential flow arrows between agents
for i in range(len(agents) - 1):
    x1 = agents[i][1] + agent_w
    x2 = agents[i + 1][1]
    arrow(x1, agent_y + 5, x2, agent_y + 5, color="#26215C", lw=1.6)

# --- Layer 4: ML + LLM services ---
box(3, 40, 26, 8, "scikit-learn Eligibility\nClassifier (local)", COLORS["ml"])
box(33, 40, 26, 8, "Local LLM Server\n(Ollama: llama3.1 / llava)", COLORS["ml"])
box(63, 40, 26, 8, "Vector Search (RAG)\nQdrant policy corpus", COLORS["ml"])
box(93, 40, 30, 8, "Graph Relationships\nNeo4j household/doc links", COLORS["ml"])

arrow(51, 55, 16, 48, color="#993C1D", lw=1)
arrow(51, 55, 46, 48, color="#993C1D", lw=1)
arrow(75, 55, 76, 48, color="#993C1D", lw=1)
arrow(99, 55, 108, 48, color="#993C1D", lw=1)

# --- Layer 5: Data pipeline ---
box(3, 22, 26, 8, "PostgreSQL\napplicants, applications,\ndecisions, audit trail", COLORS["data"], fontsize=8)
box(33, 22, 26, 8, "MongoDB\nraw multimodal\ndocument content", COLORS["data"], fontsize=8)
box(63, 22, 26, 8, "Qdrant\npolicy + precedent\nembeddings", COLORS["data"], fontsize=8)
box(93, 22, 30, 8, "Neo4j\napplicant/household/\ndocument graph", COLORS["data"], fontsize=8)

arrow(16, 40, 16, 30, color="#854F0B", lw=1)
arrow(46, 40, 46, 30, color="#854F0B", lw=1)
arrow(76, 40, 76, 30, color="#854F0B", lw=1)
arrow(108, 40, 108, 30, color="#854F0B", lw=1)

# --- Layer 6: Ingestion ---
box(20, 6, 90, 9, "Multimodal Ingestion: application form • bank statement (PDF/OCR) • Emirates ID (image/OCR)\n"
                    "• resume (text/LLM) • assets & liabilities (Excel) • credit report (text)",
    "#F1EFE8", fontsize=8.5, weight="normal")
arrow(65, 22, 65, 15, color="#444441", lw=1.4)

plt.tight_layout()
plt.savefig("/home/claude/social-support-ai/docs/architecture_diagram.png", dpi=200, bbox_inches="tight")
print("saved")
