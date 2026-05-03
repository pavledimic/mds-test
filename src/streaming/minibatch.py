import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.streaming.message import Message

@dataclass
class MiniBatch:
  id: str = field(default_factory=lambda: str(uuid.uuid4()))
  messages: List[Message] = field(default_factory=list)
  created_at: datetime = field(default_factory=datetime.now)
  closed_at: Optional[datetime] = None
  
  def add(self, message: Message):
    self.messages.append(message)
  
  def close(self):
    self.closed_at = datetime.now()
    
  def __len__(self) -> int:
    return len(self.messages)