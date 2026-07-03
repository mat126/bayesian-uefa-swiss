#!/usr/bin/env python3
"""
Pipeline di preparazione dati – esegue tutti i passi in sequenza.

Uso:
    python run_pipeline.py

I passi sono indipendenti: ognuno legge da data/raw/ e scrive in data/processed/.
È possibile eseguire un singolo passo manualmente, es.:
    python prep/clean_results.py
    python prep/clean_teams.py
    python prep/player_features.py
    python prep/build_match_dataset.py

Il passo 4 dipende dagli output dei passi 1, 2 e 3.
I passi 1, 2 e 3 sono indipendenti tra loro e possono girare in qualsiasi ordine.
"""

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = [
    Path("prep") / "clean_results.py",
    Path("prep") / "clean_teams.py",
    Path("prep") / "player_features.py",
    Path("prep") / "build_match_dataset.py",
]


def run_pipeline() -> None:
    print("\n" + "═" * 60)
    print("  PIPELINE PREPARAZIONE DATI")
    print("═" * 60)

    total_start = time.perf_counter()

    for script in SCRIPTS:
        print(f"\n  Esecuzione: {script}")
        t0 = time.perf_counter()
        result = subprocess.run(
            [sys.executable, str(script)],
            check=False,   # non interrompe la pipeline — controlliamo noi il returncode
        )
        elapsed = time.perf_counter() - t0

        if result.returncode != 0:
            print(f"\n  [ERRORE] {script} terminato con codice {result.returncode}.")
            print("  Pipeline interrotta.")
            sys.exit(result.returncode)

        print(f"  (completato in {elapsed:.1f}s)")

    total_elapsed = time.perf_counter() - total_start
    print(f"\n{'═' * 60}")
    print(f"  ✓ Pipeline completata in {total_elapsed:.1f}s")
    print(f"  Output in:  data/processed/")
    print(f"    • results_model.parquet")
    print(f"    • teams_uefa.parquet")
    print(f"    • player_features.parquet")
    print(f"    • match_dataset.parquet")
    print("═" * 60)


if __name__ == "__main__":
    run_pipeline()
