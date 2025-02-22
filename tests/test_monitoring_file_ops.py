import json
import pytest
import pytest_asyncio
from datetime import datetime
from pathlib import Path
from src.monitoring.models import URLStatus, StatusCheck
from src.monitoring.service import MonitoringService


@pytest_asyncio.fixture
async def monitoring_service(config_file):
    service = MonitoringService(config_file)
    await service.load_config()
    return service


@pytest.mark.asyncio
async def test_save_monitoring_result(monitoring_service, tmp_path):
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
    # Try to save history for nonexistent URL
    result_file = monitoring_service.save_monitoring_results(name="nonexistent")

    # Should return None for nonexistent URL
    assert result_file is None
