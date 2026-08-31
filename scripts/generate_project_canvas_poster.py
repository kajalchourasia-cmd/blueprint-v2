"""Generate Blueprint's review-only 4K project canvas poster.

The asset is deliberately standalone until it is approved. Running this script
does not edit README.md, the submission document, or the figure index.
"""

from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures" / "architecture"
S = 2
W, H = 1920, 1080

WHITE = "#FFFFFF"
INK = "#16201B"
MUTED = "#5D6963"
LINE = "#D6DCD8"
SOFT = "#F6F8F6"
GREEN = "#176447"
GREEN_SOFT = "#EAF3EE"
BLUE = "#2E5F8A"
BLUE_SOFT = "#EBF2F8"
VIOLET = "#6D5AA6"
VIOLET_SOFT = "#F2EEF8"
AMBER = "#936515"
AMBER_SOFT = "#FCF4E2"
RED = "#A64B43"
RED_SOFT = "#FBEDEC"
BROWN = "#7B583E"

FONT_REG = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/seguisb.ttf")


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


class Poster:
    def __init__(self) -> None:
        self.image = Image.new("RGB", (W * S, H * S), rgb(WHITE))
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*S}" height="{H*S}" viewBox="0 0 {W*S} {H*S}">',
            f'<rect width="{W*S}" height="{H*S}" fill="{WHITE}"/>',
            '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 z" fill="#6A746E"/></marker></defs>',
        ]

    def font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size * S)

    def text(self, x: float, y: float, value: str, size: int, color: str = INK,
             bold: bool = False, anchor: str = "left") -> None:
        font = self.font(size, bold)
        bbox = self.draw.textbbox((0, 0), value, font=font)
        tw = bbox[2] - bbox[0]
        px = x * S if anchor == "left" else x * S - tw / 2 if anchor == "center" else x * S - tw
        self.draw.text((px, y * S), value, font=font, fill=rgb(color))
        svg_anchor = {"left": "start", "center": "middle", "right": "end"}[anchor]
        self.svg.append(
            f'<text x="{x*S}" y="{(y+size)*S}" text-anchor="{svg_anchor}" '
            f'font-family="Segoe UI, Arial" font-size="{size*S}" font-weight="{600 if bold else 400}" '
            f'fill="{color}">{html.escape(value)}</text>'
        )

    def lines(self, value: str, width: float, size: int, bold: bool = False) -> list[str]:
        words = value.split()
        rows: list[str] = []
        current = ""
        font = self.font(size, bold)
        for word in words:
            trial = f"{current} {word}".strip()
            if self.draw.textbbox((0, 0), trial, font=font)[2] <= width * S or not current:
                current = trial
            else:
                rows.append(current)
                current = word
        if current:
            rows.append(current)
        return rows

    def wrapped(self, x: float, y: float, value: str, width: float, size: int,
                color: str = MUTED, bold: bool = False, gap: int = 5,
                max_lines: int | None = None) -> float:
        rows = self.lines(value, width, size, bold)
        if max_lines and len(rows) > max_lines:
            rows = rows[:max_lines]
            rows[-1] = rows[-1].rstrip(".,;:") + "…"
        for i, row in enumerate(rows):
            self.text(x, y + i * (size + gap), row, size, color, bold)
        return y + len(rows) * (size + gap)

    def rect(self, x: float, y: float, w: float, h: float, fill: str = WHITE,
             stroke: str = LINE, radius: int = 14, sw: int = 1) -> None:
        box = (round(x*S), round(y*S), round((x+w)*S), round((y+h)*S))
        self.draw.rounded_rectangle(box, radius*S, fill=rgb(fill), outline=rgb(stroke), width=sw*S)
        self.svg.append(
            f'<rect x="{x*S}" y="{y*S}" width="{w*S}" height="{h*S}" rx="{radius*S}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw*S}"/>'
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = LINE,
             width: int = 2, arrow: bool = False, dashed: bool = False) -> None:
        self.draw.line((x1*S, y1*S, x2*S, y2*S), fill=rgb(color), width=width*S)
        if arrow:
            angle = math.atan2(y2-y1, x2-x1)
            size = 9*S
            x2s, y2s = x2*S, y2*S
            head = [
                (x2s, y2s),
                (x2s-size*math.cos(angle-0.48), y2s-size*math.sin(angle-0.48)),
                (x2s-size*math.cos(angle+0.48), y2s-size*math.sin(angle+0.48)),
            ]
            self.draw.polygon(head, fill=rgb(color))
        self.svg.append(
            f'<line x1="{x1*S}" y1="{y1*S}" x2="{x2*S}" y2="{y2*S}" stroke="{color}" '
            f'stroke-width="{width*S}"{(" stroke-dasharray=\"12 10\"" if dashed else "")}'
            f'{(" marker-end=\"url(#arrow)\"" if arrow else "")}/>'
        )

    def polyline(self, points: list[tuple[float, float]], color: str = MUTED,
                 width: int = 2, arrow: bool = True, dashed: bool = False) -> None:
        pts = [(x*S, y*S) for x, y in points]
        self.draw.line(pts, fill=rgb(color), width=width*S, joint="curve")
        if arrow and len(points) > 1:
            (x1, y1), (x2, y2) = points[-2], points[-1]
            angle = math.atan2(y2-y1, x2-x1)
            size = 9*S
            x2s, y2s = x2*S, y2*S
            head = [
                (x2s, y2s),
                (x2s-size*math.cos(angle-0.48), y2s-size*math.sin(angle-0.48)),
                (x2s-size*math.cos(angle+0.48), y2s-size*math.sin(angle+0.48)),
            ]
            self.draw.polygon(head, fill=rgb(color))
        raw = " ".join(f"{x*S},{y*S}" for x, y in points)
        self.svg.append(
            f'<polyline points="{raw}" fill="none" stroke="{color}" stroke-width="{width*S}" '
            f'stroke-linejoin="round"{(" stroke-dasharray=\"12 10\"" if dashed else "")}'
            f'{(" marker-end=\"url(#arrow)\"" if arrow else "")}/>'
        )

    def circle(self, cx: float, cy: float, r: float, fill: str, stroke: str = LINE, sw: int = 1) -> None:
        self.draw.ellipse(((cx-r)*S, (cy-r)*S, (cx+r)*S, (cy+r)*S),
                          fill=rgb(fill), outline=rgb(stroke), width=sw*S)
        self.svg.append(
            f'<circle cx="{cx*S}" cy="{cy*S}" r="{r*S}" fill="{fill}" stroke="{stroke}" stroke-width="{sw*S}"/>'
        )

    def section(self, x: float, y: float, label: str, color: str = BLUE) -> None:
        self.text(x, y, label.upper(), 13, color, bold=True)

    def bullet(self, x: float, y: float, value: str, width: float, color: str = GREEN,
               size: int = 15) -> float:
        self.circle(x+5, y+10, 4, color, color)
        return self.wrapped(x+18, y, value, width-18, size, INK, gap=4)

    def numbered(self, x: float, y: float, number: int, value: str, width: float) -> float:
        self.circle(x+11, y+11, 11, BLUE, BLUE)
        self.text(x+11, y-2, str(number), 13, WHITE, bold=True, anchor="center")
        return self.wrapped(x+32, y, value, width-32, 14, INK, gap=3)

    def mini_card(self, x: float, y: float, w: float, h: float, role: str, title: str,
                  body: str, fill: str, stroke: str) -> None:
        self.rect(x, y, w, h, fill, stroke, 10, 1)
        role_color = MUTED if stroke == LINE else stroke
        self.text(x+14, y+10, role.upper(), 10, role_color, bold=True)
        self.text(x+14, y+29, title, 16, INK, bold=True)
        self.wrapped(x+14, y+52, body, w-28, 12, MUTED, gap=3, max_lines=3)

    def node_icon(self, x: float, y: float) -> None:
        self.rect(x, y, 52, 52, GREEN_SOFT, GREEN, 13, 1)
        pts = [(x+15, y+16), (x+37, y+14), (x+26, y+37), (x+39, y+36)]
        self.line(pts[0][0], pts[0][1], pts[1][0], pts[1][1], GREEN, 2)
        self.line(pts[0][0], pts[0][1], pts[2][0], pts[2][1], GREEN, 2)
        self.line(pts[1][0], pts[1][1], pts[3][0], pts[3][1], GREEN, 2)
        self.line(pts[2][0], pts[2][1], pts[3][0], pts[3][1], GREEN, 2)
        for px, py in pts:
            self.circle(px, py, 4, GREEN, GREEN)

    def save(self, stem: str) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        self.image.save(OUT / f"{stem}.png", optimize=True)
        self.svg.append("</svg>")
        (OUT / f"{stem}.svg").write_text("\n".join(self.svg), encoding="utf-8")


