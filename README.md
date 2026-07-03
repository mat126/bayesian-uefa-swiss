# Bayesian Forecasting and Swiss-System Simulation of UEFA World Cup Qualification

This project models a hypothetical UEFA World Cup qualification format structured as a Swiss-system tournament. The motivation behind this choice is straightforward: unlike the traditional group stage draw, a Swiss system pairs teams against opponents at the same current standing at every round. There is no luck of the draw, no group of death, and no easy group. Each team faces competition proportional to its own results, which makes the format arguably fairer than the one currently in use.

The project is divided into two separate but connected components. Component A is the tournament engine. Component B is a statistical model that estimates match outcomes and feeds those estimates into the engine. The final goal is to connect the two, running the simulator thousands of times under a Monte Carlo scheme to produce qualification probability distributions for each of the 54 UEFA national teams (Russia is excluded, being currently suspended).

## Components

Component A, the Swiss simulator, lives in `swiss_uefa_qualification.py` and implements the tournament engine: pairings, tiebreakers, home and away balancing, geopolitical restrictions, and a plug-in probability interface. It can run as a standalone simulation or be called repeatedly for Monte Carlo estimates. The probability interface is a single callable with the signature `(home_team, away_team) -> (p_home, p_draw, p_away)`, which makes it easy to swap the current FIFA-rank placeholder for the statistical model.

Component B, the statistical model, lives in `model.ipynb` and builds a hierarchical Bayesian Poisson model in PyMC to estimate win, draw and loss probabilities and expected goals for each fixture. It is fed by a dedicated data pipeline in the `prep/` package, described below. Once integrated, it replaces the placeholder probability function used by Component A.

## Repository Structure

```
.
├── README.md
├── requirements.txt              # pip dependencies (see note on Windows below)
├── environment.yml               # conda-forge environment for PyMC on Windows
├── swiss_uefa_qualification.py   # Component A: tournament simulator
├── model.ipynb                   # Component B: hierarchical Bayesian Poisson model
├── run_pipeline.py               # orchestrates the prep/ pipeline
├── prep/                         # data preparation package
│   ├── __init__.py
│   ├── config.py                 # shared constants, paths, name mappings
│   ├── clean_results.py
│   ├── clean_teams.py
│   ├── player_features.py
│   └── build_match_dataset.py
├── data/
│   ├── raw/                      # raw dataset files (not tracked by git)
│   └── processed/                # pipeline output, e.g. match_dataset.parquet
└── plots/                        # generated figures
```

## The Data Pipeline

The `prep/` package turns the raw datasets into a single modelling table. The four steps are meant to run in sequence, since each one depends on the output of the previous:

```
clean_results.py  →  clean_teams.py  →  player_features.py  →  build_match_dataset.py
```

`clean_results.py` filters and normalises the international results. `clean_teams.py` reconciles team identities across sources. `player_features.py` aggregates Transfermarkt market values into per-team, per-department features. `build_match_dataset.py` assembles everything into `match_dataset.parquet`, a match-level table of 48 columns that serves as the input to the model.

The whole sequence is orchestrated by `run_pipeline.py`, which runs the four steps in order:

```bash
python run_pipeline.py
```

Shared configuration lives in `prep/config.py`. Two reference dates matter in particular. `DATE_FROM` is set to `2022-12-19`, the day after the 2022 World Cup final, so that only post-Qatar form is captured. `MARKET_VALUE_REF_DATE` is set to `2025-03-21`, the qualification start date, so that squad values reflect that moment. Team names are translated between English (used across the datasets and the model) and Italian (used inside the simulator) through the mapping defined in `config.py`.

## Requirements

Python 3.10 or later. The simulator in `swiss_uefa_qualification.py` depends only on the standard library and can be run without any external package. The pipeline and the model additionally require `pandas`, `numpy`, `pyarrow`, `pymc`, and `arviz`.

A note on Windows. PyMC relies on `pytensor`, whose C extensions can crash the kernel inside pip-managed virtual environments on Windows (an access violation, exit code `3221225477`, on importing PyMC). The reliable fix is a conda environment built from the `conda-forge` channel rather than a pip venv. The provided `environment.yml` sets this up:

```bash
conda env create -f environment.yml
conda activate uefa-swiss
```

If you only intend to run Component A, a plain Python installation is enough and none of this applies.

## Running the Simulator

```bash
python swiss_uefa_qualification.py
```

Configuration parameters are defined at the top of the file: number of rounds, direct qualification spots, playoff spots, bye points, and random seed. Passing a custom `prob_fn` to `SwissTournament` replaces the default FIFA-rank heuristic with any model that respects the probability signature.

## Datasets

Raw data files are not included in this repository. Download them from the sources below and place them in `data/raw/`. See the note in that folder for the exact filenames expected by the pipeline.

International football results, from 1872 to the present, come from the martj42 dataset on Kaggle. It provides match-level results for international fixtures, including tournament type, score, and a neutral-ground indicator.
https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017

Transfermarkt data comes from the dcaribou repository on GitHub. It includes `players.csv`, `player_valuations.csv`, `national_teams.csv`, and related tables covering squad market values, player positions, and FIFA rankings.
https://github.com/dcaribou/transfermarkt-datasets/tree/master

## Statistical Model, Approach

The probability model follows a Poisson framework with team-level attack and defense parameters estimated through Bayesian hierarchical inference. The core structure is:

```
log(λ_ij) = μ + α_i + β_j
```

where `α_i` is the attacking strength of team `i` and `β_j` is the defensive weakness of team `j`. The hierarchical priors on `α` and `β` shrink teams with little data towards the overall mean, which is what makes the model workable for the smaller federations. Those priors are informed by Transfermarkt market values and ELO ratings, and a temporal decay weight down-weights older fixtures during likelihood computation.

## References

Baio, G. and Blangiardo, M. (2010). Bayesian hierarchical model for the prediction of football results. *Journal of Applied Statistics*, 37(2), 253–264.

Dixon, M. J. and Coles, S. G. (1997). Modelling association football scores and inefficiencies in the football betting market. *Journal of the Royal Statistical Society: Series C*, 46(2), 265–280.

Karlis, D. and Ntzoufras, I. (2003). Analysis of sports data by using bivariate Poisson models. *Journal of the Royal Statistical Society: Series D*, 52(3), 381–393.

Foulley, J.-L. (2022). Statistical modelling of football results. ROSES Seminar No. 113.

## A Note on AI-Assisted Development

This project made extensive use of AI tools (Claude, Anthropic) throughout the coding process, including architecture design, implementation of the Swiss pairing algorithm, tiebreaker logic, the data pipeline, and dataset schema analysis. All generated code was reviewed, tested, and adapted manually. AI assistance is acknowledged transparently as part of the development workflow.

## License

This project is distributed under the MIT License.
