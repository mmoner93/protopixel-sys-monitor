import asyncio
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from src.monitoring.models import URLStatus, StatusCheck
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


@pytest.fixture
async def monitoring_service(config_file):
    service = MonitoringService(config_file)
    await service.load_config()
    return service


@pytest.mark.asyncio
async def test_load_config(monitoring_service):
    monitoring_service = await monitoring_service
    assert monitoring_service.config is not None
    assert len(monitoring_service.config.urls) == 1
    assert monitoring_service.config.urls[0].name == "test-url"
    assert monitoring_service.config.urls[0].url == "http://example.com"


@pytest.mark.asyncio
async def test_history_cleanup(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Add some test history data
    now = datetime.now()
    old_check = StatusCheck(
        timestamp=now - timedelta(hours=2), status=URLStatus.UP, response_time=0.1
    )
    recent_check = StatusCheck(timestamp=now, status=URLStatus.UP, response_time=0.1)

    monitoring_service.status_history["test-url"] = [old_check, recent_check]

    # Simulate a monitoring cycle and cleanup
    await monitoring_service.check_url(monitoring_service.config.urls[0])
    monitoring_service.cleanup_history("test-url")

    # Verify old entries are cleaned up
    history = monitoring_service.status_history["test-url"]
    assert all(
        check.timestamp
        > (
            now
            - timedelta(
                hours=monitoring_service.config.monitoring.history_retention_hours
            )
        )
        for check in history
    )


@pytest.mark.asyncio
async def test_get_url_status(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Add a test status
    check = StatusCheck(
        timestamp=datetime.now(), status=URLStatus.UP, response_time=0.1
    )
    monitoring_service.status_history["test-url"] = [check]

    # Get status
    status = monitoring_service.get_url_status("test-url")

    assert status is not None
    assert status.name == "test-url"
    assert status.current_status == URLStatus.UP
    assert status.response_time == 0.1


@pytest.mark.asyncio
async def test_get_nonexistent_url_status(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service
    status = monitoring_service.get_url_status("nonexistent")
    assert status is None


@pytest.mark.asyncio
async def test_get_url_history(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Add test history
    check = StatusCheck(
        timestamp=datetime.now(), status=URLStatus.UP, response_time=0.1
    )
    monitoring_service.status_history["test-url"] = [check]

    # Get history
    history = monitoring_service.get_url_history("test-url")

    assert history is not None
    assert history.name == "test-url"
    assert len(history.history) == 1
    assert history.history[0].status == URLStatus.UP
