#!/usr/bin/env python3
"""Construit docs/ : coquille qui charge scripts/reglages.py et le moteur commun scripts/moteur.py.

Commande inchangée : `python scripts/build.py`. Réglages du blog : scripts/reglages.py.
"""

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import moteur  # noqa: E402

if __name__ == "__main__":
    moteur.build()
