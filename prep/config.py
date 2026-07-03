"""
Costanti e parametri condivisi per la pipeline di preparazione dati.

Modifica questo file per cambiare percorsi, finestre temporali,
pesi competizione o mappature nomi senza toccare i singoli script.
"""

from pathlib import Path

# =============================================================================
# PERCORSI
# =============================================================================
# PROJECT_ROOT è due livelli sopra questo file: project_root/prep/config.py
PROJECT_ROOT  = Path(__file__).resolve().parent.parent
RAW_DIR       = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# =============================================================================
# PARAMETRI TRAINING SET
# =============================================================================
# Limite inferiore: giorno dopo la finale del Mondiale 2022 (18/12/2022).
# Solo partite post-Mondiale entrano nel training set, così i parametri
# riflettono la forma delle squadre nell'era post-Qatar.
DATE_FROM = "2022-12-19"

# Limite superiore: data di inizio delle qualificazioni reali (21/03/2025).
# Non usiamo partite successive per evitare data leakage dalla competizione
# che il modello deve simulare.
DATE_TO = "2025-03-21"

# Snapshot Transfermarkt: valore di mercato più recente disponibile
# prima dell'inizio delle qualificazioni.
MARKET_VALUE_REF_DATE = "2025-03-21"

# =============================================================================
# PESI COMPETIZIONE
# =============================================================================
# Le friendly sono incluse con peso basso per aumentare la copertura
# delle squadre minori. Escluderle è una scelta alternativa valida.
COMPETITION_WEIGHTS: dict[str, float] = {
    "FIFA World Cup":               1.0,
    "FIFA World Cup qualification": 1.0,
    "UEFA Euro":                    1.0,
    "UEFA Euro qualification":      1.0,
    "UEFA Nations League":          0.9,
    "Friendly":                     0.3,
}

# =============================================================================
# DECADIMENTO TEMPORALE
# =============================================================================
# Peso partita = exp(-DECAY_LAMBDA * giorni_fa)
# Con DECAY_LAMBDA = 0.0005: half-life ≈ 3.8 anni (1387 giorni)
# Aumentare per dare più peso alle partite recenti; ridurre per finestre più ampie.
DECAY_LAMBDA: float = 0.0005

# =============================================================================
# ARMONIZZAZIONE NOMI – results.csv → national_teams.csv
# =============================================================================
# Alcune squadre hanno nomi leggermente diversi tra i due dataset.
# Chiave: nome in results.csv   Valore: nome in national_teams.csv
# Aggiungere discrepanze che emergono in fase di sviluppo.
RESULTS_NAME_FIXES: dict[str, str] = {
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Czech Republic":         "Czechia",              # TM usa "Czechia" dal 2016
}

# =============================================================================
# MAPPATURA NOMI – national_teams.csv (EN) → simulatore Swiss (IT)
# =============================================================================
NAME_MAP_EN_IT: dict[str, str] = {
    "Spain":                  "Spagna",
    "France":                 "Francia",
    "Belgium":                "Belgio",
    "England":                "Inghilterra",
    "Portugal":               "Portogallo",
    "Netherlands":            "Paesi Bassi",
    "Italy":                  "Italia",
    "Croatia":                "Croazia",
    "Germany":                "Germania",
    "Wales":                  "Galles",
    "Switzerland":            "Svizzera",
    "Denmark":                "Danimarca",
    "Ukraine":                "Ucraina",
    "Austria":                "Austria",
    "Sweden":                 "Svezia",
    "Poland":                 "Polonia",
    "Norway":                 "Norvegia",
    "Serbia":                 "Serbia",
    "Czechia":                "Repubblica Ceca",
    "Czech Republic":         "Repubblica Ceca",   # alias per sicurezza
    "Scotland":               "Scozia",
    "Turkey":                 "Turchia",
    "Romania":                "Romania",
    "Slovakia":               "Slovacchia",
    "Greece":                 "Grecia",
    "Hungary":                "Ungheria",
    "Republic of Ireland":    "Irlanda",
    "Ireland":                "Irlanda",            # alias alternativo
    "Slovenia":               "Slovenia",
    "Bosnia & Herzegovina":   "Bosnia-Erzegovina",
    "Bosnia and Herzegovina": "Bosnia-Erzegovina",  # alias per sicurezza
    "Bosnia-Herzegovina":     "Bosnia-Erzegovina",  # formato Transfermarkt
    "Türkiye":                "Turchia",             # nuovo nome ufficiale dal 2022
    "North Macedonia":        "Macedonia del Nord",
    "Iceland":                "Islanda",
    "Albania":                "Albania",
    "Montenegro":             "Montenegro",
    "Bulgaria":               "Bulgaria",
    "Georgia":                "Georgia",
    "Israel":                 "Israele",
    "Northern Ireland":       "Irlanda del Nord",
    "Luxembourg":             "Lussemburgo",
    "Belarus":                "Bielorussia",
    "Armenia":                "Armenia",
    "Estonia":                "Estonia",
    "Faroe Islands":          "Faroe",
    "Cyprus":                 "Cipro",
    "Kosovo":                 "Kosovo",
    "Azerbaijan":             "Azerbaigian",
    "Kazakhstan":             "Kazakhstan",
    "Latvia":                 "Lettonia",
    "Lithuania":              "Lituania",
    "Moldova":                "Moldova",
    "Malta":                  "Malta",
    "Andorra":                "Andorra",
    "Gibraltar":              "Gibilterra",
    "Liechtenstein":          "Liechtenstein",
    "San Marino":             "San Marino",
    "Finland":                "Finlandia",
    # Russia: sospesa UEFA/FIFA — esclusa dal simulatore
}

# Squadre esplicitamente escluse dal set UEFA del simulatore
EXCLUDED_TEAMS: set[str] = {"Russia"}
