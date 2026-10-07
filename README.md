# Pépites Outils IT

Repo : `revue-outils-it`

Veille **outils IT pour un studio 3D** — open source ou gratuits d’abord (payant signalé).

Site statique (GitHub Pages) : **https://olanlive.github.io/revue-outils-it/**

Flux RSS 2.0 : **https://olanlive.github.io/revue-outils-it/feed.xml** (un item par découverte, lien vers l’ancre du bloc)

Cadence : **tous les 2 jours** (jours pairs, en alternance avec la revue Audio & Vidéo) — 3 à 7 pépites par passage, **rien publié s’il n’y a rien de neuf**.

## Priorités

IT de studio 3D d’abord :

1. Render farm / gestion de nœuds, licences flottantes
2. Stockage & NAS, sauvegarde
3. Déploiement / imaging / MDM de postes, inventaire & helpdesk
4. Monitoring, réseau, accès distant / PCoIP
5. Pipeline côté infra (gestion d’assets, synchro), sécurité, self-hosting

Chaque pépite doit avoir une **vraie actualité** (release récente, projet découvert récemment), une **URL officielle vérifiée** et une **source réelle** (release notes, annonce, post HN/Reddit/X, article). Ne rien inventer.

Avant d’ajouter : vérifier [`COVERED.md`](./COVERED.md) (généré) pour éviter les doublons. Hors périmètre : 3D/VFX créatifs (`olanlive/revue-oss-3d`) et audio/vidéo (`olanlive/revue-audio-video`).

## Résumés

**Résumé court et percutant : 1 à 2 phrases, 280 caractères max** (le build avertit au-delà). Ce que fait l’outil ou ce qui est neuf dans cette version, avec la date de l’actu. Mention très courte (« RC », « bêta », « payant ») seulement si essentielle.

## Ajouter une découverte

1. Éditer [`data/discoveries.json`](./data/discoveries.json) : ajouter un objet (en tête de préférence ; le build trie par date décroissante, ordre conservé à date égale) :

```json
{
  "date": "2026-10-10",
  "name": "Nom de l’outil 1.2.3",
  "summary": "Ce que fait l’outil / ce qui est neuf (sortie le 9 oct). 1–2 phrases, 280 caractères max.",
  "url": "https://site-officiel…",
  "tags": ["sauvegarde", "nas"],
  "source": { "label": "Release GitHub — owner/repo 1.2.3", "url": "https://github.com/…/releases/tag/…" }
}
```

2. Rebuild (régénère `docs/`, dont `docs/feed.xml`, et `COVERED.md`) :

```bash
python3 scripts/build.py
```

3. Commit + push :

```bash
git add -A && git commit -m "Pépites du AAAA-MM-JJ : …" && git push origin main
```

GitHub Pages (branche `main`, dossier `/docs`) se redéploie tout seul.

## Tags (vocabulaire)

Tags kebab-case, sans accents, à réutiliser de façon cohérente :

| Tag | Usage |
|-----|--------|
| `render-farm` | Render farm, gestion de nœuds / files de jobs |
| `openjd` | Open Job Description |
| `licences` | Licences flottantes, serveurs de licences |
| `stockage` | Stockage, systèmes de fichiers |
| `nas` | NAS |
| `zfs` | ZFS |
| `s3` | Stockage objet S3 |
| `sauvegarde` | Sauvegarde / restauration |
| `deploiement` | Déploiement de postes / logiciels, MDM |
| `imaging` | Images disque / masterisation |
| `pxe` | Boot réseau |
| `inventaire` | Gestion de parc / inventaire |
| `helpdesk` | Ticketing / ITSM |
| `monitoring` | Supervision, métriques, alertes |
| `reseau` | Réseau, VPN, firewall |
| `acces-distant` | Accès distant, PCoIP, streaming de poste |
| `pipeline` | Pipeline / gestion d’assets côté infra |
| `securite` | Sécurité |
| `self-hosting` | Auto-hébergeable |
| `virtualisation` | Hyperviseurs, conteneurs |
| `rc` | Release candidate / bêta |
| `emerging` | Projet jeune / early |

## Architecture

- `data/discoveries.json` — fil plat de découvertes (éditable ; champs `date`, `name`, `summary`, `url`, `tags`, `source {label, url}`)
- `scripts/build.py` — génère le HTML dans `docs/` et `COVERED.md`
- `docs/` — site publié (Pages depuis `main` / dossier `/docs`) : `index.html` (fil unique, plus récent en haut), `tags/*.html`, `feed.xml` (RSS 2.0, 100 dernières découvertes)
- `COVERED.md` — liste générée des outils déjà couverts (anti-doublons)

Chaque bloc `<article class="discovery">` a une ancre stable `id="AAAA-MM-JJ-nom-version"` (lien direct, utilisé par le flux RSS).

Pas de npm. Python 3 standard library uniquement.

## Thème

Thème sombre **ambre/orange** (distinct du bleu de la revue 3D et du vert de la revue Audio & Vidéo), contrastes WCAG AA vérifiés :

| Couleur | Fond | Ratio |
|---|---|---|
| Texte `#f6ede1` | fond `#17110a` / carte `#231a0f` | 16.16:1 / 14.78:1 |
| Texte secondaire `#c9b393` | fond / carte | 9.24:1 / 8.44:1 |
| Liens `#ffb347` | fond / carte | 10.52:1 / 9.62:1 |
| Liens survol `#ffd18f` | fond / carte | 13.17:1 / 12.05:1 |
| Tags `#ffdca8` | `#35270f` | 11.08:1 |
| Tags survol `#ffd18f` | `#4a3612` | 8.08:1 |

Les liens dans du texte courant (source, footer) sont soulignés pour ne pas reposer sur la seule couleur.

## Source d’une découverte

Champ `source` : où la pépite a été repérée, affiché sous le résumé (« Trouvé via : … »).

Libellés usuels : « Release GitHub — owner/repo x.y.z », « Forum — projet », « Fil X — @compte », « HN — titre », « Reddit — r/sub », « Web — site ».

## Licence

Notes de veille (liens vers les projets upstream, chacun avec sa propre licence).
