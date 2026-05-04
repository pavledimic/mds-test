import uuid
from pathlib import Path
from typing import List

import numpy as np

from src.files.file_record import FileRecord


class FileSource:
  def __init__(self, count: int, mean_size_mb: float) -> None:
    self._count = count
    self._mean_size_bytes = mean_size_mb * 1024 * 1024
    
  def fetch_files(self) -> List[FileRecord]:
    files = []
    for _ in range(self._count):
      size = max(1, int(np.random.exponential(self._mean_size_bytes)))
      path = Path(f"/data/nightly/{uuid.uuid4().hex}.bin")
      files.append(FileRecord(path=path, size_bytes=size))
    return files