import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Message:
  payload: Any
  id: str = field(default_factory=lambda: str(uuid.uuid4()))
  timestamp: datetime = field(default_factory=datetime.now)