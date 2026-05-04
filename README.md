# MDS Data Engineering Test

Three independent systems implemented in Python, runnable via Docker or locally.

---

## Project structure

```
.
├── main.py                  # Single entry point with subcommands
├── config.py                # Default values for all parameters
├── src/
│   ├── streaming/           # Mini-batch message processing
│   ├── files/               # Nightly file bucketing & processing
│   ├── bonus/               # Tournament scheduling optimizer
│   └── worker/              # Shared thread-pool worker
└── tests/
```

---

## Running with Docker (recommended)

### Build once

```bash
docker build -t mds-test .
```

### Streaming — mini-batch message processing

Simulates a Poisson data source (~10 msg/min). Incoming messages are grouped into
5-minute mini-batches and dispatched to a 10-thread worker pool.

```bash
# Default values (rate=10 msg/min, window=300s, duration=600s, workers=10)
docker run --rm mds-test streaming

# Custom run — short demo
docker run --rm mds-test streaming --rate 10 --window 5 --duration 30
```

| Flag | Default | Description |
|------|---------|-------------|
| `--rate` | `10.0` | Messages per minute (Poisson rate) |
| `--window` | `300` | Batch window in seconds |
| `--duration` | `600` | Total simulation duration in seconds |
| `--workers` | `10` | Worker pool size |

### Files — nightly file bucketing

Generates 100 files with exponentially distributed sizes and packs them into
10 MB buckets before sending each bucket to a worker.

```bash
# Default values (100 files, 10 MB buckets, mean file size 2 MB)
docker run --rm mds-test files

# Custom run
docker run --rm mds-test files --files 50 --bucket-size 5 --mean-size 1.5
```

| Flag | Default | Description |
|------|---------|-------------|
| `--files` | `100` | Number of files to generate |
| `--bucket-size` | `10.0` | Target bucket size in MB |
| `--mean-size` | `2.0` | Mean file size in MB (exponential distribution) |
| `--workers` | `10` | Worker pool size |

### Bonus — tournament scheduler

Finds a seating schedule for N players across T tables (G players per table)
that maximises opponent diversity across rounds while tracking a tournament winner.

```bash
# Default values (12 players, 3 tables, 4 per table, 5 rounds)
docker run --rm mds-test bonus

# Custom run — reproducible with seed
docker run --rm mds-test bonus --players 12 --tables 3 --group-size 4 --rounds 10 --seed 42
```

> **Constraint:** `--players` must equal `--tables × --group-size`.

| Flag | Default | Description |
|------|---------|-------------|
| `--players` | `12` | Total number of participants |
| `--tables` | `3` | Number of tables |
| `--group-size` | `4` | Players per table |
| `--rounds` | `5` | Number of rounds to play |
| `--seed` | `None` | Random seed for reproducibility |

### docker compose shortcuts

```bash
docker compose run streaming
docker compose run files
docker compose run bonus
```

---

## Running locally

**Requirements:** Python 3.11+

```bash
pip install -r requirements.txt

python main.py streaming --rate 10 --window 5 --duration 30
python main.py files --files 100
python main.py bonus --rounds 5 --seed 42
```

---

## Running tests

```bash
# Locally
pytest

# Inside Docker
docker run --rm --entrypoint pytest mds-test
```
