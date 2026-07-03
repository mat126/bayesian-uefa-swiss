#!/usr/bin/env python3
"""
Simulatore di Qualificazioni Mondiali UEFA – Sistema Svizzero (Ipotetico)

Struttura:
  - 54 federazioni UEFA
  - N turni con abbinamenti svizzeri (no-rematch, gestione BYE)
  - Sistema 3-1-0 (vittoria-pareggio-sconfitta)
  - Alternanza casa/trasferta: color_preference score bilancia H/A per ogni squadra
  - Limitazioni geopolitiche UEFA: coppie non abbinabili (configurabili)
  - Tiebreaker: punti > vittorie > Sonneborn-Berger > Buchholz > DR > GF > ranking FIFA
  - Funzione di probabilità plug-in: sostituisci default_prob_fn col tuo modello

  Convenzione prob_fn: prob_fn(home_team, away_team) → (p_casa, p_pareggio, p_trasferta)
"""

import math
import random
from dataclasses import dataclass, field
from typing import Callable, FrozenSet, List, Optional, Set, Tuple


# =============================================================================
# CONFIGURAZIONE
# =============================================================================
N_ROUNDS             = 8     # Turni (consigliato 8-10 per 55 squadre)
DIRECT_SPOTS         = 12    # Posti qualificazione diretta
PLAYOFF_SPOTS        = 16    # Posti playoff (posizioni 14-16)
BYE_POINTS           = 1     # Punti per turno di riposo (BYE)
RANDOM_SEED          = None  # Intero per riproducibilità; None = casuale
SHOW_STANDINGS_EVERY = 2     # Mostra classifica ogni N turni

POINTS_WIN  = 3
POINTS_DRAW = 1
POINTS_LOSS = 0


# =============================================================================
# DATI SQUADRE  (nome, ranking FIFA mondiale)
# Aggiornare con i ranking FIFA attuali prima dell'uso.
# =============================================================================
UEFA_TEAMS_DATA: List[Tuple[str, int]] = [
    ("Spagna",              1),
    ("Francia",             2),
    ("Belgio",              3),
    ("Inghilterra",         5),
    ("Portogallo",          6),
    ("Paesi Bassi",         7),
    ("Italia",              9),
    ("Croazia",            10),
    ("Germania",           16),
    ("Galles",             22),
    ("Svizzera",           21),
    ("Danimarca",          20),
    ("Ucraina",            23),
    ("Austria",            24),
    ("Svezia",             25),
    ("Polonia",            26),
    ("Norvegia",           34),
    ("Serbia",             33),
    ("Repubblica Ceca",    37),
    ("Scozia",             38),
    ("Turchia",            40),
    ("Romania",            45),
    ("Slovacchia",         48),
    ("Grecia",             49),
    ("Ungheria",           50),
    ("Irlanda",            54),
    ("Slovenia",           57),
    ("Bosnia-Erzegovina",  60),
    ("Macedonia del Nord", 63),
    ("Islanda",            65),
    ("Albania",            66),
    ("Montenegro",         67),
    ("Bulgaria",           73),
    ("Georgia",            75),
    ("Israele",            80),
    ("Irlanda del Nord",   81),
    ("Lussemburgo",        84),
    ("Bielorussia",        90),
    ("Armenia",            94),
    ("Estonia",            95),
    ("Faroe",              99),
    ("Cipro",             104),
    ("Kosovo",            105),
    ("Azerbaigian",       108),
    ("Kazakhstan",        118),
    ("Lettonia",          120),
    ("Lituania",          126),
    ("Moldova",           130),
    ("Malta",             167),
    ("Andorra",           178),
    ("Gibilterra",        184),
    ("Liechtenstein",     188),
    ("San Marino",        210),
    ("Finlandia",          71),
]


