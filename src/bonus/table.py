from dataclasses import dataclass

from typing import Optional, List
import random

from src.bonus.player import Player


@dataclass
class Table:
  id: int
  players: List[Player]
  winner: Optional[Player] = None

  def play(self, rng: random.Random) -> Player:
    self.winner = rng.choice(self.players)
    self.winner.wins += 1
    return self.winner