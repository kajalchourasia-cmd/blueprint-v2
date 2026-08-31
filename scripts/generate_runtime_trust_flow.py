"""Generate Blueprint's review-only runtime trust, memory, and latency flow.

This figure is intentionally standalone until the user approves it. Running the
script does not edit README.md, the submission document, or the figure index.
"""

from __future__ import annotations

import generate_project_canvas_poster as base


STEM = "14-runtime-trust-memory-latency-flow"


def connector_label(p: base.Poster, x: float, y: float, value: str, color: str) -> None:
    width = max(84, len(value) * 6.1 + 22)
    p.rect(x - width / 2, y - 12, width, 24, base.WHITE, color, 12, 1)
    p.text(x, y - 8, value.upper(), 9, color, bold=True, anchor="center")


def compact_step(
    p: base.Poster,
    x: float,
    y: float,
    w: float,
    h: float,
    number: str,
    title: str,
    body: str,
    fill: str = base.WHITE,
    stroke: str = base.LINE,
) -> None:
    p.rect(x, y, w, h, fill, stroke, 12, 1)
    p.circle(x + 24, y + 26, 13, stroke if stroke != base.LINE else base.MUTED,
             stroke if stroke != base.LINE else base.MUTED)
    p.text(x + 24, y + 12, number, 12, base.WHITE, bold=True, anchor="center")
    p.text(x + 48, y + 10, title, 16, base.INK, bold=True)
    p.wrapped(x + 48, y + 36, body, w - 64, 12, base.MUTED, gap=3, max_lines=2)


