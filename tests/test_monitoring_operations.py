import asyncio
import pytest
import pytest_asyncio
from src.monitoring.models import URLStatus, URLConfig
from src.monitoring.service import MonitoringService


@pytest.mark.asyncio
async def test_monitor_urls(monitoring_service):
    try:
        # Start monitoring in background
        monitoring_task = asyncio.create_task(monitoring_service.monitor_urls())

        # Let it run for a brief period
        monitoring_service.running = True
        await asyncio.sleep(0.1)

        # Stop monitoring
        monitoring_service.running = False

        # Wait for task to complete with timeout
        try:
            await asyncio.wait_for(monitoring_task, timeout=1.0)
        except asyncio.TimeoutError:
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass

        # Verify history was created
        assert "test-url" in monitoring_service.status_history
        assert len(monitoring_service.status_history["test-url"]) > 0
    finally:
        # Ensure service is stopped
        monitoring_service.running = False


@pytest.mark.asyncio
async def test_start_stop(monitoring_service):
    try:
        # Start in background
        start_task = asyncio.create_task(monitoring_service.start())

        # Let it run briefly
        await asyncio.sleep(0.1)
        assert monitoring_service.running

        # Stop the service
        await monitoring_service.stop()

        # Wait for task to complete with timeout
        try:
            await asyncio.wait_for(start_task, timeout=1.0)
        except asyncio.TimeoutError:
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

        assert not monitoring_service.running
    finally:
        # Ensure service is stopped
        monitoring_service.running = False


@pytest.mark.asyncio
async def test_monitor_urls_with_mixed_results(monitoring_service):
    # Add a mix of working and failing URLs
    monitoring_service.config.urls = [
        URLConfig(name="good-url", url="http://google.com"),
        URLConfig(name="bad-url", url="http://nonexistent.example.com"),
        URLConfig(name="error-url", url="http://httpstat.us/500"),
    ]

    # Initialize history for new URLs
    for url_config in monitoring_service.config.urls:
        monitoring_service.status_history[url_config.name] = []

    try:
        # Start monitoring in background
        monitoring_task = asyncio.create_task(monitoring_service.monitor_urls())

        # Let it run for a brief period
        monitoring_service.running = True
        await asyncio.sleep(0.1)

        # Stop monitoring
        monitoring_service.running = False

        # Wait for task to complete with timeout
        try:
            await asyncio.wait_for(monitoring_task, timeout=1.0)
        except asyncio.TimeoutError:
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass

        # Verify history was created for all URLs regardless of their status
        assert "good-url" in monitoring_service.status_history
        assert "bad-url" in monitoring_service.status_history
        assert "error-url" in monitoring_service.status_history

        # Verify that failed checks are properly recorded
        for url_name in ["bad-url", "error-url"]:
            history = monitoring_service.status_history[url_name]
            if history:
                assert history[-1].status == URLStatus.DOWN
                assert history[-1].error is not None

    finally:
        # Ensure service is stopped
        monitoring_service.running = False


@pytest.mark.asyncio
async def test_check_url_timeout(monitoring_service):
    # Create a URL config that will timeout
    monitoring_service.config.urls[
        0
    ].url = "http://example.com:81"  # Non-responsive port
    monitoring_service.config.monitoring.timeout_seconds = 1

    # Check URL
    result = await monitoring_service.check_url(monitoring_service.config.urls[0])

    # Verify timeout handling
    assert result.status == URLStatus.DOWN
    assert result.error == "Timeout"


@pytest.mark.asyncio
async def test_check_url_error(monitoring_service):
    # Create a URL config that will fail
    monitoring_service.config.urls[0].url = "http://nonexistent.example.com"

    # Check URL
    result = await monitoring_service.check_url(monitoring_service.config.urls[0])

    # Verify error handling
    assert result.status == URLStatus.DOWN
    assert result.error is not None


@pytest.mark.asyncio
async def test_check_url_http_error(monitoring_service):
    # Create a URL config that will return 404
    monitoring_service.config.urls[0].url = "http://httpstat.us/404"

    # Check URL
    result = await monitoring_service.check_url(monitoring_service.config.urls[0])

    # Verify HTTP error handling
    assert result.status == URLStatus.DOWN
    assert result.error == "HTTP 404"