# =============================================================================
# RESTRIZIONI UEFA – COPPIE NON ABBINABILI
#
# Coppie di nazionali che per motivi geopolitici/diplomatici non possono
# scontrarsi in questa simulazione.
#
# L'algoritmo le evita con priorità massima; se è impossibile (raro),
# forza il pairing con un avviso [⚠].
#
# Fonte: prassi UEFA nota + precedenti storici di rifiuto delle partite.
# Aggiungere altre coppie decommentando o aggiungendo frozenset.
# =============================================================================
RESTRICTED_PAIRS: Set[FrozenSet[str]] = {
    # La Spagna non riconosce Gibilterra come federazione calcistica
    frozenset({"Spagna", "Gibilterra"}),

    # Armenia–Azerbaigian: conflitto armato attivo, nessuna relazione diplomatica
    frozenset({"Armenia", "Azerbaigian"}),

    # Kosovo–Serbia: la Serbia non riconosce il Kosovo come stato
    frozenset({"Kosovo", "Serbia"}),

    # ── Ulteriori coppie documentate o da valutare ───────────────────────────
    # Kosovo–Bosnia-Erzegovina: posizione ambigua (Republika Srpska); hanno
    # giocato in qualche contesto UEFA ma con tensioni. Decommentare se necessario:
    # frozenset({"Kosovo", "Bosnia-Erzegovina"}),
    #
    # Kosovo–Bielorussia / Kosovo–Slovacchia: stati che non riconoscono il Kosovo
    # ma che in pratica hanno giocato in contesti UEFA. Lasciare commentate
    # a meno di evidenza specifica di rifiuto:
    # frozenset({"Kosovo", "Bielorussia"}),
}


# =============================================================================
# TEAM
# =============================================================================
@dataclass
class Team:
    name: str
    fifa_rank: int

    points: int        = 0
    wins: int          = 0
    draws: int         = 0
    losses: int        = 0
    goals_for: int     = 0
    goals_against: int = 0

    opponents: List["Team"] = field(default_factory=list)
    results_vs: dict        = field(default_factory=dict)  # nome → 'W'/'D'/'L'
    had_bye: bool           = False

    # ── Casa / Trasferta ────────────────────────────────────────────────────
    home_games: int               = 0
    away_games: int               = 0
    home_away_history: List[bool] = field(default_factory=list)  # True=casa, False=trasferta

    # ------------------------------------------------------------------
    # Proprietà derivate – statistiche
    # ------------------------------------------------------------------
    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def matches_played(self) -> int:
        return self.wins + self.draws + self.losses

    @property
    def buchholz(self) -> float:
        """Somma dei punti attuali degli avversari affrontati."""
        return float(sum(opp.points for opp in self.opponents))

    @property
    def buchholz_cut1(self) -> float:
        """Buchholz escludendo l'avversario con meno punti (BH-1)."""
        scores = sorted(opp.points for opp in self.opponents)
        return float(sum(scores[1:])) if len(scores) > 1 else float(sum(scores))

    @property
    def sonneborn_berger(self) -> float:
        """Punti avversari battuti + metà punti avversari pareggiati."""
        sb = 0.0
        for opp in self.opponents:
            r = self.results_vs.get(opp.name, "")
            if r == "W":
                sb += opp.points
            elif r == "D":
                sb += opp.points / 2.0
        return sb

    # ------------------------------------------------------------------
    # Preferenza casa/trasferta
    # ------------------------------------------------------------------
    @property
    def color_preference(self) -> float:
        """
        Score di preferenza per il prossimo ruolo casa/trasferta.

          > 0  →  vuole giocare in CASA
          < 0  →  vuole giocare in TRASFERTA
          |x|  →  intensità della preferenza

        Calcolo:
          base    = away_games - home_games   (positivo = ha più trasferte arretrate)
          streak  = +3 se ultime 2 partite entrambe in trasferta (vuole casa urgente)
                  = -3 se ultime 2 partite entrambe in casa     (vuole trasferta urgente)
        """
        base = float(self.away_games - self.home_games)

        streak_bonus = 0.0
        if len(self.home_away_history) >= 2:
            last2 = self.home_away_history[-2:]
            if not any(last2):   # 2 trasferte di fila
                streak_bonus = 3.0
            elif all(last2):     # 2 casa di fila
                streak_bonus = -3.0

        return base + streak_bonus

    # ------------------------------------------------------------------
    # Chiave di ordinamento per la classifica
    # ------------------------------------------------------------------
    def sort_key(self) -> tuple:
        return (
            self.points,
            self.wins,
            self.sonneborn_berger,
            self.buchholz,
            self.goal_difference,
            self.goals_for,
            -self.fifa_rank,      # rank più basso = più forte → invertito
        )

    def has_played(self, other: "Team") -> bool:
        return other.name in self.results_vs

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Team) and self.name == other.name

    def __repr__(self):
        return f"Team({self.name}, rank={self.fifa_rank}, pts={self.points})"


