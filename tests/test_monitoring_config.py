import json
import pytest
import pytest_asyncio
from pydantic import ValidationError
from src.monitoring.service import MonitoringService


@pytest.fixture
def config_file(tmp_path):
    config = {
        "urls": [{"name": "test-url", "url": "http://example.com"}],
        "monitoring": {
            "check_interval_seconds": 60,
            "timeout_seconds": 5,
            "history_retention_hours": 1,
        },
    }
    config_path = tmp_path / "test_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    return str(config_path)


@pytest_asyncio.fixture
async def monitoring_service(config_file):
    service = MonitoringService(config_file)
    await service.load_config()
    return service


@pytest.mark.asyncio
async def test_load_config(monitoring_service):
    assert monitoring_service.config is not None
    assert len(monitoring_service.config.urls) == 1
    assert monitoring_service.config.urls[0].name == "test-url"
    assert monitoring_service.config.urls[0].url == "http://example.com"


@pytest.mark.asyncio
async def test_load_invalid_config(tmp_path):
    # Test missing required fields
    invalid_config = {}
    config_path = tmp_path / "invalid_config.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)

    service = MonitoringService(str(config_path))
    with pytest.raises(Exception):  # pydantic will raise validation error
        await service.load_config()


@pytest.mark.asyncio
async def test_load_invalid_monitoring_config(tmp_path):
    # Test invalid monitoring values
    invalid_config = {
        "urls": [{"name": "test", "url": "http://example.com"}],
        "monitoring": {
            "check_interval_seconds": -1,  # Invalid negative interval
            "timeout_seconds": 0,  # Invalid zero timeout
            "history_retention_hours": 0,  # Invalid zero retention
        },
    }
    config_path = tmp_path / "invalid_monitoring.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)

    service = MonitoringService(str(config_path))
    with pytest.raises(
        ValidationError
    ):  # pydantic validation error for negative/zero values
        await service.load_config()


@pytest.mark.asyncio
async def test_load_malformed_config(tmp_path):
    # Test malformed JSON
    config_path = tmp_path / "malformed_config.json"
    with open(config_path, "w") as f:
        f.write("{invalid json")

    service = MonitoringService(str(config_path))
    with pytest.raises(json.JSONDecodeError):
        await service.load_config()


@pytest.mark.asyncio
async def test_load_invalid_url_config(tmp_path):
    # Test invalid URL configurations
    invalid_config = {
        "urls": [
            {"name": "", "url": "http://example.com"},  # Empty name
            {"name": "invalid-url", "url": "not-a-url"},  # Invalid URL format
            {"name": "missing-schema", "url": "example.com"},  # Missing http(s)://
        ],
        "monitoring": {
            "check_interval_seconds": 60,
            "timeout_seconds": 5,
            "history_retention_hours": 1,
        },
    }
    config_path = tmp_path / "invalid_urls.json"
    with open(config_path, "w") as f:
        json.dump(invalid_config, f)

    service = MonitoringService(str(config_path))
    with pytest.raises(ValidationError) as exc_info:
        await service.load_config()

    # Verify the error includes URL validation failures
    error_str = str(exc_info.value)
    assert "name" in error_str  # Empty name validation
    assert "url" in error_str  # Invalid URL format validation
