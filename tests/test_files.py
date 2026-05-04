from pathlib import Path

import pytest

from src.files.file_bucket import FileBucket
from src.files.file_processor import NightlyProcessor
from src.files.file_record import FileRecord
from src.files.size_file_strategy import SizeFileStrategy
from src.worker.worker_pool import WorkerPool

MB = 1024 * 1024


def make_file(size_mb: float, name: str = "f.bin") -> FileRecord:
    return FileRecord(path=Path(f"/data/{name}"), size_bytes=int(size_mb * MB))


class MockFileSource:
    """Returns a predetermined list of FileRecords — no filesystem, no randomness."""

    def __init__(self, files):
        self._files = list(files)

    def fetch_files(self):
        return list(self._files)


# ---------------------------------------------------------------------------
# FileRecord
# ---------------------------------------------------------------------------

class TestFileRecord:
    def test_size_mb_conversion(self):
        f = make_file(5.0)
        assert abs(f.size_mb - 5.0) < 0.01

    def test_immutable(self):
        f = make_file(1.0)
        with pytest.raises(Exception):
            f.size_bytes = 0


# ---------------------------------------------------------------------------
# FileBucket
# ---------------------------------------------------------------------------

class TestFileBucket:
    def test_empty_bucket_has_zero_size(self):
        bucket = FileBucket(max_size_bytes=10 * MB)
        assert bucket.total_size_bytes == 0
        assert len(bucket) == 0

    def test_can_fit_exact_capacity(self):
        bucket = FileBucket(max_size_bytes=10 * MB)
        assert bucket.can_fit(make_file(10.0))

    def test_cannot_fit_over_capacity(self):
        bucket = FileBucket(max_size_bytes=10 * MB)
        assert not bucket.can_fit(make_file(10.1))

    def test_add_updates_size(self):
        bucket = FileBucket(max_size_bytes=10 * MB)
        f = make_file(3.0)
        bucket.add(f)
        assert bucket.total_size_bytes == f.size_bytes
        assert len(bucket) == 1

    def test_total_size_mb_sum(self):
        bucket = FileBucket(max_size_bytes=20 * MB)
        bucket.add(make_file(3.0))
        bucket.add(make_file(4.0))
        assert abs(bucket.total_size_mb - 7.0) < 0.01

    def test_can_fit_respects_existing_files(self):
        bucket = FileBucket(max_size_bytes=10 * MB)
        bucket.add(make_file(8.0))
        assert not bucket.can_fit(make_file(3.0))
        assert bucket.can_fit(make_file(2.0))


# ---------------------------------------------------------------------------
# SizeFileStrategy
# ---------------------------------------------------------------------------

class TestSizeFileStrategy:
    S = SizeFileStrategy(bucket_size_mb=10.0)

    def test_empty_input_returns_empty(self):
        assert self.S.bucket([]) == []

    def test_single_small_file_one_bucket(self):
        buckets = self.S.bucket([make_file(3.0)])
        assert len(buckets) == 1
        assert len(buckets[0]) == 1

    def test_files_fitting_one_bucket(self):
        buckets = self.S.bucket([make_file(2.0), make_file(3.0), make_file(4.0)])
        assert len(buckets) == 1
        assert len(buckets[0]) == 3

    def test_overflow_creates_second_bucket(self):
        buckets = self.S.bucket([make_file(6.0), make_file(6.0)])
        assert len(buckets) == 2

    def test_oversized_file_gets_own_bucket(self):
        buckets = self.S.bucket([make_file(15.0)])
        assert len(buckets) == 1
        assert buckets[0].total_size_mb > 10.0

    def test_oversized_file_flushes_current_bucket_first(self):
        buckets = self.S.bucket([make_file(3.0, "a.bin"), make_file(15.0, "b.bin")])
        assert len(buckets) == 2
        assert len(buckets[0]) == 1  # 3 MB file flushed before oversized
        assert len(buckets[1]) == 1  # oversized file alone

    def test_no_files_lost(self):
        files = [make_file(float(i), f"{i}.bin") for i in range(1, 9)]
        buckets = self.S.bucket(files)
        assert sum(len(b) for b in buckets) == len(files)

    def test_no_bucket_exceeds_limit_for_normal_files(self):
        files = [make_file(1.0, f"{i}.bin") for i in range(20)]
        buckets = self.S.bucket(files)
        for b in buckets:
            assert b.total_size_mb <= 10.0 + 0.01


# ---------------------------------------------------------------------------
# MockFileSource contract
# ---------------------------------------------------------------------------

class TestMockFileSource:
    def test_returns_predetermined_files(self):
        files = [make_file(1.0), make_file(2.0)]
        assert MockFileSource(files).fetch_files() == files

    def test_fetch_returns_copy(self):
        files = [make_file(1.0)]
        src = MockFileSource(files)
        src.fetch_files().append(make_file(2.0))
        assert len(src.fetch_files()) == 1


# ---------------------------------------------------------------------------
# NightlyProcessor (integration)
# ---------------------------------------------------------------------------

class TestNightlyProcessor:
    def test_all_files_processed(self):
        files = [make_file(3.0, f"f{i}.bin") for i in range(6)]
        processed = []

        with WorkerPool(max_workers=2) as pool:
            NightlyProcessor(
                file_source=MockFileSource(files),
                bucketing_strategy=SizeFileStrategy(bucket_size_mb=10.0),
                worker_pool=pool,
                processor=processed.append,
            ).run()

        assert sum(len(b) for b in processed) == len(files)

    def test_processor_called_once_per_bucket(self):
        files = [make_file(6.0, "a.bin"), make_file(6.0, "b.bin")]
        call_count = [0]

        with WorkerPool(max_workers=2) as pool:
            NightlyProcessor(
                file_source=MockFileSource(files),
                bucketing_strategy=SizeFileStrategy(bucket_size_mb=10.0),
                worker_pool=pool,
                processor=lambda _: call_count.__setitem__(0, call_count[0] + 1),
            ).run()

        assert call_count[0] == 2

    def test_empty_source_runs_without_error(self):
        with WorkerPool(max_workers=2) as pool:
            NightlyProcessor(
                file_source=MockFileSource([]),
                bucketing_strategy=SizeFileStrategy(bucket_size_mb=10.0),
                worker_pool=pool,
            ).run()
