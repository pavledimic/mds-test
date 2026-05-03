import queue
import threading
import time
import uuid
from typing import Iterator

import numpy as np

# from src.interfaces.data_source import IDataSource
from src.streaming.message import Message

class PoissonDataSource:
  def __init__(self, rate_per_minute: float = 10.0) -> None:
    self._rate_per_second = rate_per_minute / 60.0
    self._stop_event = threading.Event()
    self._queue: queue.Queue[Message] = queue.Queue()
    
  def stream(self) -> Iterator[Message]:
    producer = threading.Thread(target=self._produce)
    producer.start()
    while not self._stop_event.is_set() or not self._queue.empty():
      try:
        yield self._queue.get(timeout=0.5)    
      except queue.Empty:
        continue
      
  def stop(self) -> None:
        self._stop_event.set()    
  
  def _produce(self):
    while not self._stop_event.is_set():
      interval = np.random.exponential(1.0 / self._rate_per_second)
      time.sleep(interval)
      if not self._stop_event.is_set():
        self._queue.put(Message(payload={"data": uuid.uuid4().hex}))