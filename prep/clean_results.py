#!/usr/bin/env python3
"""
1– Pulizia e filtraggio di results.csv.

Input:  data/raw/results.csv
Output: data/processed/results_model.parquet

Operazioni:
  - Filtraggio per competizioni rilevanti (config.COMPETITION_WEIGHTS)
  - Filtraggio per finestra temporale (>= config.DATE_FROM)
  - Rimozione di partite con punteggio mancante
  - Calcolo colonna outcome ('H' / 'D' / 'A')
  - Calcolo pesi: peso_competizione × peso_temporale (decadimento esponenziale)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Aggiunge prep/ al path per importare config.py indipendentemente
# dalla directory di lavoro da cui si lancia lo script.
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    COMPETITION_WEIGHTS,
    DATE_FROM,
    DATE_TO,
    DECAY_LAMBDA,
    PROCESSED_DIR,
    RAW_DIR,
)


def clean_results() -> pd.DataFrame:
    """
    Carica results.csv, applica filtri e calcola i pesi per il modello.
    Salva il risultato in data/processed/results_model.parquet.
    """
    df = pd.read_csv(RAW_DIR / "results.csv")
    print(f"  Partite caricate:             {len(df):>7,}")

    # Parsing date
    df["date"] = pd.to_datetime(df["date"])

    # Filtraggio per competizione
    df = df[df["tournament"].isin(COMPETITION_WEIGHTS)].copy()
    print(f"  Dopo filtro competizione:     {len(df):>7,}")

    # Filtraggio per finestra temporale
    df = df[df["date"] >= DATE_FROM].copy()
    print(f"  Dopo filtro data (>={DATE_FROM}): {len(df):>7,}")

    df = df[df["date"] <= DATE_TO].copy()
    print(f"  Dopo filtro data (<={DATE_TO}):  {len(df):>7,}")

    # Rimozione punteggi mancanti (16 righe note nel dataset)
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    print(f"  Dopo drop null score:         {len(df):>7,}")

    # Colonna outcome
    df["outcome"] = np.where(
        df["home_score"] > df["away_score"], "H",
        np.where(df["home_score"] == df["away_score"], "D", "A"),
    )

    # Peso competizione
    df["weight_competition"] = df["tournament"].map(COMPETITION_WEIGHTS)

    # Peso temporale: decadimento esponenziale dalla partita più recente nel set
    ref_date          = df["date"].max()
    df["days_ago"]    = (ref_date - df["date"]).dt.days
    df["weight_time"] = np.exp(-DECAY_LAMBDA * df["days_ago"])

    # Peso finale
    df["weight"] = df["weight_competition"] * df["weight_time"]

    # Riordino colonne — le colonne peso sono in coda per leggibilità
    ordered_cols = [
        "date", "home_team", "away_team",
        "home_score", "away_score", "outcome",
        "tournament", "neutral",
        "weight_competition", "weight_time", "weight", "days_ago",
    ]
    df = df[ordered_cols]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "results_model.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n  ✓ results_model.parquet  ({len(df):,} righe × {df.shape[1]} col)")
    return df


if __name__ == "__main__":
    print("\n[Passo 1/4] Pulizia results.csv\n" + "─" * 50)
    clean_results()
