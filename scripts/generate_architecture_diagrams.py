"""Generate Blueprint's submission-ready architecture diagrams.

The figures are intentionally sparse and readable at Google Docs width:
white backgrounds, large type, thin borders, and colour only where it carries
meaning. Every figure is exported as both PNG and editable SVG.
"""

from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures" / "architecture"
W, H = 1920, 1080

WHITE = "#FFFFFF"
INK = "#17201C"
MUTED = "#5F6B65"
LINE = "#C9D0CC"
SOFT = "#F5F7F5"
GREEN = "#176447"
GREEN_SOFT = "#E8F2ED"
BLUE = "#2D5F8B"
BLUE_SOFT = "#EAF1F8"
AMBER = "#9A6A14"
AMBER_SOFT = "#FBF3DD"
RED = "#A94840"
RED_SOFT = "#FBECEB"
VIOLET = "#6D5AA6"
VIOLET_SOFT = "#F1EDF8"
BROWN = "#7C563C"

FONT_REG = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/seguisb.ttf")


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


class Figure:
    def __init__(self, title: str, subtitle: str) -> None:
        self.image = Image.new("RGB", (W, H), rgb(WHITE))
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
            '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 z" fill="#6B746F"/></marker></defs>',
        ]
        self.text(70, 54, title, 48, INK, bold=True)
        self.text(70, 116, subtitle, 25, MUTED)
        self.line(70, 165, W - 70, 165, LINE, 2)

    def font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)

    def text(self, x: float, y: float, value: str, size: int, color: str = INK,
             bold: bool = False, anchor: str = "left") -> None:
        font = self.font(size, bold)
        bbox = self.draw.textbbox((0, 0), value, font=font)
        width = bbox[2] - bbox[0]
        px = x if anchor == "left" else x - width / 2 if anchor == "center" else x - width
        self.draw.text((px, y), value, font=font, fill=rgb(color))
        svg_anchor = {"left": "start", "center": "middle", "right": "end"}[anchor]
        weight = 600 if bold else 400
        self.svg.append(
            f'<text x="{x}" y="{y + size}" text-anchor="{svg_anchor}" '
            f'font-family="Segoe UI, Arial" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}">{html.escape(value)}</text>'
        )

    def wrapped(self, x: float, y: float, value: str, width: float, size: int = 28,
                color: str = MUTED, bold: bool = False, line_gap: int = 10) -> float:
        lines = self.wrap_lines(value, width, size, bold)
        for i, line in enumerate(lines):
            self.text(x, y + i * (size + line_gap), line, size, color, bold)
        return y + len(lines) * (size + line_gap)

    def wrap_lines(self, value: str, width: float, size: int, bold: bool = False) -> list[str]:
        words = value.split()
        lines: list[str] = []
        current = ""
        font = self.font(size, bold)
        for word in words:
            trial = f"{current} {word}".strip()
            if self.draw.textbbox((0, 0), trial, font=font)[2] <= width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def rect(self, x: float, y: float, width: float, height: float, fill: str = WHITE,
             stroke: str = LINE, radius: int = 22, sw: int = 2) -> None:
        box = (round(x), round(y), round(x + width), round(y + height))
        self.draw.rounded_rectangle(box, radius, fill=rgb(fill), outline=rgb(stroke), width=sw)
        self.svg.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def card(self, x: float, y: float, width: float, height: float, title: str,
             body: str = "", fill: str = WHITE, stroke: str = LINE,
             number: str | None = None, title_color: str = INK) -> None:
        self.rect(x, y, width, height, fill, stroke)
        tx = x + 28
        if number:
            self.circle(x + 38, y + 38, 22, WHITE, stroke)
            self.text(x + 38, y + 22, number, 24, stroke, bold=True, anchor="center")
            tx = x + 76
        title_size = 29
        available = x + width - 24 - tx
        while title_size > 22 and self.draw.textbbox((0, 0), title, font=self.font(title_size, True))[2] > available:
            title_size -= 1
        self.text(tx, y + 23, title, title_size, title_color, bold=True)
        if body:
            body_size = 25
            line_gap = 8
            available_height = height - 88
            while body_size > 20:
                lines = self.wrap_lines(body, width - 56, body_size)
                if len(lines) * (body_size + line_gap) <= available_height:
                    break
                body_size -= 1
                line_gap = max(5, line_gap - 1)
            self.wrapped(x + 28, y + 72, body, width - 56, body_size, MUTED, line_gap=line_gap)

    def pill(self, x: float, y: float, text: str, fill: str, color: str) -> None:
        font = self.font(21, True)
        width = self.draw.textbbox((0, 0), text, font=font)[2] + 34
        self.rect(x, y, width, 42, fill, fill, 21, 1)
        self.text(x + 17, y + 7, text, 21, color, bold=True)

    def circle(self, cx: float, cy: float, radius: float, fill: str, stroke: str = LINE) -> None:
        self.draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=rgb(fill), outline=rgb(stroke), width=2)
        self.svg.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = LINE,
             width: int = 3, arrow: bool = False, dashed: bool = False) -> None:
        self.draw.line((x1, y1, x2, y2), fill=rgb(color), width=width)
        if arrow:
            angle = math.atan2(y2 - y1, x2 - x1)
            size = 18
            points = [
                (x2, y2),
                (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45)),
                (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45)),
            ]
            self.draw.polygon(points, fill=rgb(color))
        dash = ' stroke-dasharray="10 8"' if dashed else ""
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        self.svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{width}"{dash}{marker}/>'
        )

    def arrow_between(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.line(x1, y1, x2, y2, "#6B746F", 4, arrow=True)

    def footer(self, label: str) -> None:
        self.line(70, H - 78, W - 70, H - 78, LINE, 2)
        self.text(70, H - 56, label, 22, MUTED)

    def save(self, stem: str) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        self.image.save(OUT / f"{stem}.png", quality=95)
        self.svg.append("</svg>")
        (OUT / f"{stem}.svg").write_text("\n".join(self.svg), encoding="utf-8")


def readme_architecture() -> None:
    f = Figure("Blueprint — Architecture at a Glance", "A founder-controlled loop from uncertain idea to evidence-backed next move")
    x = [70, 365, 660, 955, 1250, 1545]
    cards = [
        ("Streamlit", "Idea, onboarding, progress and approvals", GREEN_SOFT, GREEN),
        ("n8n Supervisor", "Loads state and chooses the next eligible route", BLUE_SOFT, BLUE),
        ("Planner", "Builds the task graph and dispatches ready work", VIOLET_SOFT, VIOLET),
        ("Researchers", "Customer, competitor and market specialists", SOFT, LINE),
        ("Audit + verdict", "Checks evidence, scores viability and exposes uncertainty", AMBER_SOFT, AMBER),
        ("Founder Gate", "Proceed, revise, override with reason, or pause", GREEN_SOFT, GREEN),
    ]
    for i, (title, body, fill, stroke) in enumerate(cards):
        f.card(x[i], 265, 245, 235, title, body, fill, stroke, str(i + 1))
        if i < len(cards) - 1:
            f.arrow_between(x[i] + 245, 382, x[i + 1] - 16, 382)
    f.card(220, 650, 430, 175, "Supabase", "Canonical owner-scoped projects, runs, tasks, evidence, checkpoints and blueprint versions.", WHITE, GREEN)
    f.card(745, 650, 430, 175, "Evidence + models", "You.com discovery and Nebius structured extraction, synthesis, audit and chat.", WHITE, BLUE)
    f.card(1270, 650, 430, 175, "Bounded memory", "Pinecone accepted-evidence projection and Mem0 confirmed founder-journey projection.", WHITE, VIOLET)
    f.arrow_between(435, 650, 435, 530)
    f.arrow_between(960, 650, 960, 530)
    f.arrow_between(1485, 650, 1485, 530)
    f.footer("Reads can run autonomously. Stage changes, reruns and external writes require founder approval.")
    f.save("00-readme-architecture")


def project_canvas() -> None:
    f = Figure("Blueprint — Whole Project Canvas", "Problem, agentic system, trust model and measurable outcome in one view")
    f.card(70, 215, 400, 260, "The founder problem", "Research is scattered across tabs and chats. Evidence, assumptions, constraints and next actions are disconnected.", RED_SOFT, RED)
    f.card(500, 215, 400, 260, "The product promise", "Turn an unfinished idea into a progressive, sourced Blueprint and the next provable move.", GREEN_SOFT, GREEN)
    f.card(930, 215, 400, 260, "The agentic core", "Supervisor re-evaluates durable state, dispatches specialists, audits evidence and routes around failure.", BLUE_SOFT, BLUE)
    f.card(1360, 215, 490, 260, "The founder stays in control", "The system recommends. The founder approves reruns, stage progression and any consequential change.", AMBER_SOFT, AMBER)
    f.text(70, 535, "HOW IT WORKS", 23, MUTED, bold=True)
    steps = [
        ("1", "Capture context", "Idea, user, goal, geography, money, time and prior evidence."),
        ("2", "Research in parallel", "Customer/user, competitor and market agents gather bounded evidence."),
        ("3", "Audit before deciding", "A separate auditor rejects weak claims and preserves contradictions."),
        ("4", "Route by evidence", "Verdict and founder choice determine proceed, revise, pause or re-run."),
        ("5", "Build progressively", "Approved findings update a versioned Blueprint and action plan."),
    ]
    for i, (number, title, body) in enumerate(steps):
        xx = 70 + i * 362
        f.card(xx, 585, 320, 225, title, body, WHITE, LINE, number)
        if i < 4:
            f.arrow_between(xx + 320, 700, xx + 348, 700)
    f.pill(70, 865, "27 n8n workflows", BLUE_SOFT, BLUE)
    f.pill(315, 865, "22 Supabase migrations", GREEN_SOFT, GREEN)
    f.pill(620, 865, "35 Python tests", VIOLET_SOFT, VIOLET)
    f.pill(875, 865, "85 agentic eval cases", AMBER_SOFT, AMBER)
    f.pill(1190, 865, "Human gates", GREEN_SOFT, GREEN)
    f.pill(1400, 865, "Fail-closed evidence", RED_SOFT, RED)
    f.footer("Success is end-to-end task completion: a founder reaches a defensible decision and knows what to do next.")
    f.save("01-blueprint-project-canvas")


def end_to_end_architecture() -> None:
    f = Figure("End-to-End System Architecture", "Control plane, evidence plane and durable state are intentionally separated")
    columns = [90, 405, 720, 1035, 1350, 1665]
    top = [
        ("Founder UI", "Streamlit landing, onboarding, dashboard and approvals", GREEN_SOFT, GREEN),
        ("API boundary", "JWT owner scope, contract validation and idempotency", WHITE, LINE),
        ("Supervisor", "Loads snapshot and chooses the next eligible route", BLUE_SOFT, BLUE),
        ("Planner / Scheduler", "Creates dependencies and atomically claims ready tasks", VIOLET_SOFT, VIOLET),
        ("Specialists", "Foundation plus customer, competitor and market research", WHITE, LINE),
        ("Decision layer", "Evidence Audit → Verdict → Quality Critic → HITL", AMBER_SOFT, AMBER),
    ]
    for i, item in enumerate(top):
        f.card(columns[i], 230, 255, 235, *item)
        if i < 5:
            f.arrow_between(columns[i] + 255, 348, columns[i + 1] - 15, 348)
    f.card(140, 620, 470, 190, "Supabase — system of record", "Owner-isolated projects, runs, tasks, checkpoints, evidence, decisions, errors and immutable Blueprint versions.", WHITE, GREEN)
    f.card(725, 620, 470, 190, "Research and model services", "You.com supplies bounded discovery. Nebius performs structured extraction, synthesis, critique and grounded chat.", WHITE, BLUE)
    f.card(1310, 620, 470, 190, "Rebuildable sidecars", "Pinecone stores accepted-evidence vectors. Mem0 stores confirmed founder preferences, goals and decisions.", WHITE, VIOLET)
    f.arrow_between(375, 620, 375, 500)
    f.arrow_between(960, 620, 960, 500)
    f.arrow_between(1545, 620, 1545, 500)
    f.footer("The Supervisor never treats Pinecone or Mem0 as project truth; both are revalidated against Supabase.")
    f.save("02-end-to-end-system-architecture")


def founder_journey() -> None:
    f = Figure("Founder User Flow", "The dashboard remains useful while research continues and gates prevent accidental progression")
    steps = [
        ("1", "Describe the idea", "Choose customer, competitor and market research."),
        ("2", "Confirm context", "Goal, audience, geography, budget, time and prior work."),
        ("3", "See Foundation", "Immediate founder-input summary; research starts in parallel."),
        ("4", "Inspect Stage 1", "Read completed sections while siblings are still running."),
        ("5", "Review verdict", "See score, evidence strength, risks and what would change it."),
        ("6", "Choose the route", "Proceed, revise, override with reason, rerun or pause."),
    ]
    for i, item in enumerate(steps):
        xx = 65 + i * 308
        fill = GREEN_SOFT if i in (0, 5) else WHITE
        stroke = GREEN if i in (0, 5) else LINE
        f.card(xx, 245, 270, 240, item[1], item[2], fill, stroke, item[0])
        if i < 5:
            f.arrow_between(xx + 270, 365, xx + 294, 365)
    f.card(170, 640, 465, 175, "If evidence is strong enough", "Gate 1 unlocks Prove & Design: assumptions, operating model, validation and financial readiness.", GREEN_SOFT, GREEN)
    f.card(725, 640, 465, 175, "If evidence is weak or contradictory", "Blueprint recommends a narrower test, asks for input, preserves partial results, or pauses safely.", AMBER_SOFT, AMBER)
    f.card(1280, 640, 465, 175, "At every point", "Full Blueprint, financial boundary, sources, background status and section-scoped Ask Blueprint remain available.", BLUE_SOFT, BLUE)
    f.footer("The founder—not the model—owns the consequential decision at each stage gate.")
    f.save("03-founder-user-journey")


def orchestration_flow() -> None:
    f = Figure("Adaptive Orchestration and Closed-Loop Routing", "The next step is selected from durable state after every observation")
    f.card(720, 205, 480, 140, "Adaptive Supervisor", "Reload snapshot → validate budgets → choose one allowed route", BLUE_SOFT, BLUE)
    f.arrow_between(960, 345, 960, 405)
    f.card(720, 405, 480, 140, "Dynamic Planner + Scheduler", "Build dependencies and atomically claim only eligible tasks", VIOLET_SOFT, VIOLET)
    branches = [
        (95, 690, "Ready work", "Dispatch the allowlisted specialist or deterministic step.", GREEN_SOFT, GREEN),
        (525, 690, "Missing input", "Create a checkpoint and ask one precise founder question.", AMBER_SOFT, AMBER),
        (955, 690, "Tool observation", "Retry, repair, reload/replan, partial, review or safe fail.", RED_SOFT, RED),
        (1385, 690, "Stage complete", "Audit, score, synthesize and wait at the founder gate.", BLUE_SOFT, BLUE),
    ]
    for xx, yy, title, body, fill, stroke in branches:
        f.card(xx, yy, 350, 185, title, body, fill, stroke)
        f.line(960, 545, xx + 175, yy, "#78817C", 3, arrow=True)
    f.line(270, 690, 270, 610, GREEN, 3)
    f.line(270, 610, 690, 610, GREEN, 3)
    f.line(690, 610, 690, 275, GREEN, 3, arrow=True)
    f.text(345, 570, "observation returns to supervisor", 22, GREEN, bold=True)
    f.footer("No unlimited loops: task attempts, transitions, tool calls and cost/time budgets are bounded.")
    f.save("04-adaptive-orchestration-routing")


def stage1_flow() -> None:
    f = Figure("Stage 1 Parallel Research and Evidence Convergence", "Independent specialists can finish, fail or request input without erasing sibling work")
    f.card(70, 235, 300, 175, "Foundation", "Deterministic founder-input framing; no web or model latency.", GREEN_SOFT, GREEN)
    f.arrow_between(370, 323, 455, 323)
    f.card(455, 220, 340, 205, "Customer / User Agent", "Personas, jobs, public signals, research objectives and primary-research plan.", WHITE, BLUE)
    f.card(455, 455, 340, 205, "Competitor Agent", "Direct and indirect alternatives, offers, strengths, complaints, gaps and geography.", WHITE, VIOLET)
    f.card(455, 690, 340, 205, "Market Agent", "Secondary evidence, category direction, beachhead, forces, constraints and fit.", WHITE, BROWN)
    for yy in (322, 557, 792):
        f.line(370, 323, 430, yy, "#78817C", 3, arrow=True)
    f.card(935, 330, 350, 210, "Evidence Auditor", "Checks citation allowlists, relevance, freshness, conflicts, coverage and missing streams.", AMBER_SOFT, AMBER)
    f.card(935, 635, 350, 190, "Viability Engine", "Deterministic 40/30/30 score: demand, differentiation and market access.", WHITE, LINE)
    for yy in (322, 557, 792):
        f.line(795, yy, 915, 435, "#78817C", 3, arrow=True)
    f.arrow_between(1110, 540, 1110, 635)
    f.card(1435, 410, 390, 235, "Research Blueprint + Gate 1", "Sourced findings, limitations, next actions and founder decision: proceed, revise, rerun, override or pause.", GREEN_SOFT, GREEN)
    f.arrow_between(1285, 730, 1435, 528)
    f.footer("A directory or search engine is never treated as a competitor; a claim without accepted evidence cannot increase the score.")
    f.save("05-stage1-parallel-research")


def handoff_contracts() -> None:
    f = Figure("Agent Roles, Typed Handoffs and Shared State", "Agents exchange validated artifacts and observations—not hidden reasoning")
    f.card(70, 235, 360, 190, "Supervisor", "Reads the durable snapshot; emits one typed route and route reason.", BLUE_SOFT, BLUE)
    f.card(520, 235, 360, 190, "Research specialist", "Returns structured findings, evidence IDs, assumptions, conflicts and next actions.", WHITE, LINE)
    f.card(970, 235, 360, 190, "Evidence auditor", "Returns accepted, limited or rejected claims plus coverage and blockers.", AMBER_SOFT, AMBER)
    f.card(1420, 235, 360, 190, "Verdict / critic", "Returns score components, decision, revision needs and checkpoint payload.", GREEN_SOFT, GREEN)
    for i in range(3):
        f.arrow_between(430 + 450 * i, 330, 500 + 450 * i, 330)
    f.card(245, 610, 1430, 210, "Supabase shared-state contract", "project_id • run_id • owner_id • state_version • module_key • dependencies • status • attempt • evidence IDs • observation verdict • route reason • checkpoint • immutable output version", SOFT, LINE)
    for xx in (250, 700, 1150, 1600):
        f.arrow_between(xx, 425, xx, 610)
    f.pill(330, 870, "No raw chain of thought", RED_SOFT, RED)
    f.pill(760, 870, "Schema-validated handoffs", BLUE_SOFT, BLUE)
    f.pill(1210, 870, "Optimistic state versioning", GREEN_SOFT, GREEN)
    f.footer("Every handoff can be reproduced from durable inputs, selected tools, accepted evidence and recorded decisions.")
    f.save("06-agent-handoffs-shared-state")


def rag_flow() -> None:
    f = Figure("Ask Blueprint — Grounded RAG and Action Coaching", "The assistant explains the selected section; it cannot silently change or execute the plan")
    steps = [
        ("1", "Question router", "Classify project question, general explanation, actionable coaching, rerun intent or refusal.", WHITE, LINE),
        ("2", "Owner-scoped retrieval", "Load selected section, verdict, actions and accepted evidence from Supabase.", GREEN_SOFT, GREEN),
        ("3", "Semantic assist", "Optionally retrieve related accepted-evidence vectors from Pinecone.", VIOLET_SOFT, VIOLET),
        ("4", "Canonical revalidation", "Discard any vector hit that no longer maps to accepted Supabase evidence.", AMBER_SOFT, AMBER),
        ("5", "Bounded answer", "Answer first, show citations and limitations, then recommend the smallest next move.", BLUE_SOFT, BLUE),
    ]
    for i, item in enumerate(steps):
        xx = 55 + i * 375
        f.card(xx, 245, 335, 245, item[1], item[2], item[3], item[4], item[0])
        if i < 4:
            f.arrow_between(xx + 335, 368, xx + 360, 368)
    f.card(180, 650, 470, 180, "Allowed", "Explain, compare, trace sources, convert an existing actionable into founder-run steps, or propose a rerun.", GREEN_SOFT, GREEN)
    f.card(725, 650, 470, 180, "Needs approval", "A proposed research rerun shows dependency impact before the founder confirms it.", AMBER_SOFT, AMBER)
    f.card(1270, 650, 470, 180, "Denied", "Contact, send, publish, buy, book, pay, delete, expose secrets or invent unsupported facts.", RED_SOFT, RED)
    f.footer("Conversation context is section-scoped; long chats are summarized without replacing accepted project evidence.")
    f.save("07-evidence-grounding-rag")


def memory_model() -> None:
    f = Figure("State and Memory Model", "Different stores serve different lifetimes and authority levels")
    f.card(80, 230, 400, 255, "Session memory", "Streamlit navigation, active section and temporary chat state. Lifetime: browser session. Authority: cache only.", SOFT, LINE)
    f.card(510, 230, 400, 255, "Episodic workflow memory", "Supabase stores exact projects, runs, tasks, decisions, failures and Blueprint versions. Authority: canonical.", GREEN_SOFT, GREEN)
    f.card(940, 230, 400, 255, "Semantic evidence memory", "Pinecone stores vectors for accepted evidence only. Lifetime: rebuildable. Authority: projection.", VIOLET_SOFT, VIOLET)
    f.card(1370, 230, 470, 255, "Founder journey memory", "Mem0 stores confirmed goals, preferences, corrections and decisions. Authority: personalization only.", BLUE_SOFT, BLUE)
    f.text(80, 580, "WHAT BLUEPRINT REMEMBERS", 23, MUTED, bold=True)
    f.card(80, 625, 820, 205, "Persisted", "Founder-confirmed context • accepted sources • route reasons • tool/model selection • errors • checkpoints • approvals • outcomes • immutable versions", WHITE, GREEN)
    f.card(1020, 625, 820, 205, "Never persisted", "Raw chain of thought • provider secrets • unconfirmed personalization • rejected evidence as truth • cross-owner project context", WHITE, RED)
    f.arrow_between(710, 485, 710, 610)
    f.arrow_between(1140, 485, 1140, 610)
    f.footer("If Pinecone or Mem0 fails, Blueprint degrades retrieval or personalization but does not lose project truth.")
    f.save("08-state-and-memory-model")


def failure_flow() -> None:
    f = Figure("Failure Handling and Human-in-the-Loop", "Expected tool observations are routed deliberately; uncaught crashes converge on the global audit boundary")
    f.card(705, 205, 510, 145, "Tool or model observation", "Timeout • rate limit • empty result • schema • grounding • conflict • policy • budget", RED_SOFT, RED)
    f.arrow_between(960, 350, 960, 420)
    f.card(705, 420, 510, 145, "Shared resilience controller", "Classify → check attempts/budget → preserve siblings → choose one terminal-safe route", AMBER_SOFT, AMBER)
    routes = [
        (60, 700, "Retry / repair", "Bounded backoff or one schema/grounding repair.", BLUE_SOFT, BLUE),
        (430, 700, "Reload / replan", "Resolve stale state and recalculate eligible tasks.", VIOLET_SOFT, VIOLET),
        (800, 700, "Partial complete", "Keep useful siblings visible; label missing evidence.", WHITE, LINE),
        (1170, 700, "Human review", "Ask for input, resolve contradiction or approve override.", GREEN_SOFT, GREEN),
        (1540, 700, "Safe fail / deny", "Stop on auth, policy, exhausted budget or unsafe scope.", RED_SOFT, RED),
    ]
    for xx, yy, title, body, fill, stroke in routes:
        f.card(xx, yy, 320, 180, title, body, fill, stroke)
        f.line(960, 565, xx + 160, yy, "#78817C", 3, arrow=True)
    f.footer("No partial verdict is exposed as success. Every route records the reason, attempt, latency and terminal status.")
    f.save("09-failure-hitl-recovery")


def evaluation_flow() -> None:
    f = Figure("Evaluation, Observability and Release Gates", "Blueprint measures workflow completion, grounding and recovery—not a single attractive answer")
    f.card(70, 230, 400, 220, "Contract tests", "35 Python tests for auth, API boundaries, deterministic Foundation, navigation, titles and grounded chat fallbacks.", GREEN_SOFT, GREEN)
    f.card(500, 230, 400, 220, "Workflow structure", "Node IDs, connection targets, code syntax, error bindings, secret scanning and schema contracts.", WHITE, LINE)
    f.card(930, 230, 400, 220, "Agentic eval suite", "85 cases across scope, security, routing, state, HITL, grounding, memory, reruns, budgets and failures.", VIOLET_SOFT, VIOLET)
    f.card(1360, 230, 490, 220, "Live acceptance", "Fresh owner-scoped run, partial visibility, gate resume, unhappy path, state restoration and second-user isolation.", BLUE_SOFT, BLUE)
    f.text(70, 550, "OBSERVABILITY ENVELOPE", 23, MUTED, bold=True)
    f.card(70, 595, 1780, 175, "Recorded per route", "owner / project / run • task and attempt • selected tool/model • start/end/latency • evidence result • retry/repair reason • checkpoint • final status", SOFT, LINE)
    f.card(230, 825, 440, 130, "Release gate 1", "No unsupported claim affects a verdict.", WHITE, AMBER)
    f.card(740, 825, 440, 130, "Release gate 2", "No write or stage advance bypasses HITL.", WHITE, GREEN)
    f.card(1250, 825, 440, 130, "Release gate 3", "Happy and unhappy paths both terminate clearly.", WHITE, RED)
    f.footer("Current automated acceptance after this documentation pass: 35/35 Python tests and 85/85 agentic eval cases.")
    f.save("10-evaluation-observability")


def deployment_boundary() -> None:
    f = Figure("Deployment Boundary and Reproducibility", "Local demo is complete; public hosting needs one stable HTTPS n8n endpoint")
    f.card(90, 230, 760, 245, "Current local demonstration", "Streamlit at localhost:8501 → self-hosted n8n Docker at localhost:5679 → Supabase, You.com, Nebius, Pinecone and Mem0 over HTTPS.", GREEN_SOFT, GREEN)
    f.card(1070, 230, 760, 245, "Public deployment path", "Streamlit Community Cloud → stable public HTTPS n8n endpoint with persistent storage → the same external services and Supabase owner boundary.", BLUE_SOFT, BLUE)
    f.arrow_between(850, 352, 1050, 352)
    f.text(90, 565, "PUBLIC RELEASE CHECKLIST", 23, MUTED, bold=True)
    checks = [
        ("1", "Host n8n", "Persistent volume, TLS, credentials and webhook URL."),
        ("2", "Configure Streamlit", "Only public Supabase and webhook values in secrets."),
        ("3", "Re-run acceptance", "Happy path, denial, retry, resume and state restoration."),
        ("4", "Verify isolation", "A second anonymous user cannot read the first user's project."),
    ]
    for i, item in enumerate(checks):
        xx = 90 + i * 450
        f.card(xx, 610, 405, 210, item[1], item[2], WHITE, LINE, item[0])
    f.footer("Until n8n is public, the reliable submission demo is the local Streamlit application with a pre-completed fallback run.")
    f.save("11-deployment-boundary")


def contact_sheet() -> None:
    files = sorted(p for p in OUT.glob("*.png") if p.name != "00-architecture-review-sheet.png")
    thumb_w, thumb_h = 600, 338
    rows = math.ceil(len(files) / 3)
    sheet = Image.new("RGB", (thumb_w * 3 + 80, thumb_h * rows + 180), rgb(WHITE))
    draw = ImageDraw.Draw(sheet)
    draw.text((40, 28), "Blueprint architecture figure review sheet", font=ImageFont.truetype(str(FONT_BOLD), 38), fill=rgb(INK))
    for i, path in enumerate(files):
        img = Image.open(path).convert("RGB")
        img.thumbnail((thumb_w - 24, thumb_h - 48))
        x = 30 + (i % 3) * thumb_w
        y = 105 + (i // 3) * thumb_h
        sheet.paste(img, (x, y))
        draw.text((x, y + img.height + 6), path.stem, font=ImageFont.truetype(str(FONT_REG), 17), fill=rgb(MUTED))
    sheet.save(OUT / "00-architecture-review-sheet.png", quality=95)


def write_index() -> None:
    rows = [
        ("00-readme-architecture", "README architecture summary"),
        ("01-blueprint-project-canvas", "One-image project canvas"),
        ("02-end-to-end-system-architecture", "End-to-end system architecture"),
        ("03-founder-user-journey", "Founder user flow"),
        ("04-adaptive-orchestration-routing", "Adaptive branching and closed-loop routing"),
        ("05-stage1-parallel-research", "Stage 1 parallel research and convergence"),
        ("06-agent-handoffs-shared-state", "Typed handoffs and shared state"),
        ("07-evidence-grounding-rag", "Grounded RAG and action coaching"),
        ("08-state-and-memory-model", "State and memory model"),
        ("09-failure-hitl-recovery", "Failure handling and HITL"),
        ("10-evaluation-observability", "Evaluation and observability"),
        ("11-deployment-boundary", "Deployment boundary"),
    ]
    lines = [
        "# Blueprint Architecture Figures", "",
        "All figures use a white background, large Segoe UI type, thin borders and restrained semantic colour. Each is available as PNG and editable SVG.", "",
        "| Figure | Purpose |", "|---|---|",
    ]
    lines.extend(f"| [{stem}](figures/architecture/{stem}.png) | {purpose} |" for stem, purpose in rows)
    lines += ["", "A review contact sheet is available at `docs/figures/architecture/00-architecture-review-sheet.png`."]
    (ROOT / "docs" / "ARCHITECTURE-FIGURES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    for function in (
        readme_architecture, project_canvas, end_to_end_architecture, founder_journey,
        orchestration_flow, stage1_flow, handoff_contracts, rag_flow, memory_model,
        failure_flow, evaluation_flow, deployment_boundary,
    ):
        function()
    contact_sheet()
    write_index()


if __name__ == "__main__":
    main()
