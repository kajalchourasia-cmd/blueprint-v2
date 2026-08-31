"""Generate the review-only vertical agent orchestration and memory map.

This script intentionally writes only the standalone review asset. It does not
update README.md, the architecture index, the contact sheet, or submission docs.
"""

from __future__ import annotations

import html
import math

from generate_architecture_diagrams import (
    AMBER,
    AMBER_SOFT,
    BLUE,
    BLUE_SOFT,
    BROWN,
    Figure,
    GREEN,
    GREEN_SOFT,
    INK,
    LINE,
    MUTED,
    RED,
    RED_SOFT,
    SOFT,
    VIOLET,
    VIOLET_SOFT,
    WHITE,
    rgb,
)


WIDTH = 2000
HEIGHT = 3460


class AgentMap(Figure):
    def polyline(
        self,
        points: list[tuple[float, float]],
        color: str = "#6B746F",
        width: int = 4,
        *,
        arrow: bool = True,
        dashed: bool = False,
    ) -> None:
        """Draw an orthogonal connector with an optional arrow head."""
        self.draw.line(points, fill=rgb(color), width=width, joint="curve")
        if arrow and len(points) >= 2:
            (x1, y1), (x2, y2) = points[-2], points[-1]
            angle = math.atan2(y2 - y1, x2 - x1)
            size = 18
            head = [
                (x2, y2),
                (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45)),
                (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45)),
            ]
            self.draw.polygon(head, fill=rgb(color))
        pts = " ".join(f"{x},{y}" for x, y in points)
        dash = ' stroke-dasharray="12 10"' if dashed else ""
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        self.svg.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linejoin="round"{dash}{marker}/>'
        )

    def role_card(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        role: str,
        title: str,
        body: str,
        *,
        fill: str = WHITE,
        stroke: str = LINE,
        role_color: str = MUTED,
        title_size: int = 30,
        body_size: int = 23,
    ) -> None:
        self.rect(x, y, width, height, fill, stroke, 22, 2)
        role_size = 18
        while role_size > 13 and self.draw.textbbox(
            (0, 0), role.upper(), font=self.font(role_size, True)
        )[2] > width - 56:
            role_size -= 1
        self.text(x + 28, y + 18, role.upper(), role_size, role_color, bold=True)
        self.text(x + 28, y + 50, title, title_size, INK, bold=True)
        self.wrapped(x + 28, y + 91, body, width - 56, body_size, MUTED, line_gap=7)

    def lane_title(self, x: float, y: float, width: float, label: str, color: str) -> None:
        self.text(x, y, label.upper(), 21, color, bold=True)
        self.line(x, y + 38, x + width, y + 38, color, 3)


