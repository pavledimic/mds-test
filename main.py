import argparse
import logging
import threading
import time

import config
from src.streaming.minibatch import MiniBatch
from src.streaming.minibatch_manager import MiniBatchManager
from src.streaming.poisson_data_source import PoissonDataSource
from src.worker.worker_pool import WorkerPool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def process_batch(batch: MiniBatch) -> None:
    logger.info(
      "  [worker] batch %s: %d messages (window %.2f s)",
      batch.id[:8],
      len(batch),
      (batch.closed_at - batch.created_at).total_seconds(),
    )
    

def run_streaming(
    pool: WorkerPool,
    rate_per_minute: float,
    window_seconds: float,
    duration_seconds: float,
) -> None:
    logger.info("=== Starting streaming for %.1f seconds", duration_seconds)

    source = PoissonDataSource(rate_per_minute=rate_per_minute)
    manager = MiniBatchManager(
        worker_pool=pool,
        window_seconds=window_seconds,
        processor=process_batch,
    )

    def consume():
        for msg in source.stream():
            manager.on_message(msg)

    consumer = threading.Thread(target=consume, name="stream-consumer", daemon=True)
    consumer.start()

    time.sleep(duration_seconds)
    source.stop()
    manager.flush()
    time.sleep(0.5)
    logger.info("=== Streaming stopped ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mini-batch streaming demo")
    parser.add_argument("--rate", type=float, default=config.RATE_PER_MINUTE, help="Messages per minute")
    parser.add_argument("--window", type=float, default=config.WINDOW_SECONDS, help="Batch window in seconds")
    parser.add_argument("--duration", type=float, default=config.DURATION_SECONDS, help="Total run duration in seconds")
    parser.add_argument("--workers", type=int, default=config.MAX_WORKERS, help="Worker pool size")
    args = parser.parse_args()

    with WorkerPool(max_workers=args.workers) as pool:
        run_streaming(
            pool,
            rate_per_minute=args.rate,
            window_seconds=args.window,
            duration_seconds=args.duration,
        )
    