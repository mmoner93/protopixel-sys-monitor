import json
import pytest
import asyncio
from src.monitoring.service import MonitoringService
from src.monitoring.models import URLStatus


@pytest.mark.asyncio
async def test_add_url_monitor(monitoring_service):
    # Add a new URL monitor
    url_config = monitoring_service.add_url_monitor(
        "test-new-url", "https://example.com"
    )

    # Verify URL was added to config
    assert any(u.name == "test-new-url" for u in monitoring_service.config.urls)
    assert url_config.name == "test-new-url"
    assert url_config.url == "https://example.com"

    # Verify history was initialized
    assert "test-new-url" in monitoring_service.status_history
    assert monitoring_service.status_history["test-new-url"] == []

    # Verify config file was updated
    with open(monitoring_service.config_path, "r") as f:
        saved_config = json.load(f)
        assert any(u["name"] == "test-new-url" for u in saved_config["urls"])


@pytest.mark.asyncio
async def test_add_duplicate_url_monitor(monitoring_service):
    # Try to add URL with existing name
    with pytest.raises(ValueError) as exc_info:
        monitoring_service.add_url_monitor("test-url", "https://example.com")

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_url_monitor(monitoring_service):
    # Delete existing URL
    url_config = monitoring_service.delete_url_monitor("test-url")

    # Verify URL was removed from config
    assert not any(u.name == "test-url" for u in monitoring_service.config.urls)
    assert url_config.name == "test-url"

    # Verify history was removed
    assert "test-url" not in monitoring_service.status_history

    # Verify config file was updated
    with open(monitoring_service.config_path, "r") as f:
        saved_config = json.load(f)
        assert not any(u["name"] == "test-url" for u in saved_config["urls"])


@pytest.mark.asyncio
async def test_delete_nonexistent_url_monitor(monitoring_service):
    # Try to delete non-existent URL
    result = monitoring_service.delete_url_monitor("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_runtime_url_addition(monitoring_service):
    try:
        # Start with no URLs
        monitoring_service.config.urls = []

        # Start monitoring in background
        monitoring_task = asyncio.create_task(monitoring_service.monitor_urls())
        monitoring_service.running = True
        await asyncio.sleep(0.1)

        # Add URLs one by one using add_url_monitor
        urls = [
            ("first-url", "http://example.com"),
            ("second-url", "http://httpstat.us/200"),
        ]

        for name, url in urls:
            monitoring_service.add_url_monitor(name, url)
            await asyncio.sleep(0.1)

            # Verify history is initialized immediately
            assert name in monitoring_service.status_history
            assert isinstance(monitoring_service.status_history[name], list)

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

    finally:
        # Ensure service is stopped
        monitoring_service.running = False


@pytest.mark.asyncio
async def test_runtime_mixed_url_addition(monitoring_service):
    # Add a mix of working and failing URLs using add_url_monitor
    monitoring_service.add_url_monitor("good-url", "http://example.com")
    monitoring_service.add_url_monitor("bad-url", "http://nonexistent.example.com")
    monitoring_service.add_url_monitor("error-url", "http://httpstat.us/500")

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