def build() -> None:
    f = AgentMap(
        "Blueprint — Vertical Agent Orchestration & Memory Map",
        "Who decides, who researches, who critiques, when memory is read or written, and where a human takes control",
        WIDTH,
        HEIGHT,
    )

    # Legend
    legend_y = 202
    legend = [
        ("SUPERVISOR", BLUE_SOFT, BLUE),
        ("SPECIALIST AGENT", VIOLET_SOFT, VIOLET),
        ("AUDITOR / CRITIC", AMBER_SOFT, AMBER),
        ("DETERMINISTIC", GREEN_SOFT, GREEN),
        ("HUMAN GATE", AMBER_SOFT, BROWN),
        ("MEMORY / STATE", SOFT, MUTED),
    ]
    lx = 70
    for label, fill, color in legend:
        f.pill(lx, legend_y, label, fill, color)
        lx += f.draw.textbbox((0, 0), label, font=f.font(21, True))[2] + 58

    left_x, left_w = 70, 340
    main_x, main_w = 485, 1030
    right_x, right_w = 1590, 340
    f.lane_title(left_x, 282, left_w, "Memory and canonical state", GREEN)
    f.lane_title(main_x, 282, main_w, "Authoritative control path", BLUE)
    f.lane_title(right_x, 282, right_w, "Tools, recovery and telemetry", VIOLET)

    # Connectors behind the cards: the central control spine. Every line starts
    # at a card boundary, so no arrow is visible underneath text.
    gaps = [
        (528, 548), (694, 714), (864, 884), (1034, 1054), (1230, 1250),
        (1426, 1446), (1866, 1886), (2036, 2056), (2188, 2208),
        (2368, 2388), (2538, 2558), (2748, 2768), (3018, 3038),
    ]
    for y1, y2 in gaps:
        f.arrow_between(1000, y1, 1000, y2)

    # Main path cards.
    f.role_card(main_x, 372, main_w, 156, "Founder input", "Idea + requested outcome",
                "The founder supplies the unfinished idea, constraints, geography, goal and the research lanes to run.",
                fill=GREEN_SOFT, stroke=GREEN, role_color=GREEN)
    f.role_card(main_x, 548, main_w, 146, "Experience layer", "Streamlit onboarding",
                "Creates an anonymous owner session, validates required fields and shows progress without exposing internal tools.")
    f.role_card(main_x, 714, main_w, 150, "Deterministic API boundary", "BP-API-01 · Start or resume a run",
                "Applies scope and safety checks, restores owner context and persists a durable project/run before work begins.",
                fill=GREEN_SOFT, stroke=GREEN, role_color=GREEN)
    f.role_card(main_x, 884, main_w, 150, "Deterministic builder", "Foundation Builder · immediate",
                "Turns confirmed onboarding answers into problem framing, goals, personas-to-test, constraints and initial assumptions. No web research is needed.",
                fill=GREEN_SOFT, stroke=GREEN, role_color=GREEN)
    f.role_card(main_x, 1054, main_w, 176, "Supervisor / orchestrator", "BP-00 · Adaptive Supervisor",
                "Reloads canonical state, applies budgets and policy, chooses the next eligible route and re-evaluates after every observation or founder decision.",
                fill=BLUE_SOFT, stroke=BLUE, role_color=BLUE)
    f.role_card(main_x, 1250, main_w, 176, "Deterministic planning + scheduling", "BP-PLAN-01 + BP-SCHED-01",
                "Builds the dependency graph, releases only eligible tasks and dispatches independent research lanes in parallel—not a fixed A → B → C chain.",
                fill=GREEN_SOFT, stroke=GREEN, role_color=GREEN)

    # Parallel specialist fan-out.
    f.rect(main_x, 1446, main_w, 420, WHITE, VIOLET, 26, 2)
    f.text(main_x + 28, 1464, "PARALLEL SPECIALIST AGENTS · READ-ONLY RESEARCH", 19, VIOLET, bold=True)
    f.wrapped(
        main_x + 28,
        1494,
        "Each receives the same foundation contract and returns structured findings, evidence IDs, assumptions and limitations.",
        main_w - 56,
        22,
        MUTED,
        line_gap=5,
    )
    sub_y, sub_w, sub_gap = 1547, 306, 28
    subs = [
        ("Customer / User", "Pain signals, personas, discovery channels, interview objectives and questions."),
        ("Competitor", "Direct + indirect alternatives, positioning, pricing boundary, complaints and gaps."),
        ("Market", "Secondary evidence, market direction, adoption constraints and bounded opportunity."),
    ]
    for i, (title, body) in enumerate(subs):
        sx = main_x + 28 + i * (sub_w + sub_gap)
        f.role_card(sx, sub_y, sub_w, 262, "Specialist agent", title, body,
                    fill=VIOLET_SOFT, stroke=VIOLET, role_color=VIOLET, title_size=25, body_size=21)
        f.polyline([(1000, 1426), (1000, 1518), (sx + sub_w / 2, 1518), (sx + sub_w / 2, sub_y)], VIOLET, 3)
        f.polyline([(sx + sub_w / 2, sub_y + 262), (sx + sub_w / 2, 1836), (1000, 1836), (1000, 1886)], VIOLET, 3)

    f.role_card(main_x, 1886, main_w, 150, "Independent auditor agent", "BP-AUDIT-01 · Evidence Auditor",
                "Checks source relevance, recency, claim support, contradictions and missing evidence. Rejected claims cannot influence the verdict.",
                fill=AMBER_SOFT, stroke=AMBER, role_color=AMBER)
    f.role_card(main_x, 2056, main_w, 132, "Deterministic decision engine", "BP-VERDICT-01 · Viability Engine",
                "Computes the transparent 40 / 30 / 30 score, coverage and confidence. It never invents demand, revenue or willingness-to-pay.",
                fill=GREEN_SOFT, stroke=GREEN, role_color=GREEN, body_size=22)
    f.role_card(main_x, 2208, main_w, 160, "Critique agent", "BP-QA-01 · Quality Critic",
                "Challenges completeness, consistency, unsupported certainty and usefulness. It may request one bounded revision through the Supervisor.",
                fill=AMBER_SOFT, stroke=AMBER, role_color=AMBER)
    f.role_card(main_x, 2388, main_w, 150, "Synthesis agent", "BP-SYNTH-01 · Blueprint Synthesizer",
                "Combines only audited findings into a versioned Research Blueprint, explicit actionables, open risks and traceable sources.",
                fill=VIOLET_SOFT, stroke=VIOLET, role_color=VIOLET)
    f.role_card(main_x, 2558, main_w, 190, "Human decision layer · HITL", "BP-HITL-01 · Founder Checkpoint",
                "The founder reviews the verdict and selected idea improvements, then chooses proceed, revise, rerun, override with reason, or pause. Stage 2 cannot unlock without this decision.",
                fill=AMBER_SOFT, stroke=BROWN, role_color=BROWN)
    f.role_card(main_x, 2768, main_w, 250, "Advisory specialist agents", "Stage 2 Prove & Design → Stage 3 Action Blueprint",
                "Approved context routes into assumptions and risk, operating model, validation plan and deterministic financial scenarios. Stage 3 supplies milestone-level MVP, first-customer and distribution guidance—never executes actions for the founder.",
                fill=VIOLET_SOFT, stroke=VIOLET, role_color=VIOLET)
    f.role_card(main_x, 3038, main_w, 166, "Founder-visible outcome", "Versioned Blueprint + financial scenarios + next moves",
                "Every section stays inspectable while later work runs. The founder can compare versions, inspect evidence and request a targeted rerun through HITL.",
                fill=GREEN_SOFT, stroke=GREEN, role_color=GREEN)

    # State lane.
    f.role_card(left_x, 372, left_w, 174, "Short-term UI memory", "Streamlit session",
                "Active page, selected section and transient display state only. Never treated as business truth.",
                fill=SOFT, stroke=LINE, role_color=MUTED, title_size=25, body_size=20)
    f.role_card(left_x, 588, left_w, 386, "Canonical episodic state", "Supabase + RLS",
                "System of record for owner-scoped projects, runs, task graph, observations, evidence, errors, checkpoints, decisions and Blueprint versions. Read before every routing decision; written after every state transition.",
                fill=GREEN_SOFT, stroke=GREEN, role_color=GREEN, title_size=26, body_size=21)
    f.role_card(left_x, 1048, left_w, 278, "Long-term semantic preference memory", "Mem0",
                "Reads confirmed founder goals, preferences and prior corrections during planning. Writes only after a founder checkpoint—never stores research claims as truth.",
                fill=VIOLET_SOFT, stroke=VIOLET, role_color=VIOLET, title_size=26, body_size=21)
    f.role_card(left_x, 1610, left_w, 300, "Accepted-evidence projection", "Pinecone",
                "Receives only evidence accepted by BP-AUDIT-01 through BP-PINE-01. Used for semantic retrieval; every hit is revalidated against Supabase before generation.",
                fill=BLUE_SOFT, stroke=BLUE, role_color=BLUE, title_size=26, body_size=21)

    # Tools, recovery, telemetry and RAG lane.
    f.role_card(right_x, 1370, right_w, 185, "Read-only search tool", "You.com",
                "Discovers current sources for the three research specialists. Search excerpts are not accepted evidence by themselves.",
                fill=SOFT, stroke=LINE, role_color=MUTED, title_size=26, body_size=20)
    f.role_card(right_x, 1575, right_w, 220, "Model service", "Nebius",
                "Structured extraction and synthesis for specialists, critic and Research Copilot. Prompts demand schemas, evidence IDs and bounded uncertainty.",
                fill=SOFT, stroke=LINE, role_color=MUTED, title_size=26, body_size=20)
    f.role_card(right_x, 2022, right_w, 292, "Deterministic recovery controller", "BP-RESILIENCE-01",
                "On tool or model failure: retry within budget, repair schema, reload durable state, choose an alternate route, return partial results for review, or fail safely. It never silently fabricates a result.",
                fill=RED_SOFT, stroke=RED, role_color=RED, title_size=26, body_size=20)
    f.role_card(right_x, 2350, right_w, 280, "Observability component", "BP-90 · Audit + Error Writer",
                "Records route reason, tool choice, attempt, latency, budget, confidence, terminal state and correlation IDs for replay and evaluation.",
                fill=SOFT, stroke=LINE, role_color=MUTED, title_size=26, body_size=20)
    f.role_card(right_x, 2768, right_w, 350, "Grounded RAG agent", "BP-CHAT-01 · Research Copilot",
                "Answers only about the active Blueprint section and accepted evidence. It cites sources, states limitations and coaches next actions. Rerun or write requests are proposals sent to HITL—not executed directly.",
                fill=BLUE_SOFT, stroke=BLUE, role_color=BLUE, title_size=25, body_size=20)

    # State/tool interaction arrows and concise labels.
    f.polyline([(410, 459), (454, 459), (454, 621), (485, 621)], MUTED, 3)
    f.polyline([(410, 745), (458, 745), (458, 789), (485, 789)], GREEN, 3)
    f.polyline([(410, 826), (464, 826), (464, 1141), (485, 1141)], GREEN, 3)
    f.polyline([(485, 1198), (446, 1198), (446, 915), (410, 915)], GREEN, 3)
    f.polyline([(410, 1168), (452, 1168), (452, 1134), (485, 1134)], VIOLET, 3)
    f.polyline([(485, 2676), (440, 2676), (440, 1275), (410, 1275)], VIOLET, 3)

    f.polyline([(1515, 1652), (1548, 1652), (1548, 1460), (1590, 1460)], MUTED, 3)
    f.polyline([(1515, 1705), (1560, 1705), (1560, 1685), (1590, 1685)], MUTED, 3)
    # Accepted evidence exits the Auditor at its left boundary and travels only
    # through the gutter before entering Pinecone.
    f.polyline([(485, 1961), (424, 1961), (424, 1765), (410, 1765)], BLUE, 3)

    # Critic revision and recovery loops.
    f.polyline([(1515, 2288), (1552, 2288), (1552, 2158), (1590, 2158)], RED, 3)
    f.polyline([(1590, 2248), (1570, 2248), (1570, 1141), (1515, 1141)], RED, 3, dashed=True)
    f.polyline([(485, 2648), (432, 2648), (432, 1141), (485, 1141)], BROWN, 3, dashed=True)
    f.polyline([(1515, 2480), (1552, 2480), (1552, 2480), (1590, 2480)], MUTED, 3)

    # Research Copilot grounding paths run through the outside gutters and the
    # clear band beneath the outcome card. They never cross narrative text.
    f.polyline([(1515, 3120), (1550, 3120), (1550, 2943), (1590, 2943)], BLUE, 3)
    f.polyline([(410, 1800), (418, 1800), (418, 3230), (1560, 3230), (1560, 2985), (1590, 2985)], BLUE, 3, dashed=True)
    f.polyline([(410, 948), (426, 948), (426, 3242), (1572, 3242), (1572, 3048), (1590, 3048)], GREEN, 3, dashed=True)
    f.polyline([(1760, 2768), (1950, 2768), (1950, 1685), (1930, 1685)], MUTED, 3, dashed=True)

    # Learning boundary and footer.
    f.rect(70, 3260, 1860, 120, SOFT, LINE, 20, 2)
    f.text(96, 3280, "LEARNING BOUNDARY", 19, GREEN, bold=True)
    f.text(96, 3316, "The system improves by storing accepted observations, founder corrections and route outcomes, then reloading them on the next decision.", 22, INK)
    f.text(96, 3348, "It does not self-train model weights, store raw chain-of-thought, or let Mem0/Pinecone override Supabase as the source of truth.", 22, MUTED)
    f.footer("Solid arrows = normal control/data path · Dashed arrows = recovery, revision or retrieval path · External writes remain human-approved")
    f.save("12-vertical-agent-orchestration-map")


if __name__ == "__main__":
    build()
