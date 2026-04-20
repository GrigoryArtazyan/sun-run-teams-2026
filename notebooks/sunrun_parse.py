"""
Parse Sportstats Sun Run Teams HTML/plain-text export.
"""

from __future__ import annotations

import re
from typing import Any

# Category header
CAT = re.compile(r"^10K Team Results - (.+?) Category$")

# Team line: "  1. 5:30:28 Deloitte LLP (  41:19)" — avg may be MM:SS or H:MM:SS
_TEAM_HEAD = re.compile(r"^\s*(\d+)\.\s+(\d{1,2}:\d{2}:\d{2})\s+(.+)$")
_TIME_IN_PARENS_END = re.compile(
    r"\(\s*((?:\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2}))\s*\)\s*$"
)

# Right runner after a wide gap: bib then (time) name OR bib then bare time name (source uses both)
_RIGHT_RUNNER_PAREN = re.compile(
    r" {3,}(\d{1,5})\s+\(\s*((?:\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2}))\s*\)\s+(.+)$"
)
_RIGHT_RUNNER_BARE = re.compile(
    r" {3,}(\d{1,5})\s+((?:\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2}))\s+(.+)$"
)

# Left runner: rank + (time) name OR rank + bare_time + name
_LEFT_RUNNER = re.compile(
    r"^\s*(\d+)\s+"
    r"(?:"
    r"\(\s*((?:\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2}))\s*\)"
    r"|"
    r"((?:\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2}))"
    r")\s+(.+)$"
)


def secs(t: str) -> int:
    """H:MM:SS or MM:SS → seconds."""
    parts = [int(x) for x in t.strip().split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    raise ValueError(f"Bad time string: {t!r}")


def parse_team_line(line: str) -> dict[str, Any] | None:
    """Parse team summary line; None if not a team row."""
    s = line.strip()
    m = _TEAM_HEAD.match(s)
    if not m:
        return None
    category_rank_s, total_s, rest = m.group(1), m.group(2), m.group(3)
    m2 = _TIME_IN_PARENS_END.search(rest)
    if not m2:
        return None
    avg_s = m2.group(1)
    team_name = rest[: m2.start()].rstrip()
    if not team_name:
        return None
    return {
        "category_rank": int(category_rank_s),
        "team_total_time": total_s,
        "team_total_seconds": secs(total_s),
        "team_name": team_name,
        "team_avg_time": avg_s,
        "team_avg_seconds": secs(avg_s),
    }


def parse_runner_line(line: str) -> list[dict[str, Any]]:
    """
    Parse one physical line into one or two runners (left column, optional right).
    Returns [] if the line does not look like runner data.
    """
    raw = line.rstrip()
    right_m = _RIGHT_RUNNER_PAREN.search(raw) or _RIGHT_RUNNER_BARE.search(raw)
    if right_m:
        bib = int(right_m.group(1))
        t_r = right_m.group(2)
        name_r = right_m.group(3).strip()
        left = raw[: right_m.start()].rstrip()
        right_runner = {
            "runner_time": t_r,
            "runner_seconds": secs(t_r),
            "runner_name": name_r,
            "runner_bib": bib,
        }
    else:
        left = raw.strip()
        right_runner = None

    lm = _LEFT_RUNNER.match(left)
    if not lm:
        return []
    _rank_s = lm.group(1)
    t_left = lm.group(2) or lm.group(3)
    name_l = lm.group(4).strip()
    if not name_l:
        return []
    left_runner = {
        "runner_time": t_left,
        "runner_seconds": secs(t_left),
        "runner_name": name_l,
        "runner_bib": None,
    }

    out = [left_runner]
    if right_runner is not None:
        out.append(right_runner)
    return out


def parse_sunrun_teams_text(text: str) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Full-document parse: categories, teams, runners.

    runner_rank_in_team is sequential within each team (file order: line by line,
    left runner then right runner).
    """
    cats: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    runners: list[dict[str, Any]] = []

    cid: int | None = None
    tid: int | None = None
    nc = nt = 0
    order_in_team = 0

    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip() or line.startswith("==="):
            continue

        m = CAT.match(line.strip())
        if m:
            nc += 1
            cid, tid = nc, None
            cats.append({"category_id": cid, "category_name": m.group(1).strip()})
            continue

        tm = parse_team_line(line)
        if tm and cid is not None:
            nt += 1
            tid = nt
            order_in_team = 0
            teams.append(
                {
                    "team_id": tid,
                    "category_id": cid,
                    **tm,
                }
            )
            continue

        if tid is None:
            continue

        for r in parse_runner_line(line):
            order_in_team += 1
            runners.append(
                {
                    "team_id": tid,
                    "runner_rank_in_team": order_in_team,
                    "runner_time": r["runner_time"],
                    "runner_seconds": r["runner_seconds"],
                    "runner_name": r["runner_name"],
                    "runner_bib": r["runner_bib"],
                }
            )

    return cats, teams, runners


def extract_text_from_teams_html(html: str) -> str:
    """
    Sportstats embeds the plain-text report in one or many <pre> blocks; concatenate
    them in order so every category section is included.
    """
    blocks = re.findall(r"<pre[^>]*>(.*?)</pre>", html, flags=re.DOTALL | re.IGNORECASE)
    if not blocks:
        return html
    return "\n".join(blocks)
