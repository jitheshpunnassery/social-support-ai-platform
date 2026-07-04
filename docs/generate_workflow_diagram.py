import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(13, 7))
ax.set_xlim(0, 130)
ax.set_ylim(0, 60)
ax.axis("off")


def box(x, y, w, h, text, color, fontsize=9, textcolor="#1a1a1a"):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2",
                           linewidth=1.1, edgecolor="#444441", facecolor=color, zorder=2)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
             color=textcolor, weight="bold", zorder=3)


def diamond(x, y, w, h, text, color, fontsize=8.5):
    from matplotlib.patches import Polygon
    pts = [(x, y + h / 2), (x + w / 2, y + h), (x + w, y + h / 2), (x + w / 2, y)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor="#444441", linewidth=1.1, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, weight="bold", zorder=3)


def arrow(x1, y1, x2, y2, color="#5F5E5A", lw=1.4, label=None, label_offset=(0, 1.5)):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
                         color=color, linewidth=lw, zorder=1)
    ax.add_patch(a)
    if label:
        ax.text((x1 + x2) / 2 + label_offset[0], (y1 + y2) / 2 + label_offset[1], label,
                 ha="center", fontsize=7.5, color=color)


ax.text(65, 57.5, "Application Processing Workflow (ReAct agent pipeline)", ha="center",
        fontsize=14, weight="bold")

box(2, 42, 16, 8, "Intake\n(form + docs)", "#CECBF6")
box(23, 42, 18, 8, "Data\nExtraction Agent", "#9FE1CB")
box(46, 42, 18, 8, "Data\nValidation Agent", "#9FE1CB")
box(69, 42, 18, 8, "Eligibility\nAssessment Agent\n(ML score)", "#9FE1CB")
box(92, 42, 18, 8, "Decision\nAgent", "#9FE1CB")
box(112, 42, 16, 8, "Enablement\nAgent", "#5DCAA5")

arrow(18, 46, 23, 46)
arrow(41, 46, 46, 46)
arrow(64, 46, 69, 46)
arrow(87, 46, 92, 46)
arrow(110, 46, 112, 46)

# Decision branch
diamond(90, 22, 22, 12, "Severity /\nScore band?", "#FAC775", fontsize=8)
arrow(101, 42, 101, 34)

box(60, 6, 20, 8, "Auto-approved\n(score >= 0.80)", "#5DCAA5")
box(84, 6, 20, 8, "Human review\n(flags or borderline)", "#F0997B")
box(108, 6, 20, 8, "Soft-declined +\nenablement path", "#D4537E", textcolor="#fff")

arrow(96, 22, 70, 14, label="high score,\nno flags")
arrow(101, 22, 94, 14, label="flags or\nborderline")
arrow(107, 22, 118, 14, label="low score")

# Human-in-the-loop note
ax.text(65, 34, "High-severity data-validation flags\nalways force human review,\nregardless of ML score", ha="center",
        fontsize=8, style="italic", color="#712B13")

plt.tight_layout()
plt.savefig("/home/claude/ssai-phased/docs/workflow_diagram.png", dpi=200, bbox_inches="tight")
print("saved")
