from dataclasses import dataclass, field
from typing import List

from src.files.file_record import FileRecord


@dataclass
class FileBucket:
    max_size_bytes: int
    files: List[FileRecord] = field(default_factory=list)

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)

    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)

    def can_fit(self, file: FileRecord) -> bool:
        return self.total_size_bytes + file.size_bytes <= self.max_size_bytes

    def add(self, file: FileRecord) -> None:
        self.files.append(file)

    def __len__(self) -> int:
        return len(self.files)