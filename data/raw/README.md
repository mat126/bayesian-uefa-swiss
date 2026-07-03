# Raw Data

This folder holds the raw dataset files used by the preparation pipeline. Its contents are not tracked by git, so after cloning the repository you need to download the files yourself and place them here before running `run_pipeline.py`. The pipeline reads the files by exact name, so keep the filenames as listed below.

## Files Expected by the Pipeline

The four files below are the ones the pipeline reads directly.

| Filename                 | Source        | Used by                              |
|--------------------------|---------------|--------------------------------------|
| `results.csv`            | martj42       | `clean_results.py`                   |
| `national_teams.csv`     | Transfermarkt | `clean_teams.py`                     |
| `players.csv`            | Transfermarkt | `player_features.py`                 |
| `player_valuations.csv`  | Transfermarkt | `player_features.py`                 |

A few additional Transfermarkt tables (`competitions.csv`, `appearances.csv`, `games.csv`, and related club files) are not required by the current pipeline. They are kept in mind for possible future features but can be left out for now.

## Where to Download

International football results come from the martj42 dataset on Kaggle. Download the archive and take `results.csv` from it. The other files in that archive (goalscorers, shootouts) are not needed.

https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017

The Transfermarkt tables come from the dcaribou repository on GitHub. Take `players.csv`, `player_valuations.csv`, and `national_teams.csv` from the prepared data.

https://github.com/dcaribou/transfermarkt-datasets/tree/master

## Reference Dates

Two dates in `prep/config.py` control which slice of the data ends up in the model, so it is worth knowing what the raw files are filtered against. `DATE_FROM` is `2022-12-19`, the day after the 2022 World Cup final, which keeps only post-Qatar form. `MARKET_VALUE_REF_DATE` is `2025-03-21`, the qualification start date, which is the point at which squad market values are read from `player_valuations.csv`. If you download a newer snapshot of either source, the results will still be filtered to these windows unless you change the constants.

## After Placing the Files

From the project root, run the pipeline:

```bash
python run_pipeline.py
```

This reads the files in this folder, runs the four preparation steps in order, and writes `match_dataset.parquet` to `data/processed/`.
