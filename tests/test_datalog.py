"""Tests for data collection and time-series logging."""

from pytierra.datalog import TimeSeriesLog, DataCollector


class TestTimeSeriesLog:
    def test_record_and_retrieve(self):
        log = TimeSeriesLog(capacity=100)
        log.record(0, 1.0)
        log.record(100, 2.0)
        assert log.values() == [1.0, 2.0]
        assert log.times() == [0, 100]

    def test_ring_buffer_capacity(self):
        log = TimeSeriesLog(capacity=3)
        for i in range(5):
            log.record(i, float(i))
        assert len(log) == 3
        assert log.values() == [2.0, 3.0, 4.0]

    def test_last(self):
        log = TimeSeriesLog()
        assert log.last() is None
        log.record(10, 42.0)
        assert log.last().value == 42.0
        assert log.last().time == 10

    def test_clear(self):
        log = TimeSeriesLog()
        log.record(0, 1.0)
        log.clear()
        assert len(log) == 0


class TestDataCollector:
    def test_should_sample(self):
        dc = DataCollector(sample_interval=1000)
        assert dc.should_sample(0) is False  # 0 - 0 < 1000
        assert dc.should_sample(999) is False
        assert dc.should_sample(1000) is True

    def test_sample_collects_data(self):
        """Test that sample() populates time series from a running sim."""
        import os
        from pytierra.config import Config
        from pytierra.simulation import Simulation

        ancestor = os.path.join(
            os.path.dirname(__file__), "..", "Tierra6_02", "tierra", "gb0", "0080aaa.tie"
        )
        config = Config()
        config.soup_size = 10000
        sim = Simulation(config=config)
        sim.boot(ancestor)

        # Run a small number of instructions
        sim.run(max_instructions=5000)

        dc = DataCollector(sample_interval=1)
        dc.sample(sim)

        assert len(dc.population_size) == 1
        assert dc.population_size.last().value > 0
        assert len(dc.mean_creature_size) == 1
        assert len(dc.num_genotypes) == 1
        assert len(dc.soup_fullness) == 1

    def test_all_series(self):
        dc = DataCollector()
        series = dc.all_series()
        assert "population_size" in series
        assert "mean_creature_size" in series
        assert "instructions_per_second" in series
        assert len(series) == 6
