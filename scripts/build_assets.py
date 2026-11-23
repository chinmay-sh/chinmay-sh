"""Pull live GitHub data and redraw the profile's telemetry SVGs and charts.

Stdlib only. Run locally or from .github/workflows/telemetry.yml.
Set GITHUB_TOKEN to avoid the 60 requests/hour anonymous limit.
"""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = "chinmay-sh"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
EXTRA_REPOS = ["akashicode/kash"]  # my repos that live outside the user account
FEATURED = [  # (repo, icon, blurb) shown as mission cards; the blurb wins over the GitHub description
    ("kash", "🧬", "Compiles a folder of documents into one self-contained AI agent. Hybrid retrieval, recall@5 of 1.00."),
    ("flareRAG", "🔭", "Serverless RAG on Cloudflare Workers: embed, search, rerank, served to any MCP client. Runs at $0."),
    ("livekit-voice-agent", "📞", "A multilingual voice agent that picks up the phone and briefs you on my work."),
    ("finetuning-showdown", "⚖️", "Full FT vs LoRA vs QLoRA vs prefix-tuning on Qwen2. LoRA kept 94% quality on 1.75% of params."),
    ("frostbite-30m", "❄️", "A 29M-param edge model mixing attention with liquid neural dynamics and a learned compute router."),
    ("maya-tts-modal", "🔊", "Open-weights TTS on serverless GPUs as a remote MCP tool, benchmarked from cold start to warm."),
    ("opencode-bridge-mcp", "🌉", "Agent-to-agent delegation: Claude Code hands coding tasks to OpenCode over MCP."),
    ("satTrack", "🛰️", "Live satellite tracking on a 2D map. Where the orbit began."),
]
LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "Jupyter Notebook": "#DA5B0B", "Vue": "#41b883", "HTML": "#e34c26",
    "CSS": "#663399", "Assembly": "#6E4C13", "Java": "#b07219", "Go": "#00ADD8", "MATLAB": "#e16737",
    "Shell": "#89e051", "C++": "#f34b7d", "Dart": "#00B4AB",
}
BG, PANEL, LINE = "#0a0e17", "#0f1524", "#1f2a44"
TEXT, DIM, ACCENT, CYAN, AMBER = "#e5e7eb", "#7c869c", "#b392f0", "#5eead4", "#fbbf24"
FONT = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'
STYLE = f"""<style>
text {{ font-family: {FONT}; }}
.grow {{ transform-box: fill-box; transform-origin: left; animation: grow 1.4s cubic-bezier(.2,.8,.2,1) both; }}
.up {{ transform-box: fill-box; transform-origin: bottom; animation: up 1.4s cubic-bezier(.2,.8,.2,1) both; }}
.fade {{ animation: fade 1s ease-out both; }}
.pulse {{ animation: pulse 2s ease-in-out infinite; }}
@keyframes grow {{ from {{ transform: scaleX(0); }} }}
@keyframes up {{ from {{ transform: scaleY(0); }} }}
@keyframes fade {{ from {{ opacity: 0; }} }}
@keyframes pulse {{ 50% {{ opacity: .3; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-telemetry"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            mine = [r for r in repos if not r["fork"] and r["name"] != USER]
            return mine + [get(f"https://api.github.com/repos/{full}") for full in EXTRA_REPOS]
        page += 1


def parse_date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def svg(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">'
            f"<title>{escape(title)}</title>{STYLE}"
            f'<rect width="{w}" height="{h}" rx="16" fill="{BG}"/>'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="16" fill="none" stroke="{LINE}"/>{body}</svg>')


def panel(x, y, w, h, label):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{PANEL}" stroke="{LINE}"/>'
            f'<rect x="{x}" y="{y + 18}" width="3" height="14" fill="{ACCENT}"/>'
            f'<text x="{x + 16}" y="{y + 30}" fill="{DIM}" font-size="13" letter-spacing="3">{escape(label)}</text>')


def wrap(text, width, lines):
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: width - 1].rstrip() + "…"
    return [l for l in out if l]


def telemetry(repos, now):
    stars = sum(r["stargazers_count"] for r in repos)
    langs = Counter(r["language"] for r in repos if r["language"])
    years = Counter(parse_date(r["created_at"]).year for r in repos)
    first = min(parse_date(r["created_at"]) for r in repos)
    active = sum((now - parse_date(r["pushed_at"])).days <= 90 for r in repos)
    w, h = 1200, 560
    b = []

    tiles = [("MISSIONS", len(repos), ACCENT), ("STARS EARNED", stars, AMBER),
             ("ACTIVE · 90D", active, "#22c55e"), ("YEARS IN ORBIT", now.year - first.year, CYAN)]
    for i, (label, val, col) in enumerate(tiles):
        x = 24 + i * 292
        b.append(f'<g class="fade" style="animation-delay:{i * .12}s">'
                 f'<rect x="{x}" y="24" width="276" height="104" rx="12" fill="{PANEL}" stroke="{LINE}"/>'
                 f'<text x="{x + 20}" y="54" fill="{DIM}" font-size="13" letter-spacing="3">{label}</text>'
                 f'<text x="{x + 20}" y="106" fill="{col}" font-size="44" font-weight="700">{val}</text>'
                 f'<rect x="{x + 20}" y="114" width="236" height="2" fill="{col}" opacity=".25"/></g>')

    # propulsion mix: repos per primary language
    b.append(panel(24, 148, 560, 300, "PROPULSION MIX · REPOS BY LANGUAGE"))
    top = langs.most_common(7)
    peak = top[0][1] if top else 1
    for i, (lang, n) in enumerate(top):
        y = 196 + i * 34
        bw = max(6, 330 * n / peak)
        col = LANG_COLORS.get(lang, ACCENT)
        b.append(f'<text x="44" y="{y + 15}" fill="{TEXT}" font-size="14">{escape(lang[:16])}</text>'
                 f'<rect x="196" y="{y + 2}" width="330" height="16" rx="4" fill="#141c2f"/>'
                 f'<rect class="grow" style="animation-delay:{i * .1}s" x="196" y="{y + 2}" width="{bw:.1f}" height="16" rx="4" fill="{col}"/>'
                 f'<text x="540" y="{y + 15}" fill="{DIM}" font-size="13">{n}</text>')

    # launch cadence: repos created per year
    b.append(panel(600, 148, 576, 300, "LAUNCH CADENCE · NEW REPOS PER YEAR"))
    span = list(range(first.year, now.year + 1))
    ypeak = max(years.values())
    slot = 520 / len(span)
    bar = min(44, slot * .6)
    for i, yr in enumerate(span):
        n = years.get(yr, 0)
        bh = 180 * n / ypeak
        cx = 628 + slot * i + slot / 2
        b.append(f'<rect x="{cx - bar / 2:.1f}" y="{400 - bh:.1f}" width="{bar:.1f}" height="{max(bh, 2):.1f}" rx="4" '
                 f'fill="{CYAN if yr == now.year else ACCENT}" class="up" style="animation-delay:{i * .08}s"/>'
                 f'<text x="{cx:.1f}" y="{392 - bh:.1f}" fill="{TEXT}" font-size="12" text-anchor="middle">{n or ""}</text>'
                 f'<text x="{cx:.1f}" y="424" fill="{DIM}" font-size="12" text-anchor="middle">{str(yr)[2:]}\'</text>')
    b.append(f'<path d="M620 400H1156" stroke="{LINE}"/>')

    # last burns
    b.append(f'<rect x="24" y="464" width="1152" height="72" rx="12" fill="{PANEL}" stroke="{LINE}"/>')
    recent = sorted(repos, key=lambda r: r["pushed_at"], reverse=True)[:4]
    b.append(f'<circle class="pulse" cx="48" cy="500" r="6" fill="#22c55e"/>'
             f'<text x="64" y="505" fill="{DIM}" font-size="13" letter-spacing="3">LAST BURNS</text>')
    for i, r in enumerate(recent):
        days = (now - parse_date(r["pushed_at"])).days
        when = "today" if days == 0 else f"{days}d ago"
        x = 200 + i * 244
        b.append(f'<text x="{x}" y="497" fill="{TEXT}" font-size="14">{escape(r["name"][:24])}</text>'
                 f'<text x="{x}" y="518" fill="{DIM}" font-size="12">{when}</text>')
    b.append(f'<text x="1160" y="552" fill="#4b5675" font-size="10" text-anchor="end">LAST SYNC {now:%Y-%m-%d %H:%M} UTC</text>')
    return svg(w, h, "Live telemetry: repositories, languages and launch cadence", "".join(b))


def card(repo, icon, blurb, now):
    days = (now - parse_date(repo["pushed_at"])).days
    status, col = ("ACTIVE", "#22c55e") if days <= 90 else ("IN ORBIT", CYAN) if days <= 730 else ("DORMANT", DIM)
    lang = repo["language"] or "—"
    lines = wrap(blurb or repo["description"] or "", 56, 2)
    desc = "".join(f'<text x="24" y="{86 + i * 22}" fill="{DIM}" font-size="14">{escape(l)}</text>' for i, l in enumerate(lines))
    body = (f'<text x="24" y="44" fill="{TEXT}" font-size="20" font-weight="700">{icon} {escape(repo["name"])}</text>'
            f'<rect x="{560 - 18 - len(status) * 9 - 28}" y="24" width="{len(status) * 9 + 28}" height="24" rx="12" fill="none" stroke="{col}"/>'
            f'<circle class="pulse" cx="{560 - 18 - len(status) * 9 - 14}" cy="36" r="4" fill="{col}"/>'
            f'<text x="{560 - 26}" y="41" fill="{col}" font-size="12" text-anchor="end" letter-spacing="1">{status}</text>'
            f'{desc}'
            f'<path d="M24 142H536" stroke="{LINE}"/>'
            f'<circle cx="30" cy="164" r="6" fill="{LANG_COLORS.get(lang, ACCENT)}"/>'
            f'<text x="44" y="169" fill="{TEXT}" font-size="13">{escape(lang)}</text>'
            f'<text x="240" y="169" fill="{AMBER}" font-size="13">★ {repo["stargazers_count"]}</text>'
            f'<text x="536" y="169" fill="{DIM}" font-size="12" text-anchor="end">LAST BURN {parse_date(repo["pushed_at"]):%Y-%m-%d}</text>')
    return svg(560, 190, f'{repo["name"]}: {blurb}', body)


def update_readme(repos):
    langs = Counter(r["language"] for r in repos if r["language"]).most_common(6)
    pie = "\n".join(f'    "{l}" : {n}' for l, n in langs)
    block = f"""```mermaid
pie showData
    title Propulsion mix (repos by primary language)
{pie}
```"""
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    new = re.sub(r"(<!-- CHART:START -->).*?(<!-- CHART:END -->)", lambda m: f"{m[1]}\n{block}\n{m[2]}", text, flags=re.S)
    assert new != text or block in text, "CHART markers missing from README"
    readme.write_text(new, encoding="utf-8", newline="\n")


def main():
    now = datetime.now(timezone.utc)
    repos = fetch_repos()
    by_name = {r["name"]: r for r in repos}
    out = {"telemetry.svg": telemetry(repos, now)}
    for name, icon, blurb in FEATURED:
        if name in by_name:
            out[f"missions/{name}.svg"] = card(by_name[name], icon, blurb, now)
    for rel, content in out.items():
        ET.fromstring(content)  # self-check: fail the run rather than commit broken XML
        path = ASSETS / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    update_readme(repos)
    print(f"wrote {len(out)} svgs from {len(repos)} repos")


if __name__ == "__main__":
    assert wrap("a b c", 3, 2) == ["a b", "c"] and len(wrap("x " * 100, 10, 2)) == 2
    main()
