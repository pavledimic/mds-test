import argparse
import logging
import threading
import time

import config
from src.bonus.tournament import Tournament
from src.files.file_bucket import FileBucket
from src.files.file_processor import NightlyProcessor
from src.files.file_source import FileSource
from src.files.size_file_strategy import SizeFileStrategy
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


def process_batch(batch: MiniBatch) -> None:
  logger.info(
    "[worker] batch %s: %d messages (window %.2f s)",
    batch.id[:8],
    len(batch),
    (batch.closed_at - batch.created_at).total_seconds(),
  )


def process_bucket(bucket: FileBucket) -> None:
  logger.info(
    "[worker] bucket: %d files, %.2f MB",
    len(bucket),
    bucket.total_size_mb,
  )


def run_streaming(pool: WorkerPool, args: argparse.Namespace) -> None:
  logger.info("=== Streaming started (duration=%.0fs) ===", args.duration)

  source = PoissonDataSource(rate_per_minute=args.rate)
  manager = MiniBatchManager(
    worker_pool=pool,
    window_seconds=args.window,
    processor=process_batch,
  )

  def consume():
    for msg in source.stream():
      manager.on_message(msg)

  consumer = threading.Thread(target=consume, name="stream-consumer", daemon=True)
  consumer.start()

  time.sleep(args.duration)
  source.stop()
  manager.flush()
  time.sleep(0.5)
  logger.info("=== Streaming stopped ===")


def run_files(pool: WorkerPool, args: argparse.Namespace) -> None:
  logger.info("=== Nightly file processing started (files=%d, bucket=%.0f MB) ===",
              args.files, args.bucket_size)

  source = FileSource(count=args.files, mean_size_mb=args.mean_size)
  strategy = SizeFileStrategy(bucket_size_mb=args.bucket_size)
  processor = NightlyProcessor(
    file_source=source,
    bucketing_strategy=strategy,
    worker_pool=pool,
    processor=process_bucket,
  )
  processor.run()
  logger.info("=== Nightly file processing complete ===")


def run_bonus(args: argparse.Namespace) -> None:
  logger.info(
    "=== Tournament started (players=%d, tables=%d, group=%d, rounds=%d) ===",
    args.players, args.tables, args.group_size, args.rounds,
  )

  t = Tournament(
    n_players=args.players,
    n_tables=args.tables,
    group_size=args.group_size,
    seed=args.seed,
  )

  for rnd_num in range(1, args.rounds + 1):
    rnd = t.schedule_round()
    winners = rnd.play(t._rng)
    logger.info(
      "Round %d — table winners: %s",
      rnd_num,
      ", ".join(w.name for w in winners),
    )

  logger.info("--- Standings ---")
  for rank, player in enumerate(t.standings(), start=1):
    logger.info("  %d. %s — %d win(s)", rank, player.name, player.wins)

  winner = t.overall_winner()
  logger.info("Tournament winner: %s", winner.name)
  logger.info(
    "Social coverage: %.1f%%  |  Avg unique opponents: %.2f",
    t.social_coverage() * 100,
    t.diversity_score(),
  )
  logger.info("=== Tournament complete ===")


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description="MDS Data Engineering Demo")
  parser.add_argument("--workers", type=int, default=config.MAX_WORKERS,
                      help="Worker pool size (default: %(default)s)")

  sub = parser.add_subparsers(dest="command", required=True)

  stream_p = sub.add_parser("streaming", help="Run mini-batch streaming demo")
  stream_p.add_argument("--rate", type=float, default=config.RATE_PER_MINUTE,
                        help="Messages per minute (default: %(default)s)")
  stream_p.add_argument("--window", type=float, default=config.WINDOW_SECONDS,
                        help="Batch window in seconds (default: %(default)s)")
  stream_p.add_argument("--duration", type=float, default=config.DURATION_SECONDS,
                        help="Total run duration in seconds (default: %(default)s)")

  files_p = sub.add_parser("files", help="Run nightly file bucketing demo")
  files_p.add_argument("--files", type=int, default=config.FILE_COUNT,
                       help="Number of files to generate (default: %(default)s)")
  files_p.add_argument("--bucket-size", type=float, default=config.BUCKET_SIZE_MB,
                       dest="bucket_size",
                       help="Bucket size in MB (default: %(default)s)")
  files_p.add_argument("--mean-size", type=float, default=config.MEAN_FILE_SIZE_MB,
                       dest="mean_size",
                       help="Mean file size in MB / exp distribution (default: %(default)s)")

  bonus_p = sub.add_parser("bonus", help="Run tournament scheduling demo")
  bonus_p.add_argument("--players", type=int, default=config.TOURNAMENT_PLAYERS,
                       help="Total number of players — must equal tables * group-size (default: %(default)s)")
  bonus_p.add_argument("--tables", type=int, default=config.TOURNAMENT_TABLES,
                       help="Number of tables (default: %(default)s)")
  bonus_p.add_argument("--group-size", type=int, default=config.TOURNAMENT_GROUP_SIZE,
                       dest="group_size",
                       help="Players per table (default: %(default)s)")
  bonus_p.add_argument("--rounds", type=int, default=config.TOURNAMENT_ROUNDS,
                       help="Number of rounds to play (default: %(default)s)")
  bonus_p.add_argument("--seed", type=int, default=None,
                       help="Random seed for reproducibility (default: None)")

  return parser


if __name__ == "__main__":
  args = build_parser().parse_args()

  with WorkerPool(max_workers=args.workers) as pool:
    if args.command == "streaming":
      run_streaming(pool, args)
    elif args.command == "files":
      run_files(pool, args)

  if args.command == "bonus":
    run_bonus(args)
