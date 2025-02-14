import pytest
import pytest_asyncio
from pathlib import Path


# Set default fixture loop scope to function
def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function"


@pytest.fixture
def config_file(tmp_path):
    """Common fixture for config file path with test data"""
    config = {
        "urls": [{"name": "test-url", "url": "http://example.com"}],
        "monitoring": {
            "check_interval_seconds": 60,
            "timeout_seconds": 5,
            "history_retention_hours": 1,
        },
    }
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        import json

        json.dump(config, f)
    return str(config_path)


@pytest_asyncio.fixture
async def monitoring_service(config_file):
    """Common fixture for monitoring service"""
    from src.monitoring.service import MonitoringService

    service = MonitoringService(config_file)
    await service.load_config()
    yield service
    await service.stop()
