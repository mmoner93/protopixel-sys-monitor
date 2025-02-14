import asyncio
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from src.monitoring.models import URLStatus, StatusCheck, URLConfig
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


@pytest.mark.asyncio
async def test_get_nonexistent_url_history(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service
    history = monitoring_service.get_url_history("nonexistent")
    assert history is None


@pytest.mark.asyncio
async def test_get_empty_url_status(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Create empty history
    monitoring_service.status_history["test-url"] = []

    # Get status
    status = monitoring_service.get_url_status("test-url")

    assert status is not None
    assert status.name == "test-url"
    assert status.current_status == URLStatus.UNKNOWN
    assert status.response_time is None


@pytest.mark.asyncio
async def test_monitor_urls(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

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
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

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
async def test_save_monitoring_result(monitoring_service, tmp_path):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Create a test check
    check = StatusCheck(
        timestamp=datetime.now(), status=URLStatus.UP, response_time=0.1
    )

    # Save to a test file
    test_file = tmp_path / "test-monitoring.csv"
    monitoring_service.save_monitoring_result(
        monitoring_service.config.urls[0], check, str(test_file)
    )

    # Verify file was created and has correct format
    assert test_file.exists()
    content = test_file.read_text()
    assert "URL Name,URL,Timestamp,Status,Response Time,Error" in content
    assert "test-url" in content
    assert "up" in content


@pytest.mark.asyncio
async def test_save_monitoring_results(monitoring_service, tmp_path):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Add test history
    check = StatusCheck(
        timestamp=datetime.now(), status=URLStatus.UP, response_time=0.1
    )
    monitoring_service.status_history["test-url"] = [check]

    # Save all history
    test_file = tmp_path / "all-history.csv"
    result_file = monitoring_service.save_monitoring_results(filename=str(test_file))

    # Verify file was created and has correct format
    assert Path(result_file).exists()
    content = Path(result_file).read_text()
    assert "URL Name,URL,Timestamp,Status,Response Time,Error" in content
    assert "test-url" in content
    assert "up" in content


@pytest.mark.asyncio
async def test_save_monitoring_results_single_url(monitoring_service, tmp_path):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Add test history
    check = StatusCheck(
        timestamp=datetime.now(), status=URLStatus.UP, response_time=0.1
    )
    monitoring_service.status_history["test-url"] = [check]

    # Save single URL history
    test_file = tmp_path / "url-history.csv"
    result_file = monitoring_service.save_monitoring_results(
        name="test-url", filename=str(test_file)
    )

    # Verify file was created and has correct format
    assert Path(result_file).exists()
    content = Path(result_file).read_text()
    assert "URL Name,URL,Timestamp,Status,Response Time,Error" in content
    assert "test-url" in content
    assert "up" in content


@pytest.mark.asyncio
async def test_save_monitoring_results_nonexistent_url(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Try to save history for nonexistent URL
    result_file = monitoring_service.save_monitoring_results(name="nonexistent")

    # Should return None for nonexistent URL
    assert result_file is None


@pytest.mark.asyncio
async def test_check_url_timeout(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

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
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Create a URL config that will fail
    monitoring_service.config.urls[0].url = "http://nonexistent.example.com"

    # Check URL
    result = await monitoring_service.check_url(monitoring_service.config.urls[0])

    # Verify error handling
    assert result.status == URLStatus.DOWN
    assert result.error is not None


@pytest.mark.asyncio
async def test_check_url_http_error(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Create a URL config that will return 404
    monitoring_service.config.urls[0].url = "http://httpstat.us/404"

    # Check URL
    result = await monitoring_service.check_url(monitoring_service.config.urls[0])

    # Verify HTTP error handling
    assert result.status == URLStatus.DOWN
    assert result.error == "HTTP 404"


@pytest.mark.asyncio
async def test_monitor_urls_with_mixed_results(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

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
    from pydantic import ValidationError

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
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        await service.load_config()

    # Verify the error includes URL validation failures
    error_str = str(exc_info.value)
    assert "name" in error_str  # Empty name validation
    assert "url" in error_str  # Invalid URL format validation


@pytest.mark.asyncio
async def test_add_url_monitor(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

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
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Try to add URL with existing name
    with pytest.raises(ValueError) as exc_info:
        monitoring_service.add_url_monitor("test-url", "https://example.com")

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_url_monitor(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

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
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    # Try to delete non-existent URL
    result = monitoring_service.delete_url_monitor("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_runtime_url_addition(monitoring_service):
    # Await the monitoring_service coroutine to get the actual service instance
    monitoring_service = await monitoring_service

    try:
        # Start with no URLs
        monitoring_service.config.urls = []

        # Start monitoring in background
        monitoring_task = asyncio.create_task(monitoring_service.monitor_urls())
        monitoring_service.running = True
        await asyncio.sleep(0.1)

        # Add URLs one by one
        urls = [
            URLConfig(name="first-url", url="http://example.com"),
            URLConfig(name="second-url", url="http://httpstat.us/200"),
        ]

        for url in urls:
            monitoring_service.config.urls.append(url)
            await asyncio.sleep(0.1)

            # Verify history is initialized immediately
            assert url.name in monitoring_service.status_history
            assert isinstance(monitoring_service.status_history[url.name], list)

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

    try:
        # Start monitoring in background
        monitoring_task = asyncio.create_task(monitoring_service.monitor_urls())

        # Let it run for a brief period
        monitoring_service.running = True
        await asyncio.sleep(0.1)

        # Add a new URL at runtime
        new_url = URLConfig(name="runtime-url", url="http://example.com")
        monitoring_service.config.urls.append(new_url)

        # Let it run a bit more to monitor new URL
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

        # Verify history was initialized and populated for the new URL
        assert "runtime-url" in monitoring_service.status_history
        assert isinstance(monitoring_service.status_history["runtime-url"], list)
        if monitoring_service.status_history["runtime-url"]:
            assert isinstance(
                monitoring_service.status_history["runtime-url"][0], StatusCheck
            )

    finally:
        # Ensure service is stopped
        monitoring_service.running = False

    # Add a mix of working and failing URLs
    monitoring_service.config.urls = [
        URLConfig(name="good-url", url="http://example.com"),
        URLConfig(name="bad-url", url="http://nonexistent.example.com"),
        URLConfig(name="error-url", url="http://httpstat.us/500"),
    ]

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
