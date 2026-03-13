"""
Thread Safety Tests for ConfigLoader Singleton

Tests that ConfigLoader properly handles concurrent access:
1. Double-checked locking prevents duplicate initialization
2. Concurrent reads return consistent data
3. Singleton identity is preserved across threads
"""

import threading
from unittest.mock import patch, MagicMock

import pytest


pytestmark = [
    pytest.mark.requirement("SRS-006"),
    pytest.mark.risk("RISK-005"),
    pytest.mark.design("SDS-006"),
]


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset ConfigLoader singleton before each test."""
    from services.config_loader import ConfigLoader
    ConfigLoader._instance = None
    ConfigLoader._lock = threading.Lock()
    yield
    # Restore singleton for other tests that import config_loader
    ConfigLoader._instance = None


class TestConfigLoaderSingleton:
    """Test singleton identity and initialization."""

    def test_singleton_returns_same_instance(self):
        """Two calls to ConfigLoader() return the exact same object."""
        from services.config_loader import ConfigLoader
        a = ConfigLoader()
        b = ConfigLoader()
        assert a is b

    def test_config_loaded_on_first_access(self):
        """Config dict is populated after instantiation."""
        from services.config_loader import ConfigLoader
        loader = ConfigLoader()
        # cdss_config.json exists in project, so config should be non-empty
        assert loader.config != {}
        assert isinstance(loader.config, dict)

    def test_has_lock_attribute(self):
        """Class-level lock exists for thread safety."""
        from services.config_loader import ConfigLoader
        assert hasattr(ConfigLoader, '_lock')
        assert isinstance(ConfigLoader._lock, type(threading.Lock()))


class TestConcurrentInstantiation:
    """Test that concurrent threads all get the same singleton."""

    def test_concurrent_threads_get_same_instance(self):
        """PT-076: Multiple threads racing to create singleton get identical instance."""
        from services.config_loader import ConfigLoader

        results = []
        errors = []
        barrier = threading.Barrier(10)

        def create_instance():
            try:
                barrier.wait(timeout=5)
                instance = ConfigLoader()
                results.append(id(instance))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Threads raised errors: {errors}"
        assert len(results) == 10
        # All threads must get the same instance (same id)
        assert len(set(results)) == 1, f"Got {len(set(results))} distinct instances, expected 1"

    def test_load_config_called_exactly_once(self):
        """PT-077: _load_config is called exactly once even under contention."""
        from services.config_loader import ConfigLoader

        call_count = {'n': 0}
        original_load = ConfigLoader._load_config

        def counting_load(self):
            call_count['n'] += 1
            original_load(self)

        barrier = threading.Barrier(8)
        errors = []

        def create_instance():
            try:
                barrier.wait(timeout=5)
                ConfigLoader()
            except Exception as e:
                errors.append(e)

        with patch.object(ConfigLoader, '_load_config', counting_load):
            threads = [threading.Thread(target=create_instance) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        assert not errors
        assert call_count['n'] == 1, f"_load_config called {call_count['n']} times, expected 1"


class TestConcurrentReads:
    """Test that concurrent reads return consistent data."""

    def test_concurrent_reads_return_consistent_config(self):
        """PT-078: Concurrent config reads all return the same data."""
        from services.config_loader import ConfigLoader

        loader = ConfigLoader()
        expected_config = loader.config.copy()

        results = []
        barrier = threading.Barrier(10)

        def read_config():
            barrier.wait(timeout=5)
            cfg = loader.config
            loinc = loader.get_loinc_codes()
            params = loader.get_precise_hbr_params()
            results.append((cfg, loinc, params))

        threads = [threading.Thread(target=read_config) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(results) == 10
        for cfg, loinc, params in results:
            assert cfg == expected_config
            # All threads should get identical LOINC codes
            assert loinc == results[0][1]
            assert params == results[0][2]

    def test_config_not_none_after_concurrent_init(self):
        """No thread sees a half-initialized instance with _config=None."""
        from services.config_loader import ConfigLoader

        configs = []
        barrier = threading.Barrier(10)

        def check_config():
            barrier.wait(timeout=5)
            loader = ConfigLoader()
            configs.append(loader._config)

        threads = [threading.Thread(target=check_config) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(configs) == 10
        for cfg in configs:
            assert cfg is not None, "Thread saw _config=None (half-initialized singleton)"
            assert isinstance(cfg, dict)