def build() -> None:
    p = Poster()

    # Header
    p.rect(22, 20, 1876, 82, SOFT, LINE, 18, 1)
    p.node_icon(42, 35)
    p.text(112, 32, "BLUEPRINT", 31, INK, bold=True)
    p.text(112, 68, "Evidence-backed founder validation system", 15, MUTED)
    p.text(1874, 37, "PROJECT CANVAS · V1", 14, BLUE, bold=True, anchor="right")
    p.text(1874, 66, "Idea → evidence → founder-approved next move", 14, MUTED, anchor="right")

    # Column surfaces
    left_x, left_w = 22, 396
    center_x, center_w = 436, 1020
    right_x, right_w = 1474, 424
    top_y, panel_h = 120, 880
    p.rect(left_x, top_y, left_w, panel_h, WHITE, LINE, 18, 1)
    p.rect(center_x, top_y, center_w, panel_h, WHITE, BLUE, 18, 1)
    p.rect(right_x, top_y, right_w, panel_h, WHITE, LINE, 18, 1)

    # Left: product story
    p.section(44, 142, "The product", GREEN)
    p.text(44, 168, "Turn the unfinished idea", 29, INK, bold=True)
    p.text(44, 202, "into your next provable move.", 29, GREEN, bold=True)
    p.wrapped(
        44, 248,
        "Blueprint helps an early founder replace scattered research with one supervised path from context to evidence, verdict and action.",
        350, 16, MUTED, gap=5,
    )
    p.line(44, 330, 394, 330, LINE, 1)

    p.section(44, 350, "What it does", BLUE)
    bullets = [
        "Captures the idea, founder goal, constraints and selected research lanes.",
        "Builds an immediate Foundation from confirmed onboarding context.",
        "Runs customer, competitor and market specialists in parallel.",
        "Audits material claims before they can affect the verdict.",
        "Routes by evidence, failure state and the founder’s decision.",
        "Produces a versioned Blueprint, scenarios, actionables and grounded chat.",
    ]
    by = 380
    for item in bullets:
        by = p.bullet(44, by, item, 350, GREEN, 14) + 10

    p.line(44, 630, 394, 630, LINE, 1)
    p.section(44, 650, "Founder outcomes", VIOLET)
    outcomes = [
        "A clear problem and user hypothesis",
        "Real alternatives, gaps and market constraints",
        "A transparent viability decision with limitations",
        "A founder-approved next route—not generic weekly tasks",
    ]
    oy = 680
    for item in outcomes:
        oy = p.bullet(44, oy, item, 350, VIOLET, 14) + 9

    p.rect(44, 824, 350, 148, SOFT, LINE, 13, 1)
    p.section(62, 842, "Verified build evidence", GREEN)
    metrics = [("39/39", "Python contracts"), ("85/85", "Agentic cases"),
               ("21/21", "Closed-loop checks"), ("27", "n8n workflows")]
    for i, (value, label) in enumerate(metrics):
        mx = 62 + (i % 2) * 165
        my = 872 + (i // 2) * 48
        p.text(mx, my, value, 19, INK, bold=True)
        p.text(mx, my+24, label, 11, MUTED)

    # Center: architecture header
    p.text(464, 142, "Agentic decision system", 25, INK, bold=True)
    p.text(1432, 148, "n8n control plane", 13, BLUE, bold=True, anchor="right")
    p.line(464, 182, 1432, 182, LINE, 1)

    # Left rail inside architecture
    p.mini_card(464, 205, 200, 128, "Experience", "Streamlit UI",
                "Onboarding, progress, research sections, approvals and no-login owner session.", GREEN_SOFT, GREEN)
    p.mini_card(464, 353, 200, 146, "Canonical state", "Supabase + RLS",
                "Projects, runs, task graph, evidence, checkpoints, errors and Blueprint versions.", GREEN_SOFT, GREEN)
    p.mini_card(464, 519, 200, 116, "Preference memory", "Mem0",
                "Confirmed goals, preferences, corrections and decisions only.", VIOLET_SOFT, VIOLET)
    p.mini_card(464, 655, 200, 126, "Accepted evidence", "Pinecone",
                "Semantic projection after audit; every hit is revalidated against Supabase.", BLUE_SOFT, BLUE)

    # Orchestrator enclosure and central steps
    p.rect(686, 205, 518, 576, BLUE_SOFT, BLUE, 16, 2)
    p.text(710, 220, "ADAPTIVE SUPERVISOR / ORCHESTRATOR", 12, BLUE, bold=True)
    p.text(710, 245, "Stateful routing, bounded autonomy", 21, INK, bold=True)

    p.mini_card(710, 286, 220, 92, "Deterministic", "1 · Foundation",
                "Immediate problem framing from onboarding—no web wait.", GREEN_SOFT, GREEN)
    p.mini_card(950, 286, 230, 92, "Policy", "2 · Plan + schedule",
                "Build the DAG and release only eligible tasks.", GREEN_SOFT, GREEN)
    p.arrow = p.line
    p.line(930, 332, 950, 332, MUTED, 2, True)

    # Parallel specialist lane
    p.text(710, 397, "3 · PARALLEL SPECIALIST AGENTS", 12, VIOLET, bold=True)
    agent_w = 143
    agents = [
        ("Customer / User", "Pain, personas, channels and interviews"),
        ("Competitor", "Direct, indirect, pricing and gaps"),
        ("Market", "Secondary evidence and direction"),
    ]
    for i, (title, body) in enumerate(agents):
        ax = 710 + i * 155
        p.mini_card(ax, 422, agent_w, 108, "Specialist", title, body, VIOLET_SOFT, VIOLET)
        p.line(ax+agent_w/2, 530, ax+agent_w/2, 546, VIOLET, 2)
    p.line(781, 546, 1091, 546, VIOLET, 2)
    p.line(936, 546, 936, 557, VIOLET, 2, True)

    p.mini_card(710, 557, 220, 94, "Independent auditor", "4 · Evidence audit",
                "Accept, reject or flag claims and contradictions.", AMBER_SOFT, AMBER)
    p.mini_card(950, 557, 230, 94, "Deterministic + critic", "5 · Verdict + QA",
                "40/30/30 score, confidence and bounded critique.", AMBER_SOFT, AMBER)
    p.line(930, 604, 950, 604, MUTED, 2, True)
    p.mini_card(710, 672, 470, 86, "Human decision layer · HITL", "6 · Founder checkpoint",
                "Proceed · revise · rerun · override with reason · pause", AMBER_SOFT, BROWN)

    # Revision loop inside orchestrator
    p.polyline([(1168, 672), (1192, 672), (1192, 405), (1132, 405)], RED, 2, True, True)
    p.text(1184, 526, "bounded revision", 10, RED, bold=True, anchor="right")

    # Right tool rail
    p.mini_card(1226, 205, 206, 114, "Discovery tool", "You.com",
                "Current-source search for customer, competitor and market agents.", SOFT, LINE)
    p.mini_card(1226, 339, 206, 116, "Model service", "Nebius",
                "Structured extraction, synthesis, critique and RAG answers.", SOFT, LINE)
    p.mini_card(1226, 475, 206, 116, "Recovery", "Resilience controller",
                "Retry, repair, reload, replan, partial review or safe failure.", RED_SOFT, RED)
    p.mini_card(1226, 611, 206, 116, "Observability", "Audit + Error Writer",
                "Route reason, attempt, latency, budget and terminal state.", SOFT, LINE)
    p.polyline([(1204, 449), (1215, 449), (1215, 262), (1226, 262)], MUTED, 2)
    p.polyline([(1204, 510), (1217, 510), (1217, 397), (1226, 397)], MUTED, 2)
    p.polyline([(1204, 610), (1218, 610), (1218, 533), (1226, 533)], RED, 2)

    # System output and RAG
    p.rect(686, 803, 746, 168, GREEN_SOFT, GREEN, 14, 1)
    p.section(710, 821, "Founder-visible output", GREEN)
    p.text(710, 846, "Versioned Blueprint", 22, INK, bold=True)
    p.wrapped(710, 878,
              "Audited research, decision rationale, financial scenarios, open risks and the next defensible move.",
              450, 14, MUTED, gap=4)
    p.rect(1180, 830, 228, 116, BLUE_SOFT, BLUE, 11, 1)
    p.text(1196, 845, "GROUNDED RAG AGENT", 10, BLUE, bold=True)
    p.text(1196, 867, "Research Copilot", 17, INK, bold=True)
    p.wrapped(1196, 894, "Section-scoped answers, sources, limitations and action coaching.", 196, 12, MUTED, gap=3)
    p.line(1160, 888, 1180, 888, BLUE, 2, True)
    p.polyline([(664, 426), (678, 426), (678, 255), (686, 255)], GREEN, 2)
    p.polyline([(664, 578), (674, 578), (674, 276), (686, 276)], VIOLET, 2, False, True)
    p.polyline([(664, 718), (670, 718), (670, 920), (686, 920)], BLUE, 2, True, True)

    # Right: explainer
    p.section(1498, 142, "How it works", BLUE)
    p.text(1498, 168, "From idea to decision", 24, INK, bold=True)
    steps = [
        "Founder enters an idea, goal and constraints.",
        "Foundation appears immediately from confirmed context.",
        "Supervisor builds a dynamic dependency graph.",
        "Three specialists research in parallel.",
        "An independent auditor rejects weak claims.",
        "Verdict engine scores; critic challenges quality.",
        "Founder approves the next route at HITL.",
        "Blueprint evolves; RAG explains every section.",
    ]
    sy = 214
    for i, step in enumerate(steps, start=1):
        sy = p.numbered(1498, sy, i, step, 370) + 11

    p.line(1498, 516, 1874, 516, LINE, 1)
    p.section(1498, 536, "Trust and control", GREEN)
    p.text(1498, 562, "Evidence before confidence", 21, INK, bold=True)
    trust = [
        "Supabase is truth; Mem0 and Pinecone are bounded projections.",
        "Claims are cited or remain explicit assumptions.",
        "Stage changes, reruns and writes require founder approval.",
        "Secret, cross-owner and hidden-reasoning requests are refused.",
        "Failures preserve completed work and end visibly.",
    ]
    ty = 598
    for item in trust:
        ty = p.bullet(1498, ty, item, 370, GREEN, 13) + 7

    p.rect(1498, 838, 376, 134, AMBER_SOFT, AMBER, 13, 1)
    p.section(1518, 854, "Why this is agentic", AMBER)
    p.text(1518, 878, "Agents where judgment matters.", 17, INK, bold=True)
    p.text(1518, 902, "Determinism where trust matters.", 17, INK, bold=True)
    p.text(1518, 926, "A human where consequences matter.", 17, INK, bold=True)
    p.text(1518, 952, "The route changes after evidence, failure or feedback.", 11, MUTED)

    # Footer band
    p.rect(22, 1018, 1876, 42, SOFT, LINE, 13, 1)
    stack = "STREAMLIT   ·   n8n   ·   SUPABASE   ·   YOU.COM   ·   NEBIUS   ·   PINECONE   ·   MEM0"
    p.text(44, 1028, stack, 12, BLUE, bold=True)
    p.text(1874, 1028, "Evidence-first · progressive · founder-controlled · failure-aware", 12, GREEN, bold=True, anchor="right")

    p.save("13-blueprint-project-canvas")


if __name__ == "__main__":
    build()