# =============================================================================
# TORNEO SVIZZERO
# =============================================================================
class SwissTournament:
    def __init__(
        self,
        teams: List[Team],
        n_rounds: int = N_ROUNDS,
        direct_spots: int = DIRECT_SPOTS,
        playoff_spots: int = PLAYOFF_SPOTS,
        restricted_pairs: Optional[Set[FrozenSet[str]]] = None,
        prob_fn: Optional[Callable] = None,
        seed: Optional[int] = None,
    ):
        self.teams            = teams
        self.n_rounds         = n_rounds
        self.direct_spots     = direct_spots
        self.playoff_spots    = playoff_spots
        self.restricted_pairs = restricted_pairs if restricted_pairs is not None else RESTRICTED_PAIRS
        self.prob_fn          = prob_fn or default_prob_fn
        self.current_round    = 0
        self.round_history: List[List[dict]] = []

        if seed is not None:
            random.seed(seed)

    # ------------------------------------------------------------------
    # Classifica
    # ------------------------------------------------------------------
    def standings(self) -> List[Team]:
        return sorted(self.teams, key=lambda t: t.sort_key(), reverse=True)

    # ------------------------------------------------------------------
    # Verifica restrizione
    # ------------------------------------------------------------------
    def _is_restricted(self, t1: Team, t2: Team) -> bool:
        """True se la coppia non può giocare per motivi geopolitici."""
        return frozenset({t1.name, t2.name}) in self.restricted_pairs

    # ------------------------------------------------------------------
    # Assegnazione casa/trasferta
    # ------------------------------------------------------------------
    def _assign_home_away(self, t1: Team, t2: Team) -> Tuple[Team, Team]:
        """
        Assegna i ruoli casa/trasferta minimizzando gli squilibri di alternanza.
        La squadra con color_preference più alta riceve il ruolo casa.
        In caso di parità, t1 (posizione più alta in classifica) gioca in casa.

        Restituisce (home_team, away_team).
        """
        if t1.color_preference >= t2.color_preference:
            return (t1, t2)
        else:
            return (t2, t1)

    # ------------------------------------------------------------------
    # Abbinamenti svizzeri
    # ------------------------------------------------------------------
    def _generate_pairings(self) -> Tuple[List[Tuple[Team, Team]], Optional[Team]]:
        """
        Algoritmo greedy con tre livelli di priorità decrescente:

          Priorità 1: no rematch  +  no restrizione  →  casa/trasferta bilanciati
          Priorità 2: no rematch  (restrizione accettata se inevitabile) [⚠]
          Priorità 3: rematch forzato (caso estremo, con avviso)         [⚠]

        BYE assegnato alla squadra con punteggio più basso che non ha ancora riposato.

        Restituisce: (lista di (home_team, away_team), bye_team | None)
        """
        ordered = self.standings()
        bye_team: Optional[Team] = None

        # ── Gestione numero dispari ──────────────────────────────────────────
        if len(ordered) % 2 == 1:
            for t in reversed(ordered):
                if not t.had_bye:
                    bye_team = t
                    break
            if bye_team is None:
                bye_team = ordered[-1]          # fallback: ultima in classifica
            bye_team.had_bye = True
            bye_team.points += BYE_POINTS
            ordered = [t for t in ordered if t is not bye_team]

        # ── Abbinamento greedy ───────────────────────────────────────────────
        available = list(ordered)
        pairings:  List[Tuple[Team, Team]] = []

        while len(available) >= 2:
            team1 = available.pop(0)
            paired = False

            # Priorità 1: no rematch + no restrizione
            for i, team2 in enumerate(available):
                if not team1.has_played(team2) and not self._is_restricted(team1, team2):
                    pairings.append(self._assign_home_away(team1, team2))
                    available.pop(i)
                    paired = True
                    break

            if not paired:
                # Priorità 2: no rematch (restrizione inevitabile, segnalata)
                for i, team2 in enumerate(available):
                    if not team1.has_played(team2):
                        pairings.append(self._assign_home_away(team1, team2))
                        available.pop(i)
                        paired = True
                        print(f"  [⚠] Pairing ristretto forzato: {team1.name} vs {team2.name}")
                        break

            if not paired:
                # Priorità 3: rematch forzato
                team2 = available.pop(0)
                pairings.append(self._assign_home_away(team1, team2))
                print(f"  [⚠] Rematch forzato: {team1.name} vs {team2.name}")

        return pairings, bye_team

    # ------------------------------------------------------------------
    # Simulazione partita
    # ------------------------------------------------------------------
    def _simulate_match(self, home_team: Team, away_team: Team) -> dict:
        """
        Simula una partita con ruoli casa/trasferta espliciti.
        Aggiorna home_games/away_games/home_away_history per entrambe le squadre.

        Convenzione prob_fn:
            prob_fn(home_team, away_team) → (p_casa_vince, p_pareggio, p_trasferta_vince)
        """
        p_home, p_draw, p_away = self.prob_fn(home_team, away_team)

        # Normalizzazione di sicurezza
        total   = p_home + p_draw + p_away
        p_home /= total
        p_draw /= total

        r = random.random()
        if r < p_home:
            outcome = "H"
        elif r < p_home + p_draw:
            outcome = "D"
        else:
            outcome = "A"

        score = _generate_score(outcome)   # (gol_casa, gol_trasferta)

        # ── Aggiorna home_team ───────────────────────────────────────────────
        home_team.opponents.append(away_team)
        home_team.home_games            += 1
        home_team.home_away_history.append(True)
        home_team.goals_for             += score[0]
        home_team.goals_against         += score[1]

        # ── Aggiorna away_team ───────────────────────────────────────────────
        away_team.opponents.append(home_team)
        away_team.away_games            += 1
        away_team.home_away_history.append(False)
        away_team.goals_for             += score[1]
        away_team.goals_against         += score[0]

        # ── Punti e risultati ────────────────────────────────────────────────
        if outcome == "H":
            home_team.points += POINTS_WIN
            home_team.wins   += 1
            away_team.losses += 1
            home_team.results_vs[away_team.name] = "W"
            away_team.results_vs[home_team.name] = "L"
        elif outcome == "D":
            home_team.points += POINTS_DRAW
            home_team.draws  += 1
            away_team.points += POINTS_DRAW
            away_team.draws  += 1
            home_team.results_vs[away_team.name] = "D"
            away_team.results_vs[home_team.name] = "D"
        else:  # "A"
            away_team.points += POINTS_WIN
            away_team.wins   += 1
            home_team.losses += 1
            away_team.results_vs[home_team.name] = "W"
            home_team.results_vs[away_team.name] = "L"

        return {
            "home_team": home_team,
            "away_team": away_team,
            "score":     score,
            "outcome":   outcome,   # 'H' / 'D' / 'A'
        }

    # ------------------------------------------------------------------
    # Esecuzione turno
    # ------------------------------------------------------------------
    def run_round(self, verbose: bool = True) -> List[dict]:
        self.current_round += 1
        pairings, bye_team = self._generate_pairings()
        results: List[dict] = []

        if verbose:
            print(f"\n{'═' * 80}")
            print(f"  TURNO {self.current_round} / {self.n_rounds}")
            print(f"{'═' * 80}")
            if bye_team:
                print(f"  BYE  ►  {bye_team.name}  (+{BYE_POINTS} pt)\n")

        for home_t, away_t in pairings:
            res = self._simulate_match(home_t, away_t)
            results.append(res)
            if verbose:
                h, a = res["score"]
                out  = res["outcome"]
                # ◄ = casa vince  = = pareggio  ► = trasferta vince
                arrow = "◄" if out == "H" else ("►" if out == "A" else "=")
                # Mostra bilancio C/T di ogni squadra dopo questa partita
                balance_h = f"{home_t.home_games}c/{home_t.away_games}t"
                balance_a = f"{away_t.home_games}c/{away_t.away_games}t"
                print(
                    f"  [C] {home_t.name:<24}  {h} {arrow} {a}"
                    f"  {away_t.name:<24} [T]"
                    f"   {balance_h} | {balance_a}"
                )

        self.round_history.append(results)
        return results

    # ------------------------------------------------------------------
    # Stampa classifica
    # ------------------------------------------------------------------
    def print_standings(self, top_n: Optional[int] = None) -> None:
        rows = self.standings()
        if top_n:
            rows = rows[:top_n]

        hdr = (
            f"{'#':>3}  {'Squadra':<25} {'Pt':>4}  "
            f"{'V':>3} {'P':>3} {'S':>3}  "
            f"{'GF':>4} {'GS':>4} {'DR':>4}  "
            f"{'C/T':>5}  "
            f"{'Buch':>7}  {'S-B':>7}"
        )
        sep = "─" * len(hdr)

        print(f"\n  Classifica – dopo il Turno {self.current_round}")
        print(f"  {sep}")
        print(f"  {hdr}")
        print(f"  {sep}")

        for i, t in enumerate(rows, 1):
            if i <= self.direct_spots:
                marker = "✓"
            elif i <= self.direct_spots + self.playoff_spots:
                marker = "○"
            else:
                marker = " "

            ct = f"{t.home_games}/{t.away_games}"
            print(
                f"  {i:>3}{marker} {t.name:<25} {t.points:>4}  "
                f"{t.wins:>3} {t.draws:>3} {t.losses:>3}  "
                f"{t.goals_for:>4} {t.goals_against:>4} {t.goal_difference:>+4}  "
                f"{ct:>5}  "
                f"{t.buchholz:>7.1f}  {t.sonneborn_berger:>7.1f}"
            )

        print(f"  {sep}")
        print(f"  ✓ qualificata diretta  ○ playoff  C/T = partite in casa / in trasferta")
        print(f"  Buch = Buchholz   S-B = Sonneborn-Berger")

    # ------------------------------------------------------------------
    # Risultati finali
    # ------------------------------------------------------------------
    def print_final_results(self) -> None:
        rows = self.standings()
        print(f"\n{'═' * 80}")
        print("  QUALIFICAZIONI MONDIALI UEFA – RISULTATI FINALI")
        print(f"{'═' * 80}\n")

        print(f"  🏆  QUALIFICATE DIRETTE ({self.direct_spots} posti):")
        for i, t in enumerate(rows[: self.direct_spots], 1):
            print(
                f"       {i:>2}. {t.name:<25}  {t.points:>2} pt  "
                f"({t.wins}V {t.draws}P {t.losses}S  "
                f"DR {t.goal_difference:+}  {t.home_games}C/{t.away_games}T)"
            )

        print(f"\n  ⚔️   PLAYOFF ({self.playoff_spots} posti):")
        for i, t in enumerate(
            rows[self.direct_spots : self.direct_spots + self.playoff_spots],
            self.direct_spots + 1,
        ):
            print(
                f"       {i:>2}. {t.name:<25}  {t.points:>2} pt  "
                f"({t.wins}V {t.draws}P {t.losses}S  "
                f"DR {t.goal_difference:+}  {t.home_games}C/{t.away_games}T)"
            )

        print(f"\n  ❌  ELIMINATE ({len(rows) - self.direct_spots - self.playoff_spots}):")
        for i, t in enumerate(
            rows[self.direct_spots + self.playoff_spots :],
            self.direct_spots + self.playoff_spots + 1,
        ):
            print(
                f"       {i:>2}. {t.name:<25}  {t.points:>2} pt  "
                f"({t.home_games}C/{t.away_games}T)"
            )

    # ------------------------------------------------------------------
    # Run completo
    # ------------------------------------------------------------------
    def run(
        self,
        verbose_rounds: bool = True,
        show_standings_every: int = SHOW_STANDINGS_EVERY,
    ) -> None:
        n = len(self.teams)
        print(f"\n  {'═' * 78}")
        print("  SIMULAZIONE QUALIFICAZIONI MONDIALI UEFA – SISTEMA SVIZZERO")
        print(
            f"  Squadre: {n}  |  Turni: {self.n_rounds}  |  "
            f"Qualificate: {self.direct_spots} dirette + {self.playoff_spots} playoff"
        )
        r_lines = [f"    • {sorted(p)[0]} ↔ {sorted(p)[1]}" for p in self.restricted_pairs]
        print(f"  Restrizioni attive ({len(self.restricted_pairs)}):")
        for line in sorted(r_lines):
            print(line)
        print(f"  {'═' * 78}")

        for rnd in range(self.n_rounds):
            self.run_round(verbose=verbose_rounds)
            if (rnd + 1) % show_standings_every == 0:
                self.print_standings()

        self.print_final_results()


