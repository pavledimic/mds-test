from dataclasses import dataclass

@dataclass
class Player:
  id: int
  name: str
  wins: int = 0

  def __hash__(self) -> int:
    return hash(self.id)

  def __eq__(self, other: object) -> bool:
    return isinstance(other, Player) and self.id == other.id