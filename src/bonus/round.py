from dataclasses import dataclass, field

import random
from typing import List

from src.bonus.player import Player
from src.bonus.table import Table


@dataclass
class Round:
  id: int
  tables: List[Table] = field(default_factory=list)

  def play(self, rng: random.Random) -> List[Player]:
      return [table.play(rng) for table in self.tables]