"""Generate deterministic Agile evidence charts from the repository history.

The charts intentionally distinguish Git/GitHub evidence from Jira burndown data.
Run from the repository root with::

    python tools/generate_git_evidence_charts.py
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from textwrap import wrap


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "evidence"
PR_HISTORY = OUTPUT / "pr_history.json"

INK = "#172033"
MUTED = "#5f6b7a"
GRID = "#d9e1ea"
BLUE = "#2f6feb"
BLUE_LIGHT = "#dbeafe"
GREEN = "#1a7f37"
GREEN_LIGHT = "#dcfce7"
AMBER = "#bf6a02"
AMBER_LIGHT = "#fff1cc"
PURPLE = "#8250df"
PURPLE_LIGHT = "#eee5ff"
RED = "#cf222e"
RED_LIGHT = "#ffebe9"
PAPER = "#ffffff"
PANEL = "#f6f8fa"


# Jira supplies the planned work-item scope and titles. The evidence date below is
# the first/final origin/main commit that can reasonably support completion of the
# item; it is not copied from (or presented as) Jira's resolution timestamp.
BURNDOWN_SPRINTS = [
    {
        "number": 0,
        "start": "2026-10-14",
        "end": "2026-10-20",
        "goal": "Shared architecture/API contracts and five Core 1 runnable scenarios",
        "items": [
            {"key": "SCRUM-1", "title": "Sprint 0 Review and Retrospective", "evidence_date": None, "commits": []},
            {"key": "SCRUM-12", "title": "Fall Monitoring and Risk Assessment", "evidence_date": "2026-10-21", "commits": ["d9b42a7"]},
            {"key": "SCRUM-13", "title": "Natural Language Goal Interpretation", "evidence_date": "2026-10-24", "commits": ["75cd954"]},
            {"key": "SCRUM-14", "title": "Pet Event Monitoring", "evidence_date": "2026-10-19", "commits": ["3f5e636"]},
            {"key": "SCRUM-15", "title": "Hazard and Intrusion Monitoring", "evidence_date": "2026-10-21", "commits": ["364206c"]},
            {"key": "SCRUM-16", "title": "Environment and Preference Assessment", "evidence_date": "2026-10-21", "commits": ["2eaa35c"]},
            {"key": "SCRUM-17", "title": "API Contracts and Agent Message Schema", "evidence_date": "2026-10-18", "commits": ["afe844b"]},
            {"key": "SCRUM-18", "title": "HomeCoordinatorAgent and Agent Orchestration", "evidence_date": "2026-10-20", "commits": ["4d0af7a"]},
            {"key": "SCRUM-19", "title": "DeviceControlTool and Simulated Devices", "evidence_date": "2026-10-20", "commits": ["4d0af7a"]},
            {"key": "SCRUM-20", "title": "Shared Sensor/Event Models and Simulation", "evidence_date": "2026-10-19", "commits": ["b71a67f", "8f71f0"]},
            {"key": "SCRUM-21", "title": "Security Policy and Notification Integration", "evidence_date": "2026-10-21", "commits": ["364206c"]},
            {"key": "SCRUM-22", "title": "Shared Environment/Preference Context", "evidence_date": "2026-10-21", "commits": ["2eaa35c"]},
            {"key": "SCRUM-23", "title": "LLM Service and Fallback Handling", "evidence_date": "2026-10-19", "commits": ["b6a64f8", "33cce8e"]},
        ],
    },
    {
        "number": 1,
        "start": "2026-10-21",
        "end": "2026-10-27",
        "goal": "Five Core 2 workflows and five optional extensions through shared agents",
        "items": [
            {"key": "SCRUM-2", "title": "Sprint 1 Review and Retrospective", "evidence_date": None, "commits": []},
            {"key": "SCRUM-24", "title": "Resident Confirmation and Caregiver Notification", "evidence_date": "2026-10-21", "commits": ["4136004"]},
            {"key": "SCRUM-25", "title": "Multi-Level Emergency Escalation", "evidence_date": "2026-10-25", "commits": ["590fa61"]},
            {"key": "SCRUM-26", "title": "Multi-Device Control and Verification", "evidence_date": "2026-10-24", "commits": ["75cd954"]},
            {"key": "SCRUM-27", "title": "Home Operating Mode Commands", "evidence_date": "2026-10-24", "commits": ["0c47518", "b8d1da9"]},
            {"key": "SCRUM-28", "title": "Owner Notification and Event Logging", "evidence_date": "2026-10-24", "commits": ["53749aa"]},
            {"key": "SCRUM-29", "title": "Automatic Pet Feeding", "evidence_date": "2026-10-24", "commits": ["53749aa"]},
            {"key": "SCRUM-30", "title": "Risk-Based Protective Response", "evidence_date": "2026-10-21", "commits": ["364206c"]},
            {"key": "SCRUM-31", "title": "Trusted External Disaster Warnings", "evidence_date": "2026-10-28", "commits": ["0525a82"]},
            {"key": "SCRUM-32", "title": "Safe Energy and Comfort Control", "evidence_date": "2026-10-21", "commits": ["8655a8e"]},
            {"key": "SCRUM-33", "title": "Energy and Safety Trade-off Explanations", "evidence_date": "2026-10-21", "commits": ["3f44771"]},
        ],
    },
    {
        "number": 2,
        "start": "2026-10-28",
        "end": "2026-10-31",
        "goal": "Acceptance, integration fixes, safety review and clean-source deployment",
        "items": [
            {"key": "SCRUM-3", "title": "Sprint 2 Final Review and Retrospective", "evidence_date": None, "commits": []},
            {"key": "SCRUM-34", "title": "Elderly Safety Acceptance Tests", "evidence_date": "2026-10-28", "commits": ["ec2d130"]},
            {"key": "SCRUM-35", "title": "Smart Home Control Acceptance Tests", "evidence_date": "2026-10-31", "commits": ["78c3506"]},
            {"key": "SCRUM-36", "title": "Pet Care Acceptance Tests", "evidence_date": "2026-10-24", "commits": ["53749aa", "dd5a7e2"]},
            {"key": "SCRUM-37", "title": "Home Security Acceptance Tests", "evidence_date": "2026-10-28", "commits": ["a3e99aa", "d66f324"]},
            {"key": "SCRUM-38", "title": "Energy and Comfort Acceptance Tests", "evidence_date": "2026-10-21", "commits": ["f93437f"]},
            {"key": "SCRUM-39", "title": "Integration and API Contract Bugs", "evidence_date": "2026-10-31", "commits": ["4e7607e", "a84e781"]},
            {"key": "SCRUM-40", "title": "Acceptance Results and Sprint Feedback", "evidence_date": "2026-10-30", "commits": ["c264023"]},
            {"key": "SCRUM-41", "title": "Rebuild and Deploy from Submitted Source", "evidence_date": "2026-10-30", "commits": ["3c81277", "986de17"]},
            {"key": "SCRUM-42", "title": "Safety, Privacy and Fallback Review", "evidence_date": "2026-10-31", "commits": ["a84e781"]},
            {"key": "SCRUM-43", "title": "Contribution Statement and Canvas Submission", "evidence_date": None, "commits": []},
        ],
    },
]


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True, encoding="utf-8"
    ).strip()


def text(x: float, y: float, value: str, *, size: int = 16, fill: str = INK,
         weight: int = 400, anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{escape(value)}</text>'
    )


def multiline(x: float, y: float, value: str, *, width: int, size: int = 15,
              fill: str = INK, weight: int = 400, line_height: int = 21) -> tuple[str, int]:
    lines = wrap(value, width=width, break_long_words=False, break_on_hyphens=False) or [""]
    chunks = [
        f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">'
    ]
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else line_height
        chunks.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    chunks.append("</text>")
    return "".join(chunks), len(lines)


def svg_document(width: int, height: int, body: list[str], *, title_value: str) -> str:
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title_value)}">',
        f"<title>{escape(title_value)}</title>",
        f'<rect width="{width}" height="{height}" fill="{PAPER}"/>',
        *body,
        "</svg>",
        "",
    ])


def commits() -> list[dict[str, object]]:
    raw = git("log", "origin/main", "--reverse", "--pretty=format:%H%x1f%P%x1f%aI%x1f%s")
    rows: list[dict[str, object]] = []
    for line in raw.splitlines():
        sha, parents, authored, subject = line.split("\x1f", 3)
        rows.append({
            "sha": sha,
            "parents": parents.split() if parents else [],
            "date": datetime.fromisoformat(authored).date(),
            "subject": subject,
        })
    return rows


def rounded_max(value: int, step: int = 5) -> int:
    return max(step, ((value + step - 1) // step) * step)


def activity_chart(rows: list[dict[str, object]], head: str) -> str:
    start = date(2026, 10, 15)
    end = date(2026, 10, 31)
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    direct = Counter(row["date"] for row in rows if len(row["parents"]) <= 1)
    merges = Counter(row["date"] for row in rows if len(row["parents"]) > 1)
    maximum = rounded_max(max(direct[d] + merges[d] for d in dates))

    width, height = 1500, 820
    left, right, top, bottom = 95, 55, 245, 145
    plot_w, plot_h = width - left - right, height - top - bottom
    slot = plot_w / len(dates)
    bar_w = min(44, slot * 0.62)
    body: list[str] = []
    body.append(text(60, 58, "Repository activity by day", size=30, weight=700))
    body.append(text(60, 88, "Actual origin/main commit events, separated into direct and merge commits", size=17, fill=MUTED))

    bands = [
        (date(2026, 10, 15), date(2026, 10, 20), "Sprint 0 · 14–20 Oct", BLUE_LIGHT, BLUE),
        (date(2026, 10, 21), date(2026, 10, 27), "Sprint 1 · 21–27 Oct", GREEN_LIGHT, GREEN),
        (date(2026, 10, 28), date(2026, 10, 31), "Sprint 2 · 28–31 Oct", PURPLE_LIGHT, PURPLE),
    ]
    for band_start, band_end, label, fill, stroke in bands:
        first = max(0, (band_start - start).days)
        last = min(len(dates) - 1, (band_end - start).days)
        x = left + first * slot + 2
        w = (last - first + 1) * slot - 4
        body.append(f'<rect x="{x:.1f}" y="125" width="{w:.1f}" height="48" rx="8" fill="{fill}" stroke="{stroke}"/>')
        body.append(text(x + w / 2, 155, label, size=15, fill=stroke, weight=700, anchor="middle"))
    body.append(text(width - 58, 198, "31 Oct is the Sprint 2 / Sprint 3 hand-off", size=14, fill=AMBER, anchor="end"))

    for tick in range(0, maximum + 1, 5):
        y = top + plot_h - (tick / maximum) * plot_h
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        body.append(text(left - 16, y + 5, str(tick), size=14, fill=MUTED, anchor="end"))
    body.append(text(27, top + plot_h / 2, "Commit events", size=16, fill=MUTED, anchor="middle"))

    for index, day in enumerate(dates):
        x = left + index * slot + (slot - bar_w) / 2
        direct_h = direct[day] / maximum * plot_h
        merge_h = merges[day] / maximum * plot_h
        base = top + plot_h
        if direct_h:
            body.append(f'<rect x="{x:.1f}" y="{base-direct_h:.1f}" width="{bar_w:.1f}" height="{direct_h:.1f}" rx="3" fill="{BLUE}"/>')
        if merge_h:
            body.append(f'<rect x="{x:.1f}" y="{base-direct_h-merge_h:.1f}" width="{bar_w:.1f}" height="{merge_h:.1f}" rx="3" fill="{AMBER}"/>')
        total = direct[day] + merges[day]
        if total:
            body.append(text(x + bar_w / 2, base - direct_h - merge_h - 9, str(total), size=13, weight=700, anchor="middle"))
        body.append(text(x + bar_w / 2, base + 25, day.strftime("%d"), size=13, fill=MUTED, anchor="middle"))
    body.append(text(left + plot_w / 2, top + plot_h + 52, "October 2026", size=15, fill=MUTED, anchor="middle"))

    legend_y = 735
    body.append(f'<rect x="95" y="{legend_y-15}" width="18" height="18" rx="3" fill="{BLUE}"/>')
    body.append(text(123, legend_y, "Direct commit", size=14))
    body.append(f'<rect x="250" y="{legend_y-15}" width="18" height="18" rx="3" fill="{AMBER}"/>')
    body.append(text(278, legend_y, "Merge commit", size=14))
    body.append(text(60, 785, f"Source: Git history of origin/main @ {head}. Counts are repository events, not contribution percentages.", size=14, fill=MUTED))
    return svg_document(width, height, body, title_value="Repository activity by day")


def reconstructed_burndown_chart(sprint: dict[str, object], head: str) -> str:
    """Draw a Jira-like chart while visibly preserving its reconstructed status."""
    start = date.fromisoformat(str(sprint["start"]))
    end = date.fromisoformat(str(sprint["end"]))
    items = list(sprint["items"])
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    precompleted = sum(
        1 for item in items
        if item["evidence_date"] and date.fromisoformat(item["evidence_date"]) < start
    )
    initial = len(items) - precompleted
    completions = Counter(
        date.fromisoformat(item["evidence_date"])
        for item in items
        if item["evidence_date"]
        and start <= date.fromisoformat(item["evidence_date"]) <= end
    )
    final_remaining = initial - sum(completions.values())
    outside_after = sum(
        1 for item in items
        if item["evidence_date"] and date.fromisoformat(item["evidence_date"]) > end
    )
    no_git_evidence = sum(1 for item in items if not item["evidence_date"])

    width, height = 940, 900
    plot_x, plot_y, plot_w, plot_h = 110, 310, 720, 365
    body: list[str] = []
    body.append(text(45, 53, "Git-derived reconstructed burndown", size=28, weight=700))
    body.append(text(45, 82, "Jira work-item scope reconciled with origin/main implementation evidence", size=16, fill=MUTED))
    body.append(f'<rect x="660" y="32" width="235" height="32" rx="16" fill="{AMBER_LIGHT}"/>')
    body.append(text(777.5, 54, "RECONSTRUCTION - NOT JIRA EXPORT", size=11, fill=AMBER, weight=700, anchor="middle"))

    body.append(text(45, 124, "Sprint", size=13, fill=MUTED))
    body.append(f'<rect x="45" y="136" width="280" height="47" rx="4" fill="{PAPER}" stroke="#8c9bab"/>')
    body.append(text(61, 166, f'SCRUM Sprint {sprint["number"]} (reconstructed)', size=15))
    body.append(text(355, 124, "Estimation field", size=13, fill=MUTED))
    body.append(f'<rect x="355" y="136" width="225" height="47" rx="4" fill="{PAPER}" stroke="{BLUE}" stroke-width="1.5"/>')
    body.append(text(371, 166, "Work item count", size=15))
    body.append(text(45, 222, f'Date - {start.strftime("%B %d, %Y")} to {end.strftime("%B %d, %Y")}', size=15, weight=600))
    goal_svg, _ = multiline(45, 250, "Sprint goal - " + str(sprint["goal"]), width=105, size=13, fill=MUTED, line_height=18)
    body.append(goal_svg)

    body.append(f'<line x1="110" y1="289" x2="145" y2="289" stroke="#d04a3a" stroke-width="4"/>')
    body.append(text(155, 294, "Remaining work", size=14, weight=700))
    body.append(f'<line x1="335" y1="289" x2="370" y2="289" stroke="#b7bdc5" stroke-width="4"/>')
    body.append(text(380, 294, "Guideline", size=14, weight=700))

    y_max = max(1, len(items))
    for tick in range(0, y_max + 1, 2):
        y = plot_y + plot_h - tick / y_max * plot_h
        body.append(f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x+plot_w}" y2="{y:.1f}" stroke="#e6e9ed"/>')
        body.append(text(plot_x - 13, y + 5, str(tick), size=12, fill=MUTED, anchor="end"))
    body.append(f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#aeb6c0"/>')

    guideline_start_y = plot_y + plot_h - initial / y_max * plot_h
    body.append(f'<line x1="{plot_x}" y1="{guideline_start_y:.1f}" x2="{plot_x+plot_w}" y2="{plot_y+plot_h}" stroke="#b7bdc5" stroke-width="2"/>')

    def x_for(day: date, offset: float = 0.0) -> float:
        span = max(1, len(days) - 1)
        return plot_x + ((day - start).days + offset) / span * plot_w

    def y_for(value: int) -> float:
        return plot_y + plot_h - value / y_max * plot_h

    remaining = initial
    points: list[tuple[float, float]] = [(plot_x, y_for(remaining))]
    for day in days:
        count = completions[day]
        if not count:
            continue
        event_x = min(plot_x + plot_w, x_for(day, 0.55 if day < end else 0.0))
        points.append((event_x, y_for(remaining)))
        remaining -= count
        points.append((event_x, y_for(remaining)))
    points.append((plot_x + plot_w, y_for(remaining)))
    path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in points)
    body.append(f'<path d="{path}" fill="none" stroke="#d04a3a" stroke-width="3" stroke-linejoin="miter"/>')

    for index, day in enumerate(days):
        x = plot_x + index / max(1, len(days) - 1) * plot_w
        body.append(f'<line x1="{x:.1f}" y1="{plot_y+plot_h}" x2="{x:.1f}" y2="{plot_y+plot_h+7}" stroke="#808a96"/>')
        body.append(text(x, plot_y + plot_h + 27, day.strftime("%b %d"), size=11, fill=MUTED, anchor="middle"))
    body.append(text(34, plot_y + plot_h / 2, "Work item count", size=13, fill=MUTED, anchor="middle"))
    body.append(text(plot_x + plot_w / 2, plot_y + plot_h + 58, "Date", size=13, fill=MUTED, anchor="middle"))

    summary_y = 770
    body.append(f'<rect x="45" y="{summary_y-35}" width="850" height="105" rx="9" fill="{PANEL}" stroke="{GRID}"/>')
    body.append(text(65, summary_y - 7, f"Planned Jira scope: {len(items)} work items", size=14, weight=700))
    body.append(text(335, summary_y - 7, f"Pre-window Git evidence: {precompleted}", size=14, weight=700))
    body.append(text(615, summary_y - 7, f"Remaining at window end: {final_remaining}", size=14, weight=700))
    body.append(text(65, summary_y + 22, f"Evidence after window: {outside_after}; no independent Git evidence at cutoff: {no_git_evidence}.", size=13, fill=MUTED))
    body.append(text(65, summary_y + 48, f"Source cutoff: origin/main @ {head}. Mapping details: git-derived-burndown-data.json", size=13, fill=MUTED))
    body.append(text(45, 875, "Method: an item burns only when a matching main-branch implementation/test commit exists; Jira Done dates are not reused.", size=12, fill=MUTED))
    return svg_document(width, height, body, title_value=f'Git-derived reconstructed Sprint {sprint["number"]} burndown')


def arrow(body: list[str], x1: int, y: int, x2: int, color: str = MUTED) -> None:
    body.append(f'<line x1="{x1}" y1="{y}" x2="{x2-10}" y2="{y}" stroke="{color}" stroke-width="3"/>')
    body.append(f'<path d="M {x2-10} {y-6} L {x2} {y} L {x2-10} {y+6} Z" fill="{color}"/>')


def feedback_node(body: list[str], x: int, y: int, w: int, title_value: str,
                  subtitle: str, *, fill: str, stroke: str) -> None:
    body.append(f'<rect x="{x}" y="{y}" width="{w}" height="86" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    body.append(text(x + w / 2, y + 31, title_value, size=15, fill=stroke, weight=700, anchor="middle"))
    sub_svg, _ = multiline(x + 15, y + 55, subtitle, width=max(20, w // 9), size=12, fill=MUTED, line_height=16)
    body.append(sub_svg)


def feedback_chart(head: str, pr_data: dict[str, object]) -> str:
    numbers = {entry["number"] for entry in pr_data["pull_requests"]}
    if not {8, 26}.issubset(numbers):
        raise RuntimeError("pr_history.json is missing required PR #8/#26 evidence")

    width, height = 1660, 840
    body: list[str] = []
    body.append(text(55, 58, "Observed feedback loops: finding → refinement → verification", size=30, weight=700))
    body.append(text(55, 88, "Real pull-request reviews and CI outcomes, joined to the resulting commits", size=17, fill=MUTED))

    lanes = [
        ("PR #8 · Pet Care", "24–25 Oct", [
            ("Review requested changes", "Timeout stopped core monitoring", RED_LIGHT, RED),
            ("ce5a131 / dd5a7e2", "Fail-open monitoring boundary + regressions", BLUE_LIGHT, BLUE),
            ("Reviewer approval", "11 Pet tests + 134 repository tests", GREEN_LIGHT, GREEN),
            ("Merged", "26ba305", PURPLE_LIGHT, PURPLE),
        ]),
        ("PR #20 · Container CI", "30 Oct", [
            ("CI failure", "Run 41048246193: read-only /app path", RED_LIGHT, RED),
            ("546400d / 986de17", "Move test fixtures to system temp", BLUE_LIGHT, BLUE),
            ("Passing CI", "Run 41048545525", GREEN_LIGHT, GREEN),
            ("Merged", "5a00b10", PURPLE_LIGHT, PURPLE),
        ]),
        ("PR #26 · Elderly Safety", "31 Oct", [
            ("Review 1", "Unsafe prefix matching reproduced", RED_LIGHT, RED),
            ("0dffe44 + review 2", "Phrase fix; second ambiguity found", AMBER_LIGHT, AMBER),
            ("a84e781", "Complete safe-phrase rule + regressions", BLUE_LIGHT, BLUE),
            ("Green CI + merge", "c9d9570", GREEN_LIGHT, GREEN),
        ]),
    ]

    lane_top = 135
    lane_h = 195
    label_w = 225
    node_w = 285
    node_gap = 46
    node_start = 295
    for lane_index, (label, dates, nodes) in enumerate(lanes):
        y = lane_top + lane_index * lane_h
        body.append(f'<rect x="45" y="{y}" width="1570" height="164" rx="16" fill="{PANEL}"/>')
        body.append(text(70, y + 55, label, size=20, weight=700))
        body.append(text(70, y + 83, dates, size=14, fill=MUTED))
        node_y = y + 38
        for index, node in enumerate(nodes):
            x = node_start + index * (node_w + node_gap)
            feedback_node(body, x, node_y, node_w, node[0], node[1], fill=node[2], stroke=node[3])
            if index < len(nodes) - 1:
                arrow(body, x + node_w + 4, node_y + 43, x + node_w + node_gap - 4)

    body.append(text(55, 785, f"Sources: selected GitHub review metadata in docs/evidence/pr_history.json, linked Actions runs, and origin/main @ {head}.", size=14, fill=MUTED))
    body.append(text(55, 810, "The lanes show verified sequence, not a common time scale; no approval is inferred where GitHub records only requested changes.", size=14, fill=MUTED))
    return svg_document(width, height, body, title_value="Observed GitHub feedback loops")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = commits()
    head = git("rev-parse", "--short", "origin/main")
    with PR_HISTORY.open(encoding="utf-8") as handle:
        pr_data = json.load(handle)

    outputs = {
        "git-activity-by-day.svg": activity_chart(rows, head),
        "github-feedback-loops.svg": feedback_chart(head, pr_data),
    }
    for sprint in BURNDOWN_SPRINTS:
        outputs[f'git-reconstructed-sprint{sprint["number"]}-burndown.svg'] = reconstructed_burndown_chart(sprint, head)
    for name, content in outputs.items():
        (OUTPUT / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT / name}")

    manifest = {
        "created_on": "2026-11-01 Australia/Sydney",
        "classification": "Git-derived reconstruction; not a Jira export or contemporaneous burndown",
        "jira_scope_source": "Authenticated Jira Sprint 0-2 reports inspected on 2026-11-01",
        "git_source": f"origin/main @ {head}",
        "completion_rule": "An item burns on the mapped implementation/test commit date. Jira resolution dates are not reused. Items without independent Git evidence remain unburned.",
        "mapping_caveat": "Some tightly coupled work items share one commit. The mapping is an evidence interpretation and is intentionally reviewable below.",
        "sprints": BURNDOWN_SPRINTS,
    }
    manifest_path = OUTPUT / "git-derived-burndown-data.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
