#!/usr/bin/env python3
"""
4 – Dataset finale per il modello statistico.

Input:  data/processed/results_model.parquet
        data/processed/teams_uefa.parquet
        data/processed/player_features.parquet
Output: data/processed/match_dataset.parquet

Operazioni:
  - Armonizzazione nomi squadre (results.csv → national_teams.csv)
  - Filtraggio partite dove entrambe le squadre sono UEFA
  - Join delle feature di squadra per home e away (prefisso home_ / away_)
  - Calcolo di feature derivate: rank_diff, log_mv_ratio
  - Report finale: dimensioni, null critici, distribuzione outcome
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import PROCESSED_DIR, RESULTS_NAME_FIXES


# Colonne di feature da propagare su ogni partita (per home e away)
SQUAD_FEAT_COLS = [
    "national_team_id",
    "total_market_value",
    "fifa_ranking",
    "squad_size",
    "average_age",
]


def build_match_dataset() -> pd.DataFrame:

    results  = pd.read_parquet(PROCESSED_DIR / "results_model.parquet")
    teams    = pd.read_parquet(PROCESSED_DIR / "teams_uefa.parquet")
    features = pd.read_parquet(PROCESSED_DIR / "player_features.parquet")
    print(f"  Partite lette:        {len(results):>6,}")
    print(f"  Squadre UEFA lette:   {len(teams):>6}")

    # ── Armonizzazione nomi tra results.csv e national_teams.csv ────────────
    # Applica RESULTS_NAME_FIXES solo alle entry definite — non tocca il resto
    results["home_team"] = results["home_team"].replace(RESULTS_NAME_FIXES)
    results["away_team"] = results["away_team"].replace(RESULTS_NAME_FIXES)

    # ── Merge feature Transfermarkt sulle squadre ────────────────────────────
    mv_cols     = [c for c in features.columns if c.startswith("mv_")]
    team_full   = teams.merge(features, on="national_team_id", how="left")
    feat_cols   = SQUAD_FEAT_COLS + mv_cols
    lookup      = team_full.set_index("name")[feat_cols]
    uefa_names  = set(team_full["name"])

    # ── Filtraggio partite UEFA×UEFA ─────────────────────────────────────────
    mask    = results["home_team"].isin(uefa_names) & results["away_team"].isin(uefa_names)
    df      = results[mask].copy()
    dropped = len(results) - len(df)
    print(f"  Partite UEFA×UEFA:    {len(df):>6,}  (escluse non-UEFA: {dropped:,})")

    # Squadre nei risultati non trovate nel lookup — segnale per RESULTS_NAME_FIXES
    all_teams_in_results = set(df["home_team"]) | set(df["away_team"])
    unmatched = all_teams_in_results - uefa_names
    if unmatched:
        print(f"  [⚠] Squadre nei risultati senza match nel lookup ({len(unmatched)}):")
        for t in sorted(unmatched):
            print(f"       \"{t}\"  ← aggiungere a config.RESULTS_NAME_FIXES")

    # ── Join feature per home e away ─────────────────────────────────────────
    for prefix, role_col in [("home", "home_team"), ("away", "away_team")]:
        renamed = lookup.add_prefix(f"{prefix}_")
        df = df.join(renamed, on=role_col)

    # ── Feature derivate ─────────────────────────────────────────────────────
    # rank_diff > 0  →  la squadra di casa ha ranking FIFA più basso (più forte)
    df["rank_diff"] = df["away_fifa_ranking"] - df["home_fifa_ranking"]

    # log_mv_ratio > 0  →  la squadra di casa vale di più
    df["log_mv_ratio"] = (
        np.log1p(df["home_total_market_value"])
        - np.log1p(df["away_total_market_value"])
    )

    # ── Report finale ────────────────────────────────────────────────────────
    _report(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "match_dataset.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n  ✓ match_dataset.parquet  ({len(df):,} righe × {df.shape[1]} col)")
    return df


def _report(df: pd.DataFrame) -> None:
    """Stampa un breve report di qualità sul dataset finale."""
    print("\n  ── Report dataset ──────────────────────────────────")

    # Null nelle feature critiche
    critical = ["home_fifa_ranking", "away_fifa_ranking",
                "home_total_market_value", "away_total_market_value"]
    for col in critical:
        if col in df.columns:
            n = df[col].isna().sum()
            flag = " [⚠]" if n > 0 else ""
            print(f"  null {col:<35}: {n:>4}{flag}")

    # Distribuzione outcome
    counts = df["outcome"].value_counts()
    total  = len(df)
    print(f"\n  Distribuzione outcome:")
    for oc, label in [("H", "Casa vince"), ("D", "Pareggio"), ("A", "Trasferta vince")]:
        n = counts.get(oc, 0)
        print(f"    {label:<18}: {n:>5}  ({n/total:.1%})")

    # Range date
    print(f"\n  Date: {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  Tornei: {df['tournament'].value_counts().to_dict()}")
    print("  ────────────────────────────────────────────────────")


if __name__ == "__main__":
    print("\n[Passo 4/4] Costruzione match dataset finale\n" + "─" * 50)
    build_match_dataset()
