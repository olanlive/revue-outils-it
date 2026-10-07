#!/usr/bin/env python3
"""Build static HTML discovery feed for revue-outils-it into docs/ (+ COVERED.md).

Même logique que olanlive/revue-oss-3d : un fil plat de découvertes,
une page unique docs/index.html (plus récent en haut) + pages de tags + flux RSS.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "discoveries.json"
DOCS = ROOT / "docs"
TAGS_DIR = DOCS / "tags"
COVERED = ROOT / "COVERED.md"
SITE_URL = "https://olanlive.github.io/revue-outils-it/"
FEED_MAX = 100
SUMMARY_MAX = 280

SITE_TITLE = "Pépites Outils IT"
SITE_DESC = "Veille outils IT pour studio 3D — render farm, stockage, sauvegarde, déploiement, réseau, sécurité — open source d’abord — tous les 2 jours."

CSS = """\
:root {
  --bg: #17110a;
  --surface: #231a0f;
  --border: #4d3a20;
  --text: #f6ede1;
  --muted: #c9b393;
  --accent: #ffb347;
  --accent-hover: #ffd18f;
  --tag-bg: #35270f;
  --tag-text: #ffdca8;
  --tag-hover-bg: #4a3612;
  --radius: 8px;
  --font: system-ui, -apple-system, "Segoe UI", Roboto, Ubuntu, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --max: 720px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
}
a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); text-decoration: underline; }
/* Liens dans du texte courant : soulignés (ne pas reposer sur la seule couleur, WCAG 1.4.1) */
.discovery .source a, footer.site a { text-decoration: underline; text-underline-offset: 2px; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.wrap {
  max-width: var(--max);
  margin: 0 auto;
  padding: 1.25rem 1.25rem 3rem;
}
header.site {
  border-bottom: 1px solid var(--border);
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
}
header.site h1 {
  margin: 0 0 0.35rem;
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
header.site h1 a { color: var(--text); text-decoration: none; }
header.site h1 a:hover { color: var(--accent); }
.tagline { color: var(--muted); margin: 0; font-size: 0.95rem; }
nav.crumbs {
  font-size: 0.85rem;
  color: var(--muted);
  margin-bottom: 1.5rem;
}
nav.crumbs a { color: var(--muted); }
nav.crumbs a:hover { color: var(--accent); }
nav.crumbs span.sep { margin: 0 0.35rem; }
.meta { color: var(--muted); font-size: 0.9rem; }
.discovery {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.15rem 1.25rem;
  margin-bottom: 1rem;
}
.discovery h3 {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
}
.discovery h3 a { color: var(--text); }
.discovery h3 a:hover { color: var(--accent); }
.discovery .summary {
  margin: 0 0 0.75rem;
  color: var(--text);
  font-size: 0.95rem;
}
.discovery .source {
  margin: 0 0 0.75rem;
  color: var(--muted);
  font-size: 0.85rem;
}
.tags { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.tag {
  display: inline-block;
  background: var(--tag-bg);
  color: var(--tag-text);
  font-size: 0.75rem;
  font-family: var(--mono);
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  text-decoration: none;
}
.tag:hover {
  background: var(--tag-hover-bg);
  color: var(--accent-hover);
  text-decoration: none;
  border-color: var(--accent);
}
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 1rem 0 2rem;
  align-items: center;
}
h2.section {
  font-size: 1.25rem;
  margin: 0 0 1rem;
  font-weight: 600;
}
.date-label {
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0 0 0.35rem;
}
/* Séparateur de date (page d’accueil) : grand espace au-dessus, titre lisible, fin trait ambre */
h2.day-sep {
  margin: 2.75rem 0 1rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--accent);
  color: var(--text);
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}
h2.day-sep.first { margin-top: 1.25rem; }
footer.site {
  margin-top: 3rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.85rem;
}
.empty { color: var(--muted); }
code { font-family: var(--mono); font-size: 0.9em; }
@media (max-width: 520px) {
  .wrap { padding: 1rem 1rem 2.5rem; }
  header.site h1 { font-size: 1.35rem; }
}
"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def format_date_fr(iso: str) -> str:
    dt = datetime.strptime(iso, "%Y-%m-%d")
    months = [
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    return f"{dt.day} {months[dt.month]} {dt.year}"


def format_day_fr(iso: str) -> str:
    """« Jeudi 8 octobre 2026 » — noms français codés en dur (indépendant de la locale)."""
    dt = datetime.strptime(iso, "%Y-%m-%d")
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return f"{days[dt.weekday()]} {format_date_fr(iso)}"


def day_separator_html(iso: str, *, first: bool) -> str:
    cls = "day-sep first" if first else "day-sep"
    return (
        f'\n<h2 class="{cls}" id="jour-{esc(iso)}">'
        f'<time datetime="{esc(iso)}">{esc(format_day_fr(iso))}</time></h2>\n'
    )


def page(
    title: str,
    body: str,
    *,
    depth: int = 0,
    crumbs: list[tuple[str, str]] | None = None,
) -> str:
    """depth: 0 = docs/, 1 = docs/tags/."""
    prefix = "../" * depth
    crumb_html = ""
    if crumbs:
        parts = []
        for i, (label, href) in enumerate(crumbs):
            if i < len(crumbs) - 1 and href:
                parts.append(f'<a href="{esc(href)}">{esc(label)}</a>')
            else:
                parts.append(f"<span>{esc(label)}</span>")
        crumb_html = (
            '<nav class="crumbs" aria-label="Fil d’Ariane">'
            + '<span class="sep" aria-hidden="true"> / </span>'.join(parts)
            + "</nav>"
        )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(SITE_DESC)}">
  <link rel="stylesheet" href="{prefix}style.css">
  <link rel="alternate" type="application/rss+xml" title="{esc(SITE_TITLE)}" href="{SITE_URL}feed.xml">
</head>
<body>
  <div class="wrap">
    <header class="site">
      <h1><a href="{prefix}index.html">{esc(SITE_TITLE)}</a></h1>
      <p class="tagline">{esc(SITE_DESC)}</p>
    </header>
    {crumb_html}
    {body}
    <footer class="site">
      <p>Veille outils IT pour studio 3D · open source d’abord (gratuit / payant signalé) · tous les 2 jours</p>
      <p><a href="https://github.com/olanlive/revue-outils-it">Code source sur GitHub</a>
         · <a href="{prefix}tags/index.html">Tous les tags</a>
         · <a href="{prefix}feed.xml">Flux RSS</a></p>
    </footer>
  </div>
</body>
</html>
"""


def tags_html(tags: list[str], *, tags_base: str) -> str:
    if not tags:
        return ""
    links = [
        f'<a class="tag" href="{tags_base}{esc(t)}.html">#{esc(t)}</a>'
        for t in tags
    ]
    return '<div class="tags">' + "".join(links) + "</div>"


def source_html(source) -> str:
    """source: {"label": str, "url": str?} or a plain string."""
    if not source:
        return ""
    if isinstance(source, str):
        return f'<p class="source">Trouvé via : {esc(source)}</p>'
    label = esc(source.get("label", ""))
    url = source.get("url")
    if url:
        label = f'<a href="{esc(url)}" rel="noopener" target="_blank">{label}</a>'
    return f'<p class="source">Trouvé via : {label}</p>'


def anchor_id(item: dict) -> str:
    """Ancre stable : AAAA-MM-JJ-nom-version (ex. 2026-10-07-gntoolkit-0-2-8)."""
    if item.get("id"):
        return item["id"]
    name = unicodedata.normalize("NFKD", item["name"]).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{item['date']}-{slug}"


def discovery_html(
    item: dict,
    *,
    tags_base: str,
    show_date: bool = True,
) -> str:
    date_bit = ""
    if show_date and item.get("date"):
        date_bit = (
            f'<p class="date-label"><time datetime="{esc(item["date"])}">'
            f"{esc(format_date_fr(item['date']))}</time></p>"
        )
    return f"""
<article class="discovery" id="{esc(anchor_id(item))}">
  {date_bit}
  <h3><a href="{esc(item['url'])}" rel="noopener" target="_blank">{esc(item['name'])}</a></h3>
  <p class="summary">{esc(item['summary'])}</p>
  {source_html(item.get('source'))}
  {tags_html(item.get('tags', []), tags_base=tags_base)}
</article>
"""


def write_feed(discoveries: list[dict]) -> None:
    """docs/feed.xml — RSS 2.0, un item par découverte (lien = ancre du bloc)."""
    paris = ZoneInfo("Europe/Paris")

    def x(s: str) -> str:
        return html.escape(s, quote=False)

    items = []
    for d in discoveries[:FEED_MAX]:
        link = f"{SITE_URL}#{anchor_id(d)}"
        pub = datetime.strptime(d["date"], "%Y-%m-%d").replace(hour=9, tzinfo=paris)
        cats = "".join(f"\n      <category>{x(t)}</category>" for t in d.get("tags", []))
        items.append(f"""    <item>
      <title>{x(d['name'])}</title>
      <link>{x(link)}</link>
      <guid isPermaLink="true">{x(link)}</guid>
      <pubDate>{format_datetime(pub)}</pubDate>
      <description>{x(d['summary'])}</description>{cats}
    </item>""")
    last = discoveries[0]["date"] if discoveries else "1970-01-01"
    last_dt = datetime.strptime(last, "%Y-%m-%d").replace(hour=9, tzinfo=paris)
    feed = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{x(SITE_TITLE)}</title>
    <link>{SITE_URL}</link>
    <description>{x(SITE_DESC)}</description>
    <language>fr</language>
    <lastBuildDate>{format_datetime(last_dt)}</lastBuildDate>
    <atom:link href="{SITE_URL}feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (DOCS / "feed.xml").write_text(feed, encoding="utf-8")


def build() -> None:
    discoveries = json.loads(DATA.read_text(encoding="utf-8"))
    discoveries = sorted(discoveries, key=lambda d: d["date"], reverse=True)
    for d in discoveries:
        if len(d["summary"]) > SUMMARY_MAX:
            print(f"ATTENTION : résumé trop long ({len(d['summary'])} > {SUMMARY_MAX} car.) : {d['name']}")

    if DOCS.exists():
        for child in DOCS.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    DOCS.mkdir(parents=True, exist_ok=True)
    TAGS_DIR.mkdir(parents=True, exist_ok=True)

    (DOCS / "style.css").write_text(CSS, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    by_tag: dict[str, list[dict]] = defaultdict(list)
    all_tags: set[str] = set()

    for item in discoveries:
        for tag in item.get("tags", []):
            all_tags.add(tag)
            by_tag[tag].append(item)

    feed_parts: list[str] = []
    prev_date = None
    for item in discoveries:
        if item["date"] != prev_date:
            feed_parts.append(day_separator_html(item["date"], first=prev_date is None))
            prev_date = item["date"]
        feed_parts.append(discovery_html(item, tags_base="tags/"))
    feed = "".join(feed_parts)
    tag_links = "".join(
        f'<a class="tag" href="tags/{esc(t)}.html">#{esc(t)}</a>'
        for t in sorted(all_tags)
    )
    n = len(discoveries)
    home_body = f"""
<section>
  <h2 class="section">Découvertes</h2>
  <p class="meta">{n} découverte{'s' if n != 1 else ''}</p>
  {feed if feed else '<p class="empty">Aucune découverte pour le moment.</p>'}
</section>
<section>
  <h2 class="section">Tags</h2>
  <div class="tag-cloud">{tag_links or '<span class="empty">—</span>'}</div>
</section>
"""
    (DOCS / "index.html").write_text(
        page(SITE_TITLE, home_body, depth=0), encoding="utf-8"
    )

    for tag in sorted(all_tags):
        entries = sorted(by_tag[tag], key=lambda e: e["date"], reverse=True)
        items_html = "".join(
            discovery_html(item, tags_base="./") for item in entries
        )
        body = f"""
<h2 class="section">Tag <code>#{esc(tag)}</code></h2>
<p class="meta">{len(entries)} découverte{'s' if len(entries) != 1 else ''}</p>
{items_html}
"""
        (TAGS_DIR / f"{tag}.html").write_text(
            page(
                f"#{tag} · {SITE_TITLE}",
                body,
                depth=1,
                crumbs=[
                    ("Accueil", "../index.html"),
                    ("Tags", "index.html"),
                    (f"#{tag}", ""),
                ],
            ),
            encoding="utf-8",
        )

    cloud_parts = []
    for t in sorted(all_tags):
        cloud_parts.append(
            f'<a class="tag" href="{esc(t)}.html">#{esc(t)}</a>'
            f'<span class="meta">({len(by_tag[t])})</span>'
        )
    tags_index_body = f"""
<h2 class="section">Tous les tags</h2>
<div class="tag-cloud">{' '.join(cloud_parts) or '<span class="empty">—</span>'}</div>
"""
    (TAGS_DIR / "index.html").write_text(
        page(
            f"Tags · {SITE_TITLE}",
            tags_index_body,
            depth=1,
            crumbs=[("Accueil", "../index.html"), ("Tags", "")],
        ),
        encoding="utf-8",
    )

    write_feed(discoveries)

    rows = "\n".join(
        f"| {d['date']} | {d['name']} | {', '.join(d.get('tags', []))} | {d['url']} | {SITE_URL}#{anchor_id(d)} |"
        for d in discoveries
    )
    COVERED.write_text(
        "# Outils déjà couverts\n\n"
        "Fichier **généré** par `scripts/build.py` depuis `data/discoveries.json` — ne pas éditer à la main.\n"
        "Avant d’ajouter une découverte : ne reprendre un outil déjà listé que s’il y a une nouvelle version "
        "majeure ou une actu forte (et le dire dans le résumé : « déjà vu le … »).\n\n"
        "Hors périmètre : 3D/VFX créatifs (voir `olanlive/revue-oss-3d`) et audio/vidéo (voir `olanlive/revue-audio-video`).\n\n"
        "| Date | Découverte | Tags | Lien officiel | Ancre sur le site |\n|---|---|---|---|---|\n"
        + rows + "\n",
        encoding="utf-8",
    )

    print(f"Built {len(discoveries)} discovery(ies), {len(all_tags)} tag(s) → {DOCS}")


if __name__ == "__main__":
    build()
