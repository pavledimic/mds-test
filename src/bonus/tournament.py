

import random
from itertools import combinations
from typing import Dict, List, Tuple

from src.bonus.player import Player
from src.bonus.table import Table
from src.bonus.round import Round


class Tournament:
  def __init__(self, n_players: int, n_tables: int, group_size: int, seed: int = None) -> None:
    if n_players != n_tables * group_size:
      raise ValueError("Number of players must be equal to n_tables * group_size")

    self.n_players = n_players
    self.n_tables = n_tables
    self.group_size = group_size

    self.players: List[Player] = [Player(id=i, name=f"Player {i + 1}") for i in range(n_players)]
    self.rounds: List[Round] = []
    self._pair_weight: Dict[Tuple[int, int], int] = {}
    self._rng = random.Random(seed)
    
  def schedule_round(self, max_restarts: int = 10, max_iter: int = 2000) -> Round:
    best_assignment, best_score = self._best_assignment(max_restarts, max_iter)
    self._update_pair_weights(best_assignment)

    tables = [
      Table(id=i, players=[self.players[pid] for pid in group]) for i, group in enumerate(best_assignment)
    ]
    rnd = Round(id=len(self.rounds) + 1, tables=tables)
    self.rounds.append(rnd)
    return rnd

  def run_tournament(self, n_rounds: int) -> Player:
    for _ in range(n_rounds):
      rnd = self.schedule_round()
      rnd.play(self._rng)
    return self.overall_winner()

  def overall_winner(self) -> Player:
    return max(self.players, key=lambda p: p.wins)

  def standings(self) -> List[Player]:
    return sorted(self.players, key=lambda p: p.wins, reverse=True)

  def social_coverage(self) -> float:
    total = self.n_players * (self.n_players - 1) // 2
    return len(self._pair_weight) / total if total else 0.0

  def diversity_score(self) -> float:
    unique_opponents: Dict[int, set] = {p.id: set() for p in self.players}
    for (a, b), count in self._pair_weight.items():
      if count > 0:
        unique_opponents[a].add(b)
        unique_opponents[b].add(a)
    if not self.players:
      return 0.0
    return sum(len(v) for v in unique_opponents.values()) / len(self.players)

  # HELPERS
  
  def _conflict_score(self, assignment: List[List[int]]) -> int:
    score = 0
    for group in assignment:
      for a, b in combinations(group, 2):
        score += self._pair_weight.get(self._key(a, b), 0)
    return score

  def _local_search(self, assignment: List[List[int]], max_iter: int) -> Tuple[List[List[int]], int]:
      current = [list(g) for g in assignment]
      current_score = self._conflict_score(current)

      for _ in range(max_iter):
        if current_score == 0:
          break
        t1, t2 = self._rng.sample(range(self.n_tables), 2)
        i1 = self._rng.randrange(self.group_size)
        i2 = self._rng.randrange(self.group_size)

        candidate = [list(g) for g in current]
        candidate[t1][i1], candidate[t2][i2] = candidate[t2][i2], candidate[t1][i1]
        candidate_score = self._conflict_score(candidate)

        if candidate_score <= current_score:
          current, current_score = candidate, candidate_score

      return current, current_score

  def _best_assignment(self, max_restarts: int, max_iter: int) -> Tuple[List[List[int]], int]:
    ids = list(range(self.n_players))
    best_assignment: List[List[int]] = []
    best_score = float("inf")

    for _ in range(max_restarts):
      self._rng.shuffle(ids)
      assignment = [
        ids[i * self.group_size: (i + 1) * self.group_size]
        for i in range(self.n_tables)
      ]
      assignment, score = self._local_search(assignment, max_iter)
      if score < best_score:
        best_score = score
        best_assignment = assignment

    return best_assignment, int(best_score)

  def _update_pair_weights(self, assignment: List[List[int]]) -> None:
    for group in assignment:
      for a, b in combinations(group, 2):
        k = self._key(a, b)
        self._pair_weight[k] = self._pair_weight.get(k, 0) + 1

  @staticmethod
  def _key(a: int, b: int) -> Tuple[int, int]:
      return (min(a, b), max(a, b))

  