"""Tests for the event system."""

from pytierra.events import EventBus


class TestEventBus:
    def test_subscribe_and_emit(self):
        bus = EventBus()
        received = []
        bus.subscribe("TEST", lambda **kw: received.append(kw))
        bus.emit("TEST", value=42)
        assert received == [{"value": 42}]

    def test_multiple_subscribers(self):
        bus = EventBus()
        a, b = [], []
        bus.subscribe("X", lambda **kw: a.append(1))
        bus.subscribe("X", lambda **kw: b.append(2))
        bus.emit("X")
        assert a == [1] and b == [2]

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        cb = lambda **kw: received.append(1)
        bus.subscribe("X", cb)
        bus.unsubscribe("X", cb)
        bus.emit("X")
        assert received == []

    def test_unsubscribe_nonexistent(self):
        bus = EventBus()
        bus.unsubscribe("X", lambda: None)  # should not raise

    def test_disable_enable(self):
        bus = EventBus()
        received = []
        bus.subscribe("X", lambda **kw: received.append(1))
        bus.disable()
        bus.emit("X")
        assert received == []
        bus.enable()
        bus.emit("X")
        assert received == [1]

    def test_clear(self):
        bus = EventBus()
        received = []
        bus.subscribe("X", lambda **kw: received.append(1))
        bus.clear()
        bus.emit("X")
        assert received == []

    def test_different_event_types(self):
        bus = EventBus()
        a_events, b_events = [], []
        bus.subscribe("A", lambda **kw: a_events.append(1))
        bus.subscribe("B", lambda **kw: b_events.append(1))
        bus.emit("A")
        assert a_events == [1] and b_events == []
