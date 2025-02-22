import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from src.monitoring.models import URLStatus, StatusCheck
from src.monitoring.service import MonitoringService


@pytest_asyncio.fixture
async def monitoring_service(config_file):
    service = MonitoringService(config_file)
    await service.load_config()
    return service


@pytest.mark.asyncio
async def test_history_cleanup(monitoring_service):
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
    status = monitoring_service.get_url_status("nonexistent")
    assert status is None


@pytest.mark.asyncio
async def test_get_empty_url_status(monitoring_service):
    # Create empty history
    monitoring_service.status_history["test-url"] = []

    # Get status
    status = monitoring_service.get_url_status("test-url")

    assert status is not None
    assert status.name == "test-url"
    assert status.current_status == URLStatus.UNKNOWN
    assert status.response_time is None


@pytest.mark.asyncio
async def test_get_url_history(monitoring_service):
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


@pytest.mark.asyncio
async def test_get_nonexistent_url_history(monitoring_service):
    history = monitoring_service.get_url_history("nonexistent")
    assert history is None