# =============================================================================
# GENERAZIONE PUNTEGGIO REALISTICO
# =============================================================================
def _generate_score(outcome: str) -> Tuple[int, int]:
    """
    Genera un risultato numerico realistico per una partita di calcio.
    outcome: 'H' casa vince, 'D' pareggio, 'A' trasferta vince.
    Restituisce (gol_casa, gol_trasferta).
    """
    if outcome == "D":
        g = random.choices([0, 1, 2, 3], weights=[15, 45, 30, 10])[0]
        return (g, g)
    elif outcome == "H":
        g1 = random.choices([1, 2, 3, 4, 5], weights=[30, 35, 20, 10, 5])[0]
        g2 = random.randint(0, g1 - 1)
        return (g1, g2)
    else:  # "A"
        g2 = random.choices([1, 2, 3, 4, 5], weights=[30, 35, 20, 10, 5])[0]
        g1 = random.randint(0, g2 - 1)
        return (g1, g2)


# =============================================================================
# FUNZIONE PROBABILITÀ PLACEHOLDER
# =============================================================================
def default_prob_fn(home_team: Team, away_team: Team) -> Tuple[float, float, float]:
    """
    Probabilità placeholder basata sul ranking FIFA.
    """
    diff = away_team.fifa_rank - home_team.fifa_rank   # positivo = home più forte

    p_home_base = 1.0 / (1.0 + math.exp(-diff / 20.0))
    p_draw      = 0.28 * math.exp(-((diff / 40.0) ** 2))
    p_draw      = max(0.08, min(0.30, p_draw))
    p_home      = p_home_base * (1.0 - p_draw)
    p_away      = 1.0 - p_home - p_draw

    return p_home, p_draw, p_away


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    # Rimuovi duplicati (mantieni prima occorrenza)
    seen: set = set()
    unique: List[Tuple[str, int]] = []
    for entry in UEFA_TEAMS_DATA:
        if entry[0] not in seen:
            seen.add(entry[0])
            unique.append(entry)

    teams = [Team(name=name, fifa_rank=rank) for name, rank in unique]
    print(f"  Squadre caricate: {len(teams)}")

    tournament = SwissTournament(
        teams=teams,
        n_rounds=N_ROUNDS,
        direct_spots=DIRECT_SPOTS,
        playoff_spots=PLAYOFF_SPOTS,
        restricted_pairs=RESTRICTED_PAIRS,
        prob_fn=default_prob_fn,    # <── sostituire con il proprio modello
        seed=RANDOM_SEED,
    )

    tournament.run(
        verbose_rounds=True,
        show_standings_every=SHOW_STANDINGS_EVERY,
    )
