import logging
from typing import Callable, Optional

from src.files.file_bucket import FileBucket
from src.worker.worker_pool import WorkerPool

logger = logging.getLogger(__name__)


class NightlyProcessor:

  def __init__(
      self,
      file_source,
      bucketing_strategy,
      worker_pool: WorkerPool,
      processor: Optional[Callable[[FileBucket], None]] = None,
  ) -> None:
      self._source = file_source
      self._strategy = bucketing_strategy
      self._pool = worker_pool
      self._processor: Callable[[FileBucket], None] = (
          processor or self._log_bucket
      )

  def run(self) -> None:
      logger.info("Nightly processing started")
      files = self._source.fetch_files()
      logger.info("Fetched %d files", len(files))

      buckets = self._strategy.bucket(files)
      logger.info(
          "Packed into %d buckets (strategy: %s)",
          len(buckets),
          type(self._strategy).__name__,
      )

      futures = [self._pool.submit(self._processor, b) for b in buckets]
      for f in futures:
          f.result()

      logger.info("Nightly processing complete")

  @staticmethod
  def _log_bucket(bucket: FileBucket) -> None:
      logger.info(
          "Processed bucket: %d files, %.2f MB", len(bucket), bucket.total_size_mb
      )
