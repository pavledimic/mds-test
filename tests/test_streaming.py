import time

import pytest

from src.streaming.message import Message
from src.streaming.minibatch import MiniBatch
from src.streaming.minibatch_manager import MiniBatchManager
from src.worker.worker_pool import WorkerPool


class MockDataSource:
    """Yields a fixed sequence of messages without any real timing."""

    def __init__(self, messages):
        self._messages = list(messages)
        self._stopped = False

    def stream(self):
        for msg in self._messages:
            if self._stopped:
                return
            yield msg

    def stop(self):
        self._stopped = True


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class TestMessage:
    def test_unique_ids(self):
        m1, m2 = Message(payload="a"), Message(payload="b")
        assert m1.id != m2.id

    def test_stores_payload(self):
        msg = Message(payload={"key": 42})
        assert msg.payload == {"key": 42}

    def test_timestamp_set(self):
        msg = Message(payload=None)
        assert msg.timestamp is not None


# ---------------------------------------------------------------------------
# MiniBatch
# ---------------------------------------------------------------------------

class TestMiniBatch:
    def test_empty_on_creation(self):
        assert len(MiniBatch()) == 0

    def test_add_increments_length(self):
        batch = MiniBatch()
        batch.add(Message(payload="x"))
        assert len(batch) == 1

    def test_add_preserves_order(self):
        batch = MiniBatch()
        msgs = [Message(payload=i) for i in range(3)]
        for m in msgs:
            batch.add(m)
        assert batch.messages == msgs

    def test_closed_at_none_before_close(self):
        assert MiniBatch().closed_at is None

    def test_close_sets_closed_at(self):
        batch = MiniBatch()
        batch.close()
        assert batch.closed_at is not None


# ---------------------------------------------------------------------------
# MiniBatchManager
# ---------------------------------------------------------------------------

class TestMiniBatchManager:
    def _manager(self, window=60.0):
        pool = WorkerPool(max_workers=2)
        received = []
        mgr = MiniBatchManager(worker_pool=pool, window_seconds=window, processor=received.append)
        return pool, mgr, received

    def test_single_message_flushed_in_one_batch(self):
        pool, mgr, received = self._manager()
        mgr.on_message(Message(payload="hi"))
        mgr.flush()
        pool.shutdown()
        assert len(received) == 1
        assert len(received[0]) == 1

    def test_multiple_messages_collected_in_same_batch(self):
        pool, mgr, received = self._manager()
        for i in range(5):
            mgr.on_message(Message(payload=i))
        mgr.flush()
        pool.shutdown()
        assert len(received) == 1
        assert len(received[0]) == 5

    def test_flush_with_no_messages_does_nothing(self):
        pool, mgr, received = self._manager()
        mgr.flush()
        pool.shutdown()
        assert received == []

    def test_two_separate_windows_produce_two_batches(self):
        pool, mgr, received = self._manager()
        mgr.on_message(Message(payload="first"))
        mgr.flush()
        mgr.on_message(Message(payload="second"))
        mgr.flush()
        pool.shutdown()
        assert len(received) == 2

    def test_batch_is_closed_on_submit(self):
        pool, mgr, received = self._manager()
        mgr.on_message(Message(payload="z"))
        mgr.flush()
        pool.shutdown()
        assert received[0].closed_at is not None

    @pytest.mark.timeout(2)
    def test_window_timer_auto_submits_without_flush(self):
        pool, mgr, received = self._manager(window=0.05)
        mgr.on_message(Message(payload="auto"))
        time.sleep(0.3)
        pool.shutdown()
        assert len(received) == 1


# ---------------------------------------------------------------------------
# MockDataSource contract
# ---------------------------------------------------------------------------

class TestMockDataSource:
    def test_yields_all_messages(self):
        msgs = [Message(payload=i) for i in range(4)]
        assert list(MockDataSource(msgs).stream()) == msgs

    def test_stop_before_stream_yields_nothing(self):
        msgs = [Message(payload=i) for i in range(10)]
        src = MockDataSource(msgs)
        src.stop()
        assert list(src.stream()) == []

    def test_stop_mid_stream(self):
        msgs = [Message(payload=i) for i in range(100)]
        src = MockDataSource(msgs)

        collected = []
        for msg in src.stream():
            collected.append(msg)
            if len(collected) == 3:
                src.stop()

        assert len(collected) == 3