def build() -> None:
    # A little taller than the project canvas so every label stays readable.
    base.H = 1200
    p = base.Poster()

    # Header
    p.rect(22, 20, 1876, 86, base.SOFT, base.LINE, 18, 1)
    p.node_icon(42, 37)
    p.text(112, 31, "Blueprint — Runtime Trust, Memory & Latency Flow", 29, base.INK, bold=True)
    p.text(
        112,
        68,
        "How the system answers quickly, deepens research safely, remembers deliberately, and returns control to the founder.",
        14,
        base.MUTED,
    )
    p.text(1874, 37, "REVIEW ASSET · V1", 13, base.BLUE, bold=True, anchor="right")
    p.text(1874, 67, "Human approval is a control plane—not one final button", 13, base.MUTED, anchor="right")

    # Surfaces
    left_x, left_w = 22, 416
    center_x, center_w = 456, 990
    right_x, right_w = 1464, 434
    top_y, panel_h = 124, 960
    p.rect(left_x, top_y, left_w, panel_h, base.WHITE, base.LINE, 18, 1)
    p.rect(center_x, top_y, center_w, panel_h, base.WHITE, base.BLUE, 18, 1)
    p.rect(right_x, top_y, right_w, panel_h, base.WHITE, base.LINE, 18, 1)

    # Left: explicit memory authorities
    p.section(44, 146, "Four memory layers", base.VIOLET)
    p.text(44, 173, "Remember the right thing", 25, base.INK, bold=True)
    p.wrapped(
        44,
        207,
        "Each store has one authority. This prevents stale personalization from becoming project truth.",
        370,
        14,
        base.MUTED,
        gap=4,
    )

    p.mini_card(
        44, 270, 370, 128,
        "Session memory", "Streamlit UI state",
        "Current page, selected section, transient controls and display cache. Lost safely when the session ends.",
        base.SOFT, base.LINE,
    )
    p.mini_card(
        44, 416, 370, 154,
        "Canonical episodic state", "Supabase",
        "Profiles, runs, tasks, evidence, approvals, checkpoints and Blueprint versions. Read before routing; write after every state transition.",
        base.BLUE_SOFT, base.BLUE,
    )
    p.mini_card(
        44, 588, 370, 140,
        "Long-term founder memory", "Mem0",
        "Only confirmed goals, preferences, constraints, corrections and decisions—with provenance. Never the canonical Blueprint.",
        base.GREEN_SOFT, base.GREEN,
    )
    p.mini_card(
        44, 746, 370, 154,
        "Semantic evidence memory", "Pinecone",
        "Accepted evidence and completed sections for retrieval. Every hit is mapped back to owner-scoped Supabase truth before use.",
        base.VIOLET_SOFT, base.VIOLET,
    )
    p.rect(44, 918, 370, 130, base.AMBER_SOFT, base.AMBER, 12, 1)
    p.section(62, 936, "Learning boundary", base.AMBER)
    p.wrapped(
        62,
        962,
        "Blueprint learns by recording observations, accepted evidence and founder feedback, then replanning from durable state. It does not self-train the model or store raw chain-of-thought.",
        334,
        13,
        base.INK,
        gap=4,
    )

    # Center: runtime flow
    p.section(480, 146, "Runtime control flow", base.BLUE)
    p.text(480, 173, "Fast first value. Deep evidence next.", 25, base.INK, bold=True)
    p.text(1420, 178, "SUPERVISOR-OWNED", 11, base.BLUE, bold=True, anchor="right")

    compact_step(
        p, 480, 220, 942, 72, "1", "Founder request + onboarding",
        "Idea, goal, constraints and selected research lanes enter an owner-isolated run.",
    )
    p.line(951, 292, 951, 310, base.MUTED, 2, True)
    compact_step(
        p, 480, 312, 942, 78, "2", "Safety, scope, identity + idempotency boundary",
        "Reject unsafe/out-of-scope requests; restore or create exactly one durable project/run.",
        base.SOFT, base.LINE,
    )
    p.line(951, 390, 951, 408, base.MUTED, 2, True)
    compact_step(
        p, 480, 410, 942, 92, "3", "Immediate Foundation — deterministic fast path",
        "Structure founder-provided inputs locally. No web search or model round-trip blocks the first useful view.",
        base.GREEN_SOFT, base.GREEN,
    )
    connector_label(p, 951, 516, "FOUNDATION VISIBLE", base.GREEN)
    p.line(951, 528, 951, 546, base.MUTED, 2, True)
    compact_step(
        p, 480, 548, 942, 82, "4", "Dynamic Supervisor + dependency-aware scheduler",
        "Load canonical state, eligible memories and budgets; dispatch only justified specialist work.",
        base.BLUE_SOFT, base.BLUE,
    )
    p.line(951, 630, 951, 647, base.MUTED, 2, True)

    # Parallel specialists
    p.rect(480, 650, 942, 148, base.SOFT, base.LINE, 14, 1)
    p.text(500, 666, "5  PARALLEL SPECIALIST FAN-OUT", 11, base.BLUE, bold=True)
    specialist_y = 696
    gap = 14
    specialist_w = (902 - 2 * gap) / 3
    p.mini_card(
        500, specialist_y, specialist_w, 82,
        "Research agent", "Customer",
        "Pains, jobs, personas, interview path and demand signals.",
        base.WHITE, base.GREEN,
    )
    p.mini_card(
        500 + specialist_w + gap, specialist_y, specialist_w, 82,
        "Research agent", "Competitor",
        "Direct, indirect and workaround alternatives; gaps and complaints.",
        base.WHITE, base.VIOLET,
    )
    p.mini_card(
        500 + 2 * (specialist_w + gap), specialist_y, specialist_w, 82,
        "Research agent", "Market",
        "Secondary evidence, dynamics, reachability and market constraints.",
        base.WHITE, base.AMBER,
    )
    p.text(1402, 668, "Each completed section renders immediately", 10, base.GREEN, bold=True, anchor="right")
    p.line(951, 798, 951, 816, base.MUTED, 2, True)

    # Audit, verdict and critic
    p.rect(480, 818, 942, 128, base.WHITE, base.LINE, 14, 1)
    lane_gap = 14
    lane_w = (902 - 2 * lane_gap) / 3
    p.mini_card(
        500, 840, lane_w, 84,
        "Independent agent", "Evidence audit",
        "Coverage, relevance, freshness, contradictions and citation integrity.",
        base.BLUE_SOFT, base.BLUE,
    )
    p.mini_card(
        500 + lane_w + lane_gap, 840, lane_w, 84,
        "Deterministic policy", "Research verdict",
        "Transparent score, threshold, limitations and allowed next routes.",
        base.AMBER_SOFT, base.AMBER,
    )
    p.mini_card(
        500 + 2 * (lane_w + lane_gap), 840, lane_w, 84,
        "Critique agent", "Quality gate",
        "Grounding, completeness, actionability and safety; cannot self-approve.",
        base.VIOLET_SOFT, base.VIOLET,
    )
    p.line(951, 946, 951, 964, base.MUTED, 2, True)

    p.rect(480, 966, 942, 88, base.AMBER_SOFT, base.AMBER, 14, 2)
    p.text(500, 980, "6  HUMAN-IN-THE-LOOP DECISION GATE", 12, base.AMBER, bold=True)
    p.text(500, 1007, "Founder can approve, revise, add information, request a rerun, override with reason, pause or stop.", 15, base.INK, bold=True)
    p.text(500, 1034, "Only an accepted decision unlocks Stage 2 and updates the versioned Blueprint.", 12, base.MUTED)

    # Memory connectors. Labels name the authority without creating line clutter.
    p.polyline([(438, 488), (462, 488), (462, 351), (480, 351)], base.BLUE, 2, True, True)
    connector_label(p, 464, 472, "STATE", base.BLUE)
    p.polyline([(438, 658), (450, 658), (450, 590), (480, 590)], base.GREEN, 2, True, True)
    connector_label(p, 458, 644, "CONFIRMED", base.GREEN)
    p.polyline([(480, 882), (456, 882), (456, 823), (438, 823)], base.VIOLET, 2, True, True)
    connector_label(p, 455, 866, "ACCEPTED", base.VIOLET)

    # Right: latency, recovery, and HITL trigger map
    p.section(1486, 146, "Latency design", base.GREEN)
    p.text(1486, 173, "Where waiting is removed", 24, base.INK, bold=True)
    latency = [
        "Deterministic Foundation: no external research wait.",
        "Customer, competitor and market work run in parallel.",
        "Scheduler skips agents whose dependencies or evidence do not justify them.",
        "Progressive persistence keeps completed sections readable while others run.",
        "Bounded timeouts, retries, tool and cost budgets prevent endless loops.",
        "Durable resume continues from the last checkpoint instead of restarting.",
        "Section-scoped RAG retrieves only the evidence needed for that question.",
    ]
    ly = 216
    for i, item in enumerate(latency, 1):
        ly = p.numbered(1486, ly, i, item, 388) + 8

    p.line(1486, 536, 1876, 536, base.LINE, 1)
    p.section(1486, 556, "Bounded recovery loop", base.RED)
    p.text(1486, 582, "Failure never becomes an infinite spinner", 19, base.INK, bold=True)
    recovery = [
        ("Tool/model failure", base.RED_SOFT, base.RED),
        ("Classify + record", base.SOFT, base.LINE),
        ("Retry / repair once", base.AMBER_SOFT, base.AMBER),
        ("Reload state + replan", base.BLUE_SOFT, base.BLUE),
        ("Partial result / HITL / safe fail", base.GREEN_SOFT, base.GREEN),
    ]
    ry = 620
    for i, (label, fill, stroke) in enumerate(recovery):
        p.rect(1486, ry, 388, 38, fill, stroke, 9, 1)
        p.text(1680, ry + 8, label, 12, base.INK, bold=i in {0, 4}, anchor="center")
        if i < len(recovery) - 1:
            p.line(1680, ry + 38, 1680, ry + 48, base.MUTED, 1, True)
        ry += 49

    p.line(1486, 868, 1876, 868, base.LINE, 1)
    p.section(1486, 888, "Every HITL trigger", base.AMBER)
    triggers = [
        "Required founder context is missing or ambiguous.",
        "Decision-critical evidence is contradictory or insufficient.",
        "A profile correction makes downstream work stale.",
        "A rerun, route override or idea change is proposed.",
        "A stage gate or final Blueprint decision is reached.",
        "Retries, provider budget or time budget are exhausted.",
        "Any external create, modify, send, publish, pay or delete action is requested.",
    ]
    ty = 916
    for item in triggers:
        ty = p.bullet(1486, ty, item, 388, base.AMBER, 11) + 3

    # Footer: observability and the success boundary
    p.rect(22, 1092, 1876, 82, base.INK, base.INK, 16, 1)
    p.text(48, 1108, "OBSERVE", 11, "#A8D7C4", bold=True)
    p.text(48, 1133, "Latency per step · attempts · route reason · tool/model · budget · terminal status", 14, base.WHITE)
    p.text(1000, 1108, "TASK COMPLETION", 11, "#F4D899", bold=True)
    p.text(1000, 1133, "Every run ends visibly: completed, partial, needs input, human review, cancelled or safe failed.", 14, base.WHITE)

    p.save(STEM)


if __name__ == "__main__":
    build()
