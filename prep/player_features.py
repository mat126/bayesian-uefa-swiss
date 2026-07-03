#!/usr/bin/env python3
"""
3 – Feature di valore di mercato per reparto (players + valuations).

Input:  data/raw/players.csv
        data/raw/player_valuations.csv
Output: data/processed/player_features.parquet

Operazioni:
  - Selezione giocatori con current_national_team_id valorizzato
  - Join temporale con player_valuations: per ogni giocatore, valore più recente
    alla data MARKET_VALUE_REF_DATE (snapshot statico — vedi nota sotto)
  - Filtro top-N giocatori per (national_team_id, position) ordinati per valore
    decrescente: si escludono le riserve e i giocatori di minor qualità che
    abbasserebbero la media delle nazionali top (vedi TOP_N sotto)
  - Aggregazione per (national_team_id, position): media e conteggio sul subset top-N
  - Pivot su position → colonne flat del tipo mv_mean_Attack, mv_mean_Defender, ...
  - Imputazione a 0 per reparti senza giocatori valorizzati

Nota sulla limitazione del dato:
  current_national_team_id traccia solo la rosa *attuale*, non quella storica.
  Queste feature sono pertanto uno snapshot statico, non feature match-per-match.
  Per il modello baseline vanno bene; il notebook documenta questo trade-off
  e descrive come aggiornare l'approccio con dati storici.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import MARKET_VALUE_REF_DATE, PROCESSED_DIR, RAW_DIR

# Posizioni standard da mantenere — esclude 'Missing'
VALID_POSITIONS = {"Goalkeeper", "Defender", "Midfield", "Attack"}

# Numero massimo di giocatori per posizione usati nel calcolo della media.
# Si prendono i top-N per valore di mercato, approssimando la qualità
# dell'undici titolare ed escludendo riserve che abbasserebbero la media.
TOP_N: dict[str, int] = {
    "Goalkeeper": 3,    # titolare + 2 riserve
    "Defender":   10,   # difensori chiave (4-5 titolari + riserve di qualità)
    "Midfield":   10,
    "Attack":     10,
}


def build_player_features() -> pd.DataFrame:
    """
    Costruisce feature di valore di mercato per reparto per ogni nazionale.
    Salva il risultato in data/processed/player_features.parquet.
    """
    players    = pd.read_csv(RAW_DIR / "players.csv")
    valuations = pd.read_csv(RAW_DIR / "player_valuations.csv")
    print(f"  Giocatori caricati:          {len(players):>8,}")
    print(f"  Valutazioni caricate:        {len(valuations):>8,}")

    # ── Filtraggio giocatori con nazionale e posizione valida ────────────────
    mask = players["current_national_team_id"].notna() & \
           players["position"].isin(VALID_POSITIONS)
    df = players[mask].copy()
    df["current_national_team_id"] = df["current_national_team_id"].astype(int)
    print(f"  Con nazionale e pos. valida: {len(df):>8,}")

    # ── Join temporale: valore più recente ≤ MARKET_VALUE_REF_DATE ──────────
    valuations["date"] = pd.to_datetime(valuations["date"])
    ref_date = pd.Timestamp(MARKET_VALUE_REF_DATE)

    latest_values = (
        valuations[valuations["date"] <= ref_date]
        .sort_values("date")
        .groupby("player_id")["market_value_in_eur"]
        .last()
        .reset_index()
        .rename(columns={"market_value_in_eur": "market_value_ref"})
    )

    df = df[["player_id", "current_national_team_id", "position"]].merge(
        latest_values, on="player_id", how="left"
    )

    # Imputazione dei valori mancanti a 0 (giocatori senza storico Transfermarkt)
    n_missing = df["market_value_ref"].isna().sum()
    if n_missing > 0:
        print(f"  [⚠] {n_missing} giocatori senza valutazione → imputati a 0")
    df["market_value_ref"] = df["market_value_ref"].fillna(0.0)

    # ── Filtro top-N per (national_team_id, position) ───────────────────────
    # Per ogni posizione: ordina per valore decrescente e prendi i top-N per squadra.
    # Approccio per-position invece di groupby().apply() per robustezza su pandas 2.x.
    parts = []
    for pos, n in TOP_N.items():
        part = (
            df[df["position"] == pos]
            .sort_values("market_value_ref", ascending=False)
            .groupby("current_national_team_id", group_keys=False)
            .head(n)
        )
        parts.append(part)
    df_top = pd.concat(parts).reset_index(drop=True)
    print(f"  Giocatori dopo filtro top-N: {len(df_top):>8,}")

    # ── Aggregazione sul subset top-N ────────────────────────────────────────
    # mv_mean = media dei top-N → proxy qualità titolari
    # mv_count = quanti giocatori top-N hanno valutazione (utile per diagnostica)
    agg = (
        df_top.groupby(["current_national_team_id", "position"])["market_value_ref"]
        .agg(mv_mean="mean", mv_count="count")
        .unstack("position")                              # posizioni → colonne
    )

    # Flatten nomi colonne multi-livello: (stat, Position) → "stat_Position"
    agg.columns = [f"{stat}_{pos}" for stat, pos in agg.columns]
    agg = (
        agg.reset_index()
           .rename(columns={"current_national_team_id": "national_team_id"})
           .fillna(0.0)   # reparti assenti → 0
    )

    print(f"  Squadre nel dataset:         {len(agg):>8}")
    print(f"  Colonne feature generate:    {agg.shape[1] - 1:>8}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "player_features.parquet"
    agg.to_parquet(out_path, index=False)
    print(f"\n  ✓ player_features.parquet  ({len(agg)} righe × {agg.shape[1]} col)")
    return agg


if __name__ == "__main__":
    print("\n[Passo 3/4] Costruzione player features\n" + "─" * 50)
    build_player_features()
