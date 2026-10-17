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
SITE_DESC = "Veille outils IT pour studio 3D — render farm, stockage, sauvegarde, déploiement, réseau, sécurité — open source d’abord."

SITE_TITLE_EN = "IT Tools Gems"
SITE_DESC_EN = "IT tools watch for a 3D studio — render farm, storage, backup, deployment, network, security — open source first."
FOOTER_EN = "IT tools watch for a 3D studio · open source first (free / paid noted)"

CSS = """\
:root {
  --bg: #0f1419;
  --surface: #1a2332;
  --border: #2d3a4f;
  --text: #e7ecf3;
  --muted: #9aa8bc;
  --accent: #ffb347;
  --accent-hover: #ffd18f;
  --tag-bg: #243044;
  --tag-text: #f5d7a8;
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
  background: #2e4058;
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
.day-sep {
  margin: 2.75rem 0 1rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--accent);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text);
}
.day-sep:first-of-type { margin-top: 1.5rem; }
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


# --- Pépites : filtres par tag, partage X, latest.json (ne pas supprimer) ---
from urllib.parse import quote as _pq

PEPITES_HASHTAGS = "#opensource #sysadmin"
PEPITES_TOP_TAGS = 14

PEPITES_CSS = """
.tag-filter { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.75rem 0 1.25rem; }
.tag-filter .tag { cursor: pointer; font: inherit; font-size: 0.75rem; font-family: var(--mono); }
.tag-filter .tag[aria-pressed="true"] { background: var(--accent); color: var(--bg, #fff); border-color: var(--accent); }
.tag-filter .tag-all, .tag-filter .tag-clear, .tag-filter .tag-back { font-family: var(--font); }
.tag-filter .tag-clear { background: var(--accent); color: var(--bg, #fff); border-color: var(--accent); }
.tag-filter { scroll-margin-top: 4rem; }
.tag-filter[data-home] { align-items: center; margin: 0.5rem 0 1rem; }
.tag-filter .tag-toggle { font-family: var(--font); font-size: 0.85rem; padding: 0.3rem 0.8rem; cursor: pointer; }
.tag-filter .tf-panel { flex-basis: 100%; display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.4rem; padding: 0.6rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius, 8px); max-height: 50vh; overflow-y: auto; }
.tag-filter .tf-n { opacity: 0.7; }
.share-x { margin: 0.6rem 0 0; font-size: 0.8rem; }
.share-x a { color: var(--muted); }
.share-x a:hover { color: var(--accent); }
.share-x .copy-btn { background: none; border: 0; padding: 0; font: inherit; color: var(--muted); cursor: pointer; }
.share-x .copy-btn:hover { color: var(--accent); }
[hidden] { display: none !important; }
"""

PEPITES_FILTER_JS = r"""
(function(){
  var bar=document.querySelector('.tag-filter[data-home]'); if(!bar) return;
  var tog=bar.querySelector('.tag-toggle'), panel=bar.querySelector('.tf-panel'), clr=bar.querySelector('.tag-clear');
  var btns=[].slice.call(panel.querySelectorAll('[data-tag]'));
  function tagsOf(a){var d=a.querySelector('[data-tags]');return d?d.getAttribute('data-tags').split(' '):[];}
  function open(o){ panel.hidden=!o; tog.setAttribute('aria-expanded',String(o)); tog.textContent=o?'Filtrer ▴':'Filtrer ▾'; }
  function apply(){
    var m=location.hash.match(/^#tag=(.+)$/), t=m?decodeURIComponent(m[1]):'';
    btns.forEach(function(b){b.setAttribute('aria-pressed', String(b.getAttribute('data-tag')===t));});
    clr.hidden=!t; clr.textContent=t+' ✕'; clr.setAttribute('aria-label','Retirer le filtre '+t);
    var nodes=[].slice.call(document.querySelectorAll('.day-sep, article.discovery')), sep=null, seen=false;
    function close(){ if(sep) sep.hidden=!seen; }
    nodes.forEach(function(n){
      if(n.classList.contains('day-sep')){ close(); sep=n; seen=false; return; }
      var show=!t||tagsOf(n).indexOf(t)>=0; n.hidden=!show; if(show) seen=true;
    });
    close();
  }
  function setTag(t){ if(t) location.hash='tag='+encodeURIComponent(t); else history.replaceState(null,'',location.pathname+location.search); apply(); }
  tog.addEventListener('click',function(e){ e.preventDefault(); open(panel.hidden); });
  clr.addEventListener('click',function(){ setTag(''); });
  btns.forEach(function(b){ b.addEventListener('click',function(e){ e.preventDefault(); setTag(b.getAttribute('data-tag')); open(false); tog.focus(); }); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&!panel.hidden){ open(false); tog.focus(); } });
  window.addEventListener('hashchange',apply); apply();
})();
"""

CSS += PEPITES_CSS


def _x_len(s: str) -> int:
    return sum(2 if ord(c) > 0x10FF else 1 for c in s)


def share_text(item: dict) -> str:
    head = "Pépite du jour 💎\n"
    tail = "\n" + item["url"] + "\n" + PEPITES_HASHTAGS
    fixed = _x_len(head) + 1 + 23 + 1 + _x_len(PEPITES_HASHTAGS)
    body = f"{item['name']} : {item['summary']}"
    if fixed + _x_len(body) > 280:
        while fixed + _x_len(body) + 1 > 280:
            body = body[:-1]
        body = body.rstrip(" ,;:.") + "…"
    return head + body + tail


def share_html(item: dict) -> str:
    text = share_text(item)
    href = "https://twitter.com/intent/tweet?text=" + _pq(text, safe="")
    tags = " ".join(item.get("tags", []))
    return (f'<p class="share-x" data-tags="{html.escape(tags, quote=True)}" data-text="{html.escape(text, quote=True)}">'
            f'<a class="share-btn" href="{html.escape(href, quote=True)}" rel="noopener" target="_blank" aria-label="Partager">Partager</a>'
            f' · <button type="button" class="copy-btn" hidden>Copier</button></p>')


PEPITES_SHARE_JS = r"""
(function(){
  [].forEach.call(document.querySelectorAll('.share-x .copy-btn'),function(b){ if(navigator.clipboard) b.hidden=false; });
  document.addEventListener('click',function(e){
    var t=e.target, p=t.closest&&t.closest('.share-x'); if(!p) return;
    var text=p.getAttribute('data-text');
    if(t.closest('.share-btn')){
      e.preventDefault();
      if(navigator.share){ navigator.share({text:text}).catch(function(){}); }
      else { window.open('https://twitter.com/intent/tweet?text='+encodeURIComponent(text),'_blank','noopener'); }
    } else if(t.closest('.copy-btn')){
      navigator.clipboard.writeText(text).then(function(){
        var b=t.closest('.copy-btn'); b.textContent='Copié ✓'; setTimeout(function(){ b.textContent='Copier'; },2000);
      }).catch(function(){});
    }
  });
})();
"""


def inject_share_js() -> None:
    for f in DOCS.rglob("*.html"):
        s = f.read_text(encoding="utf-8")
        if 'class="share-x"' in s and "PEPITES_SHARE" not in s:
            s = s.replace("</body>", "<script>/*PEPITES_SHARE*/" + PEPITES_SHARE_JS + "</script>\n</body>", 1)
            f.write_text(s, encoding="utf-8")


def filter_bar_html(discoveries: list) -> str:
    counts: dict = {}
    for d in discoveries:
        for t in d.get("tags", []):
            counts[t] = counts.get(t, 0) + 1
    order = sorted(counts, key=lambda t: (-counts[t], t))
    if not order:
        return ""
    btns = ['<a class="tag tag-all" href="#" data-tag="" aria-pressed="true">Tous</a>']
    for t in order:
        e = html.escape(t, quote=True)
        btns.append(f'<a class="tag" href="tags/{e}.html" data-tag="{e}" aria-pressed="false">{e} <span class="tf-n">({counts[t]})</span></a>')
    return ('<div class="tag-filter" data-home role="group" aria-label="Filtrer par tag">'
            '<a class="tag tag-toggle" href="tags/index.html" role="button" aria-expanded="false" aria-controls="tf-panel">Filtrer ▾</a>'
            '<button type="button" class="tag tag-clear" hidden></button>'
            '<div class="tf-panel" id="tf-panel" hidden>' + "".join(btns) + "</div>"
            f"</div><script>{PEPITES_FILTER_JS}</script>")


def fix_tag_pages(discoveries: list) -> None:
    """Pages tags/xxx.html : barre « ← Tous » + autres tags, tags des pépites vers l'accueil filtré."""
    import re as _re
    counts: dict = {}
    for d in discoveries:
        for t in d.get("tags", []):
            counts[t] = counts.get(t, 0) + 1
    order = sorted(counts, key=lambda t: (-counts[t], t))
    for t in order:
        f = DOCS / "tags" / f"{t}.html"
        if not f.exists():
            continue
        s = f.read_text(encoding="utf-8")
        links = ['<a class="tag tag-back" href="../index.html">← Tous</a>']
        for o in order:
            e = html.escape(o, quote=True)
            cur = ' aria-current="page" aria-pressed="true"' if o == t else ""
            links.append(f'<a class="tag" href="../index.html#tag={_pq(o, safe="")}"{cur}>#{e}</a>')
        bar = '<div class="tag-filter" aria-label="Changer de tag">' + "".join(links) + "</div>\n"
        s = s.replace('<h2 class="section">Tag <code>', bar + '<h2 class="section">Tag <code>', 1)
        def _art(m):
            return _re.sub(r'class="tag" href="(?:\./)?([^"/]+)\.html"',
                           lambda k: f'class="tag" href="../index.html#tag={_pq(html.unescape(k.group(1)), safe="")}"', m.group(0))
        s = _re.sub(r'<article class="discovery".*?</article>', _art, s, flags=_re.S)
        f.write_text(s, encoding="utf-8")


def write_latest(discoveries: list) -> None:
    fix_tag_pages(discoveries)
    inject_share_js()
    data = {}
    if discoveries:
        d = discoveries[0]
        data = {"date": d["date"], "anchor": anchor_id(d), "name": d["name"]}
    (DOCS / "latest.json").write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
# --- fin Pépites ---

# --- Pépites : version anglaise (ne pas supprimer) ---
_EN_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_EN_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

UI = {
    "fr": {
        "discoveries": "Découvertes",
        "empty": "Aucune découverte pour le moment.",
        "filter_open": "Filtrer ▾",
        "filter_close": "Filtrer ▴",
        "filter_by_tag": "Filtrer par tag",
        "all": "Tous",
        "all_back": "← Tous",
        "change_tag": "Changer de tag",
        "remove_filter": "Retirer le filtre",
        "share": "Partager",
        "copy": "Copier",
        "copied": "Copié ✓",
        "found_via": "Trouvé via :",
        "all_tags": "Tous les tags",
        "tags": "Tags",
        "home": "Accueil",
        "breadcrumb": "Fil d\u2019Ariane",
        "source_code": "Code source sur GitHub",
        "rss": "Flux RSS",
        "share_head": "Pépite du jour 💎\n",
        "count_one": "découverte",
        "count_many": "découvertes",
    },
    "en": {
        "discoveries": "Discoveries",
        "empty": "No discoveries yet.",
        "filter_open": "Filter ▾",
        "filter_close": "Filter ▴",
        "filter_by_tag": "Filter by tag",
        "all": "All",
        "all_back": "← All",
        "change_tag": "Change tag",
        "remove_filter": "Remove filter",
        "share": "Share",
        "copy": "Copy",
        "copied": "Copied ✓",
        "found_via": "Found via:",
        "all_tags": "All tags",
        "tags": "Tags",
        "home": "Home",
        "breadcrumb": "Breadcrumb",
        "source_code": "Source code on GitHub",
        "rss": "RSS feed",
        "share_head": "Gem of the day 💎\n",
        "count_one": "discovery",
        "count_many": "discoveries",
    },
}


def ui(lang: str, key: str) -> str:
    table = UI.get(lang) or UI["fr"]
    return table.get(key) or UI["fr"][key]


def tr_field(item: dict, key: str, lang: str) -> tuple[str, bool]:
    """Texte du champ, et True si le français est affiché en repli."""
    if lang == "en":
        val = item.get(key + "_en")
        if isinstance(val, str) and val.strip():
            return val, False
    return item[key], lang == "en"


def format_date_lang(iso: str, lang: str = "fr") -> str:
    if lang != "en":
        return format_date_fr(iso)
    dt = datetime.strptime(iso, "%Y-%m-%d")
    return f"{_EN_MONTHS[dt.month]} {dt.day}, {dt.year}"


def format_day_lang(iso: str, lang: str = "fr") -> str:
    if lang != "en":
        return format_day_fr(iso)
    dt = datetime.strptime(iso, "%Y-%m-%d")
    return f"{_EN_DAYS[dt.weekday()]}, {format_date_lang(iso, 'en')}"


def count_label(n: int, lang: str) -> str:
    word = ui(lang, "count_one" if n == 1 else "count_many")
    return f"{n} {word}"


def share_text_lang(item: dict, lang: str) -> str:
    if lang != "en":
        return share_text(item)
    head = ui("en", "share_head")
    tail = "\n" + item["url"] + "\n" + PEPITES_HASHTAGS
    fixed = _x_len(head) + 1 + 23 + 1 + _x_len(PEPITES_HASHTAGS)
    name, _fb = tr_field(item, "name", lang)
    summary, _fb2 = tr_field(item, "summary", lang)
    body = f"{name} : {summary}"
    if fixed + _x_len(body) > 280:
        while fixed + _x_len(body) + 1 > 280:
            body = body[:-1]
        body = body.rstrip(" ,;:.") + "…"
    return head + body + tail


def share_html_lang(item: dict, lang: str = "fr") -> str:
    if lang != "en":
        return share_html(item)
    text = share_text_lang(item, lang)
    href = "https://twitter.com/intent/tweet?text=" + _pq(text, safe="")
    tags = " ".join(item.get("tags", []))
    share = ui(lang, "share")
    copy = ui(lang, "copy")
    return (f'<p class="share-x" data-tags="{html.escape(tags, quote=True)}" data-text="{html.escape(text, quote=True)}">'
            f'<a class="share-btn" href="{html.escape(href, quote=True)}" rel="noopener" target="_blank" aria-label="{html.escape(share)}">{html.escape(share)}</a>'
            f' · <button type="button" class="copy-btn" hidden>{html.escape(copy)}</button></p>')


def _filter_js(lang: str) -> str:
    if lang != "en":
        return PEPITES_FILTER_JS
    return (PEPITES_FILTER_JS
            .replace("Filtrer ▴", ui("en", "filter_close"))
            .replace("Filtrer ▾", ui("en", "filter_open"))
            .replace("Retirer le filtre ", ui("en", "remove_filter") + " "))


def _share_js(lang: str) -> str:
    if lang != "en":
        return PEPITES_SHARE_JS
    return (PEPITES_SHARE_JS
            .replace("Copié ✓", ui("en", "copied"))
            .replace("Copier", ui("en", "copy")))


def filter_bar_lang(discoveries: list, lang: str = "fr") -> str:
    if lang != "en":
        return filter_bar_html(discoveries)
    counts: dict = {}
    for d in discoveries:
        for t in d.get("tags", []):
            counts[t] = counts.get(t, 0) + 1
    order = sorted(counts, key=lambda t: (-counts[t], t))
    if not order:
        return ""
    btns = [f'<a class="tag tag-all" href="#" data-tag="" aria-pressed="true">{html.escape(ui(lang, "all"))}</a>']
    for t in order:
        e = html.escape(t, quote=True)
        btns.append(
            f'<a class="tag" href="tags/{e}.html" data-tag="{e}" aria-pressed="false">{e} '
            f'<span class="tf-n">({counts[t]})</span></a>'
        )
    return ('<div class="tag-filter" data-home role="group" aria-label="' + html.escape(ui(lang, "filter_by_tag")) + '">'
            '<a class="tag tag-toggle" href="tags/index.html" role="button" aria-expanded="false" aria-controls="tf-panel">'
            + html.escape(ui(lang, "filter_open")) + '</a>'
            '<button type="button" class="tag tag-clear" hidden></button>'
            '<div class="tf-panel" id="tf-panel" hidden>' + "".join(btns) + "</div>"
            f"</div><script>{_filter_js(lang)}</script>")


def source_html_lang(source, lang: str = "fr") -> str:
    if lang != "en":
        return source_html(source)
    if not source:
        return ""
    found = ui("en", "found_via")
    if isinstance(source, str):
        return f'<p class="source">{esc(found)} <span lang="fr">{esc(source)}</span></p>'
    label_en = source.get("label_en")
    fallback = not (isinstance(label_en, str) and label_en.strip())
    label_text = source.get("label", "") if fallback else label_en
    label = esc(label_text)
    lang_attr = ' lang="fr"' if fallback else ""
    url = source.get("url")
    if url:
        inner = f'<a href="{esc(url)}" rel="noopener" target="_blank"{lang_attr}>{label}</a>'
    elif fallback:
        inner = f'<span{lang_attr}>{label}</span>'
    else:
        inner = label
    return f'<p class="source">{esc(found)} {inner}</p>'


def _discovery_en(item: dict, *, show_date: bool = True) -> str:
    name, name_fb = tr_field(item, "name", "en")
    summary, sum_fb = tr_field(item, "summary", "en")
    name_attr = ' lang="fr"' if name_fb else ""
    sum_attr = ' lang="fr"' if sum_fb else ""
    date_bit = ""
    if show_date and item.get("date"):
        date_bit = (
            f'<p class="date-label"><time datetime="{esc(item["date"])}">'
            f"{esc(format_date_lang(item['date'], 'en'))}</time></p>"
        )
    return f"""
<article class="discovery" id="{esc(anchor_id(item))}">
  {date_bit}
  <h3><a href="{esc(item['url'])}" rel="noopener" target="_blank"{name_attr}>{esc(name)}</a></h3>
  <p class="summary"{sum_attr}>{esc(summary)}</p>
  {source_html(item.get('source'), lang="en")}
  {share_html_lang(item, "en")}
</article>
"""


def _page_en(
    title: str,
    body: str,
    *,
    prefix: str,
    crumb_html: str,
    fr_href: str,
    en_href: str,
    github_href: str,
    theme_color: str = "",
) -> str:
    css_prefix = "../" + prefix
    theme = f'  <meta name="theme-color" content="{esc(theme_color)}">\n' if theme_color else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
{theme}  <title>{esc(title)}</title>
  <meta name="description" content="{esc(SITE_DESC_EN)}">
  <link rel="stylesheet" href="{css_prefix}style.css">
  <link rel="alternate" type="application/rss+xml" title="{esc(SITE_TITLE_EN)}" href="{SITE_URL}en/feed.xml">
  <link rel="alternate" hreflang="fr" href="{esc(fr_href)}">
  <link rel="alternate" hreflang="en" href="{esc(en_href)}">
<script src="https://olanlive.github.io/pepites/nav.js?v=3" defer></script>
</head>
<body>
  <div class="wrap">
    <header class="site">
      <h1><a href="{prefix}index.html">{esc(SITE_TITLE_EN)}</a></h1>
      <p class="tagline">{esc(SITE_DESC_EN)}</p>
    </header>
    {crumb_html}
    {body}
    <footer class="site">
      <p>{esc(FOOTER_EN)}</p>
      <p><a href="{esc(github_href)}">{esc(ui("en", "source_code"))}</a>
         · <a href="{prefix}tags/index.html">{esc(ui("en", "all_tags"))}</a>
         · <a href="{prefix}feed.xml">{esc(ui("en", "rss"))}</a></p>
    </footer>
  </div>
</body>
</html>
"""


def fix_tag_pages_lang(discoveries: list, lang: str, docs: Path) -> None:
    if lang != "en":
        return
    counts: dict = {}
    for d in discoveries:
        for t in d.get("tags", []):
            counts[t] = counts.get(t, 0) + 1
    order = sorted(counts, key=lambda t: (-counts[t], t))
    tags_dir = docs / "tags"
    for t in order:
        f = tags_dir / f"{t}.html"
        if not f.exists():
            continue
        s = f.read_text(encoding="utf-8")
        links = [f'<a class="tag tag-back" href="../index.html">{html.escape(ui(lang, "all_back"))}</a>']
        for o in order:
            e = html.escape(o, quote=True)
            cur = ' aria-current="page" aria-pressed="true"' if o == t else ""
            links.append(f'<a class="tag" href="../index.html#tag={_pq(o, safe="")}"{cur}>#{e}</a>')
        bar = '<div class="tag-filter" aria-label="' + html.escape(ui(lang, "change_tag")) + '">' + "".join(links) + "</div>\n"
        s = s.replace('<h2 class="section">Tag <code>', bar + '<h2 class="section">Tag <code>', 1)

        def _art(m, _pq=_pq):
            return re.sub(
                r'class="tag" href="(?:\./)?([^"/]+)\.html"',
                lambda k: f'class="tag" href="../index.html#tag={_pq(html.unescape(k.group(1)), safe="")}"',
                m.group(0),
            )

        s = re.sub(r'<article class="discovery".*?</article>', _art, s, flags=re.S)
        f.write_text(s, encoding="utf-8")


def inject_share_js_lang(lang: str, docs: Path) -> None:
    if lang != "en":
        return
    js = _share_js(lang)
    for f in docs.rglob("*.html"):
        s = f.read_text(encoding="utf-8")
        if 'class="share-x"' in s and "PEPITES_SHARE" not in s:
            s = s.replace("</body>", "<script>/*PEPITES_SHARE*/" + js + "</script>\n</body>", 1)
            f.write_text(s, encoding="utf-8")


def feed_html_lang(discoveries: list, *, tags_base: str, lang: str) -> str:
    day_feed = globals().get("day_feed_html")
    if day_feed is not None:
        return day_feed(discoveries, tags_base=tags_base, lang=lang)
    day_sep = globals().get("day_separator_html")
    parts: list[str] = []
    prev = None
    for item in discoveries:
        day = item.get("date")
        if day and day != prev:
            if day_sep is not None:
                parts.append(day_sep(day, first=prev is None, lang=lang))
            else:
                parts.append(
                    f'<h3 class="day-sep" id="jour-{esc(day)}">{esc(format_day_lang(day, lang))}</h3>'
                )
            prev = day
        parts.append(discovery_html(item, tags_base=tags_base, lang=lang))
    return "".join(parts)


def warn_summaries_en(discoveries: list) -> None:
    for d in discoveries:
        s = d.get("summary_en")
        if isinstance(s, str) and len(s) > SUMMARY_MAX:
            print(f"ATTENTION : résumé trop long ({len(s)} > {SUMMARY_MAX} car.) : {d['name']}")


def write_feed_en(discoveries: list) -> None:
    """docs/en/feed.xml — même forme que le flux FR, textes anglais (repli FR)."""
    paris = ZoneInfo("Europe/Paris")
    minute = int(globals().get("FEED_MINUTE", 0))

    def x(s: str) -> str:
        return html.escape(s, quote=False)

    items = []
    for d in discoveries[:FEED_MAX]:
        link = f"{SITE_URL}en/#{anchor_id(d)}"
        pub = datetime.strptime(d["date"], "%Y-%m-%d").replace(hour=9, minute=minute, tzinfo=paris)
        name, name_fb = tr_field(d, "name", "en")
        summary, sum_fb = tr_field(d, "summary", "en")
        name_attr = ' xml:lang="fr"' if name_fb else ""
        sum_attr = ' xml:lang="fr"' if sum_fb else ""
        cats = "".join(f"\n      <category>{x(t)}</category>" for t in d.get("tags", []))
        items.append(f"""    <item>
      <title{name_attr}>{x(name)}</title>
      <link>{x(link)}</link>
      <guid isPermaLink="true">{x(link)}</guid>
      <pubDate>{format_datetime(pub)}</pubDate>
      <description{sum_attr}>{x(summary)}</description>{cats}
    </item>""")
    last = discoveries[0]["date"] if discoveries else "1970-01-01"
    last_dt = datetime.strptime(last, "%Y-%m-%d").replace(hour=9, minute=minute, tzinfo=paris)
    feed = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{x(SITE_TITLE_EN)}</title>
    <link>{SITE_URL}en/</link>
    <description>{x(SITE_DESC_EN)}</description>
    <language>en</language>
    <lastBuildDate>{format_datetime(last_dt)}</lastBuildDate>
    <atom:link href="{SITE_URL}en/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (DOCS / "en" / "feed.xml").write_text(feed, encoding="utf-8")


def build_lang(lang: str, discoveries: list) -> None:
    if lang != "en":
        return
    warn_summaries_en(discoveries)
    en_docs = DOCS / "en"
    en_tags = en_docs / "tags"
    en_tags.mkdir(parents=True, exist_ok=True)

    by_tag: dict[str, list] = defaultdict(list)
    all_tags: set[str] = set()
    for item in discoveries:
        for tag in item.get("tags", []):
            all_tags.add(tag)
            by_tag[tag].append(item)

    feed = feed_html_lang(discoveries, tags_base="tags/", lang=lang)
    n = len(discoveries)
    home_body = f"""
<section>
  <h2 class="section">{ui(lang, "discoveries")}</h2>
  <p class="meta">{count_label(n, lang)}</p>
  {filter_bar_lang(discoveries, lang)}
  {feed if feed else '<p class="empty">' + ui(lang, "empty") + '</p>'}
</section>
"""
    (en_docs / "index.html").write_text(
        page(SITE_TITLE_EN, home_body, depth=0, lang=lang, rel_path=""),
        encoding="utf-8",
    )

    for tag in sorted(all_tags):
        entries = sorted(by_tag[tag], key=lambda e: e["date"], reverse=True)
        items_html = "".join(
            discovery_html(item, tags_base="./", lang=lang) for item in entries
        )
        body = f"""
<h2 class="section">Tag <code>#{esc(tag)}</code></h2>
<p class="meta">{count_label(len(entries), lang)}</p>
{items_html}
"""
        (en_tags / f"{tag}.html").write_text(
            page(
                f"#{tag} · {SITE_TITLE_EN}",
                body,
                depth=1,
                lang=lang,
                rel_path=f"tags/{tag}.html",
                crumbs=[
                    (ui(lang, "home"), "../index.html"),
                    (ui(lang, "tags"), "index.html"),
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
<h2 class="section">{ui(lang, "all_tags")}</h2>
<div class="tag-cloud">{' '.join(cloud_parts) or '<span class="empty">—</span>'}</div>
"""
    (en_tags / "index.html").write_text(
        page(
            f"{ui(lang, 'tags')} · {SITE_TITLE_EN}",
            tags_index_body,
            depth=1,
            lang=lang,
            rel_path="tags/index.html",
            crumbs=[(ui(lang, "home"), "../index.html"), (ui(lang, "tags"), "")],
        ),
        encoding="utf-8",
    )

    write_feed(discoveries, lang=lang)
    fix_tag_pages_lang(discoveries, lang, en_docs)
    inject_share_js_lang(lang, en_docs)
# --- fin Pépites EN ---



def esc(s: str) -> str:
    return html.escape(s, quote=True)


def format_date_fr(iso: str, lang: str = "fr") -> str:
    if lang == "en":
        return format_date_lang(iso, "en")
    dt = datetime.strptime(iso, "%Y-%m-%d")
    months = [
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    return f"{dt.day} {months[dt.month]} {dt.year}"


def format_day_fr(iso: str, lang: str = "fr") -> str:
    """« Jeudi 8 octobre 2026 » — noms français codés en dur (indépendant de la locale)."""
    if lang == "en":
        return format_day_lang(iso, "en")
    dt = datetime.strptime(iso, "%Y-%m-%d")
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return f"{days[dt.weekday()]} {format_date_fr(iso)}"


def day_separator_html(iso: str, *, first: bool, lang: str = "fr") -> str:
    return (
        f'\n<h3 class="day-sep" id="jour-{esc(iso)}">'
        f'<time datetime="{esc(iso)}">{esc(format_day_fr(iso, lang))}</time></h3>\n'
    )


def page(
    title: str,
    body: str,
    *,
    depth: int = 0,
    crumbs: list[tuple[str, str]] | None = None,
    lang: str = "fr",
    rel_path: str = "",
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
            '<nav class="crumbs" aria-label="' + ('Breadcrumb' if lang == 'en' else 'Fil d’Ariane') + '">'
            + '<span class="sep" aria-hidden="true"> / </span>'.join(parts)
            + "</nav>"
        )
    _fr_href = SITE_URL + rel_path
    _en_href = SITE_URL + "en/" + rel_path
    if lang == "en":
        return _page_en(
            title,
            body,
            prefix=prefix,
            crumb_html=crumb_html,
            fr_href=_fr_href,
            en_href=_en_href,
            github_href="https://github.com/olanlive/revue-outils-it",
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
  <link rel="alternate" hreflang="en" href="{esc(_en_href)}">
<script src="https://olanlive.github.io/pepites/nav.js?v=3" defer></script>
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
      <p>Veille outils IT pour studio 3D · open source d’abord (gratuit / payant signalé)</p>
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


def source_html(source, lang: str = "fr") -> str:
    """source: {"label": str, "url": str?} or a plain string."""
    if lang == "en":
        return source_html_lang(source, "en")
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
    lang: str = "fr",
) -> str:
    if lang == "en":
        return _discovery_en(item, show_date=show_date)
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
  {share_html(item)}
</article>
"""


def write_feed(discoveries: list[dict], lang: str = "fr") -> None:
    """docs/feed.xml — RSS 2.0, un item par découverte (lien = ancre du bloc)."""
    if lang == "en":
        write_feed_en(discoveries)
        return
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
  {filter_bar_html(discoveries)}
  {feed if feed else '<p class="empty">Aucune découverte pour le moment.</p>'}
</section>
"""
    (DOCS / "index.html").write_text(
        page(SITE_TITLE, home_body, depth=0, rel_path=""), encoding="utf-8"
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
                rel_path=f"tags/{tag}.html",
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
            rel_path="tags/index.html",
            crumbs=[("Accueil", "../index.html"), ("Tags", "")],
        ),
        encoding="utf-8",
    )

    write_feed(discoveries)
    write_latest(discoveries)

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

    build_lang("en", discoveries)
    print(f"Built {len(discoveries)} discovery(ies), {len(all_tags)} tag(s) → {DOCS}")


if __name__ == "__main__":
    build()
