#!/usr/bin/env python3
"""Contrôles du site généré (docs/) : RSS, latest.json, liens internes, moteur commun.

Stdlib uniquement. Identique dans les 5 blogs Pépites. Code de sortie 1 si un contrôle échoue.
Usage : python3 scripts/check_site.py [rss|latest|links|moteur ...]  (tous par défaut)
"""
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPO = ROOT.name if (ROOT / "scripts" / "build.py").exists() else ""
errors = []


def err(check, msg):
    errors.append(f"[{check}] {msg}")


def check_rss():
    for feed in (DOCS / "feed.xml", DOCS / "en" / "feed.xml"):
        rel = feed.relative_to(ROOT)
        if not feed.exists():
            err("rss", f"{rel} absent")
            continue
        try:
            root = ET.parse(feed).getroot()
        except ET.ParseError as e:
            err("rss", f"{rel} : XML invalide ({e})")
            continue
        items = root.findall("./channel/item")
        if len(items) > 100:
            err("rss", f"{rel} : {len(items)} items (> 100)")
        for i, it in enumerate(items, 1):
            for tag in ("title", "link", "guid"):
                el = it.find(tag)
                if el is None or not (el.text or "").strip():
                    err("rss", f"{rel} item {i} : <{tag}> manquant ou vide")
        print(f"rss : {rel} {len(items)} items")


def check_latest():
    f = DOCS / "latest.json"
    if not f.exists():
        err("latest", "docs/latest.json absent")
        return
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except ValueError as e:
        err("latest", f"JSON invalide ({e})")
        return
    if not isinstance(d, dict):
        err("latest", "la racine n'est pas un objet")
        return
    # nav.js (olanlive/pepites) lit d.date et la compare en chaîne : AAAA-MM-JJ obligatoire.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d.get("date", ""))):
        err("latest", f"champ date absent ou pas au format AAAA-MM-JJ : {d.get('date')!r}")
    for k in ("anchor", "name"):
        if not isinstance(d.get(k), str) or not d[k]:
            err("latest", f"champ {k} absent ou vide")
    a = d.get("anchor")
    if isinstance(a, str) and a and a not in ids_of(DOCS / "index.html"):
        err("latest", f"ancre #{a} absente de docs/index.html")
    print(f"latest : {d.get('date')} #{a}")


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.refs = set(), []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if v is None:
                continue
            if k in ("id", "name") and tag != "meta":
                self.ids.add(v)
            if k in ("href", "src") and not (tag == "link" and dict(attrs).get("rel") == "preconnect"):
                self.refs.append((tag, k, v, self.getpos()[0]))


_cache = {}


def parse(path):
    if path not in _cache:
        c = Collector()
        c.feed(path.read_text(encoding="utf-8"))
        _cache[path] = c
    return _cache[path]


def ids_of(path):
    return parse(path).ids if path.exists() else set()


def resolve(base, url):
    """Renvoie le fichier visé dans docs/, ou None si le lien sort du repo."""
    p = unquote(urlsplit(url).path)
    if p.startswith("/"):
        prefix = f"/{REPO}/"
        if not REPO or not (p + "/").startswith(prefix):
            return None  # autre site de olanlive.github.io : hors périmètre
        target = DOCS / p[len(prefix):]
    else:
        target = base.parent / p if p else base
    if p.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target


def check_links():
    pages = sorted(DOCS.rglob("*.html"))
    n = 0
    for page in pages:
        rel = page.relative_to(ROOT)
        for tag, attr, url, line in parse(page).refs:
            u = url.strip()
            s = urlsplit(u)
            if s.scheme or u.startswith("//") or not u:
                continue  # externe, mailto:, data:, javascript: : non testé
            target = resolve(page, u)
            if target is None:
                continue
            n += 1
            try:
                target.resolve().relative_to(DOCS.resolve())
            except ValueError:
                err("liens", f"{rel}:{line} {attr}={url!r} sort de docs/")
                continue
            if not target.exists():
                err("liens", f"{rel}:{line} {attr}={url!r} → fichier introuvable ({target.relative_to(ROOT)})")
                continue
            frag = unquote(s.fragment)
            if frag.startswith("tag="):
                continue  # filtre JS de build.py (location.hash « #tag=… »), pas une ancre
            if frag and target.suffix == ".html" and frag not in ids_of(target):
                err("liens", f"{rel}:{line} {attr}={url!r} → ancre #{frag} introuvable")
    print(f"liens : {len(pages)} pages, {n} liens internes")


# md5 de référence du moteur commun (identique dans les 5 blogs). Si on modifie
# scripts/moteur.py ou la coquille scripts/build.py, mettre à jour ces valeurs ici
# et recopier les 3 fichiers à l'identique dans les 5 repos.
MOTEUR_MD5 = {"moteur.py": "f18010837d6fbc7ece90c14a1c8b1a92", "build.py": "3224f7ae52a2fab65e2f7a4a203e97dd"}


def check_moteur():
    for name, ref in MOTEUR_MD5.items():
        f = ROOT / "scripts" / name
        got = hashlib.md5(f.read_bytes()).hexdigest() if f.exists() else "absent"
        if got != ref:
            err("moteur", f"scripts/{name} : md5 {got} ≠ référence {ref} (copie commune modifiée ?)")
    print("moteur : " + ", ".join(f"{n} {r}" for n, r in MOTEUR_MD5.items()))


CHECKS = {"rss": check_rss, "latest": check_latest, "links": check_links, "moteur": check_moteur}

if __name__ == "__main__":
    for name in sys.argv[1:] or CHECKS:
        CHECKS[name]()
    for e in errors:
        print(f"::error::{e}" if __import__("os").environ.get("GITHUB_ACTIONS") else e)
    print("OK" if not errors else f"{len(errors)} erreur(s)")
    sys.exit(1 if errors else 0)
