import logging
import threading
from typing import Callable, Optional

from src.streaming.message import Message
from src.streaming.minibatch import MiniBatch
from src.worker.worker_pool import WorkerPool

logger = logging.getLogger(__name__)

class MiniBatchManager:
  def __init__(
    self, 
    worker_pool: WorkerPool,
    window_seconds: float = 300.0,
    processor: Optional[Callable[[MiniBatch], None]] = None
  ) -> None:
    self._pool = worker_pool
    self._window_seconds = window_seconds
    self._processor: Callable[[MiniBatch], None] = processor or self._log_batch
    self._current_batch: MiniBatch | None = None
    self._lock = threading.Lock()
    self._timer: Optional[threading.Timer] = None
  
  def on_message(self, message: Message) -> None:
    with self._lock:
      if self._current_batch is None:
        self._open_batch(message)
      else:
        self._current_batch.add(message)
        
  def flush(self) -> None:
    with self._lock:
      if self._timer is not None:
        self._timer.cancel()
        self._timer = None
    self._close_and_submit()

        
  def _open_batch(self, first_message: Message) -> None:
    batch = MiniBatch()
    batch.add(first_message)
    self._current_batch = batch
    
    timer = threading.Timer(self._window_seconds, self._close_and_submit)
    timer.daemon = True
    timer.start()
    self._timer = timer
    logger.info("Opened mini-batch %s", batch.id)
    
  def _close_and_submit(self) -> None:
    with self._lock:
        batch = self._current_batch
        self._current_batch = None
        self._timer = None

    if batch is None:
        return

    batch.close()
    logger.info(
        "Submitting mini-batch %s (%d messages)", batch.id, len(batch)
    )
    try:
        self._pool.submit(self._processor, batch)
    except RuntimeError:
        logger.debug("Worker pool shut down; mini-batch %s discarded.", batch.id)
        
  @staticmethod
  def _log_batch(batch: MiniBatch) -> None:
    logger.info(
        "Processing mini-batch %s with %d messages (window %.2f s)",
        batch.id,
        len(batch),
        (batch.closed_at - batch.created_at).total_seconds(),
    )