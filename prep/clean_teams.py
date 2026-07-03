#!/usr/bin/env python3
"""
2 – Pulizia di national_teams.csv.

Input:  data/raw/national_teams.csv
Output: data/processed/teams_uefa.parquet

Operazioni:
  - Filtraggio per confederation == "UEFA"
  - Esclusione squadre sospese (Russia)
  - Selezione colonne utili al modello
  - Aggiunta colonna name_it per il collegamento con il simulatore Swiss
  - Report delle squadre senza mappatura (segnale per aggiornare config.py)
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import EXCLUDED_TEAMS, NAME_MAP_EN_IT, PROCESSED_DIR, RAW_DIR


# Colonne di national_teams.csv da tenere nel dataset processato.
# total_market_value e fifa_ranking sono feature dirette per il modello baseline.
KEEP_COLS = [
    "national_team_id",
    "name",
    "country_name",
    "total_market_value",
    "fifa_ranking",
    "squad_size",
    "average_age",
]


def clean_teams() -> pd.DataFrame:
    """
    Carica national_teams.csv, filtra le squadre UEFA e aggiunge la mappatura nomi.
    Salva il risultato in data/processed/teams_uefa.parquet.
    """
    df = pd.read_csv(RAW_DIR / "national_teams.csv")
    print(f"  Squadre caricate:   {len(df):>4}")

    # Filtraggio per confederazione UEFA
    df = df[df["confederation"] == "UEFA"].copy()
    print(f"  Squadre UEFA:       {len(df):>4}")

    # Esclusione squadre sospese o non presenti nel simulatore
    df = df[~df["name"].isin(EXCLUDED_TEAMS)].copy()
    print(f"  Dopo esclusioni:    {len(df):>4}  (escluse: {EXCLUDED_TEAMS})")

    # Selezione colonne — usa solo quelle effettivamente presenti nel file
    cols_present = [c for c in KEEP_COLS if c in df.columns]
    missing_cols = set(KEEP_COLS) - set(cols_present)
    if missing_cols:
        print(f"  [⚠] Colonne attese mancanti nel CSV: {missing_cols}")
    df = df[cols_present].copy()

    # Mappatura nomi inglesi → nomi italiani del simulatore
    df["name_it"] = df["name"].map(NAME_MAP_EN_IT)

    # Report squadre senza mappatura → aggiungere a config.NAME_MAP_EN_IT
    unmapped = df[df["name_it"].isna()]["name"].tolist()
    if unmapped:
        print(f"\n  [⚠] Squadre senza mappatura IT ({len(unmapped)}) "
              f"— aggiungerle a config.NAME_MAP_EN_IT:")
        for n in sorted(unmapped):
            print(f"       \"{n}\": \"\",")
    else:
        print(f"  Tutte le squadre hanno mappatura IT.")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "teams_uefa.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n  ✓ teams_uefa.parquet  ({len(df)} righe × {df.shape[1]} col)")
    return df


if __name__ == "__main__":
    print("\n[Passo 2/4] Pulizia national_teams.csv\n" + "─" * 50)
    clean_teams()
