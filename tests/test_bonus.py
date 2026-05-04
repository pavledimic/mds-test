import random

import pytest

from src.bonus.player import Player
from src.bonus.round import Round
from src.bonus.table import Table
from src.bonus.tournament import Tournament


def make_players(n: int):
    return [Player(id=i, name=f"P{i}") for i in range(n)]


def make_table(id: int, n_players: int = 4, id_offset: int = 0):
    return Table(id=id, players=[Player(id=id_offset + i, name=f"P{id_offset + i}") for i in range(n_players)])


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

class TestPlayer:
    def test_initial_wins_zero(self):
        assert Player(id=0, name="Alice").wins == 0

    def test_equality_by_id(self):
        assert Player(id=1, name="A") == Player(id=1, name="B")
        assert Player(id=1, name="A") != Player(id=2, name="A")

    def test_hashable_usable_in_set(self):
        players = {Player(id=0, name="A"), Player(id=1, name="B"), Player(id=0, name="dup")}
        assert len(players) == 2


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

class TestTable:
    def test_play_returns_one_of_the_players(self):
        table = make_table(id=0)
        rng = random.Random(42)
        winner = table.play(rng)
        assert winner in table.players

    def test_play_increments_only_winner_wins(self):
        table = make_table(id=0)
        rng = random.Random(42)
        winner = table.play(rng)
        assert winner.wins == 1
        assert sum(p.wins for p in table.players) == 1

    def test_play_stores_winner_on_table(self):
        table = make_table(id=0)
        rng = random.Random(42)
        winner = table.play(rng)
        assert table.winner is winner


# ---------------------------------------------------------------------------
# Round
# ---------------------------------------------------------------------------

class TestRound:
    def test_play_returns_one_winner_per_table(self):
        tables = [make_table(id=i, id_offset=i * 4) for i in range(3)]
        rnd = Round(id=1, tables=tables)
        winners = rnd.play(random.Random(0))
        assert len(winners) == 3
        assert all(isinstance(w, Player) for w in winners)

    def test_play_each_winner_in_their_table(self):
        tables = [make_table(id=i, id_offset=i * 4) for i in range(3)]
        rnd = Round(id=1, tables=tables)
        winners = rnd.play(random.Random(0))
        for table, winner in zip(tables, winners):
            assert winner in table.players


# ---------------------------------------------------------------------------
# Tournament
# ---------------------------------------------------------------------------

class TestTournament:
    def test_invalid_params_raise_value_error(self):
        with pytest.raises(ValueError):
            Tournament(n_players=10, n_tables=3, group_size=4)

    def test_schedule_round_correct_table_count(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=0)
        rnd = t.schedule_round()
        assert len(rnd.tables) == 3

    def test_schedule_round_correct_group_size(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=0)
        rnd = t.schedule_round()
        assert all(len(table.players) == 4 for table in rnd.tables)

    def test_schedule_round_covers_all_players(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=0)
        rnd = t.schedule_round()
        seated_ids = {p.id for table in rnd.tables for p in table.players}
        assert seated_ids == set(range(12))

    def test_no_player_seated_twice_per_round(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=7)
        rnd = t.schedule_round()
        seated = [p.id for table in rnd.tables for p in table.players]
        assert len(seated) == len(set(seated))

    def test_overall_winner_has_most_wins(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=42)
        for _ in range(5):
            t.schedule_round().play(t._rng)
        winner = t.overall_winner()
        assert winner.wins == max(p.wins for p in t.players)

    def test_standings_sorted_descending(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=7)
        for _ in range(5):
            t.schedule_round().play(t._rng)
        wins = [p.wins for p in t.standings()]
        assert wins == sorted(wins, reverse=True)

    def test_social_coverage_increases_after_round(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=1)
        before = t.social_coverage()
        t.schedule_round().play(t._rng)
        assert t.social_coverage() >= before

    def test_social_coverage_bounded_between_0_and_1(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=1)
        for _ in range(10):
            t.schedule_round().play(t._rng)
        assert 0.0 <= t.social_coverage() <= 1.0

    def test_diversity_score_non_negative(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=2)
        for _ in range(3):
            t.schedule_round().play(t._rng)
        assert t.diversity_score() >= 0.0

    def test_seed_produces_reproducible_results(self):
        def run(seed):
            t = Tournament(n_players=12, n_tables=3, group_size=4, seed=seed)
            for _ in range(5):
                t.schedule_round().play(t._rng)
            return t.overall_winner().id

        assert run(99) == run(99)

    def test_round_stored_in_history(self):
        t = Tournament(n_players=12, n_tables=3, group_size=4, seed=0)
        t.schedule_round()
        t.schedule_round()
        assert len(t.rounds) == 2
