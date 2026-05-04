from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileRecord:
  path: Path
  size_bytes: int

  @property
  def size_mb(self) -> float:
    return self.size_bytes / (1024 * 1024)
