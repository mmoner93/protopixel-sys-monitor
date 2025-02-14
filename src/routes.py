import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
from monitoring.models import URLStatusResponse, URLHistoryResponse, URLStatus
from monitoring.service import MonitoringService
from pydantic import BaseModel


class CreateMonitorRequest(BaseModel):
    name: str
    url: str


router = APIRouter()
monitor = MonitoringService("config.json")


@router.on_event("startup")
async def startup_event():
    """Start the monitoring service when the application starts"""
    asyncio.create_task(monitor.start())


@router.on_event("shutdown")
async def shutdown_event():
    """Stop the monitoring service when the application shuts down"""
    await monitor.stop()


@router.get("/status/{name}", response_model=URLStatusResponse)
async def get_url_status(name: str):
    """Get the current status of a URL"""
    status = monitor.get_url_status(name)
    if status is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return status


@router.get("/history/{name}", response_model=URLHistoryResponse)
async def get_url_history(name: str):
    """Get the history of a URL"""
    history = monitor.get_url_history(name)
    if history is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return history


@router.post("/monitoring/start")
async def start_monitoring():
    """Start the monitoring service"""
    if monitor.running:
        raise HTTPException(status_code=400, detail="Monitoring is already running")
    asyncio.create_task(monitor.start())
    return {"status": "started"}


@router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop the monitoring service"""
    if not monitor.running:
        raise HTTPException(status_code=400, detail="Monitoring is not running")
    await monitor.stop()
    return {"status": "stopped"}


@router.get("/monitoring/status")
async def monitoring_status():
    """Get the current status of the monitoring service"""
    return {"running": monitor.running}


@router.get("/download/csv")
async def download_history_csv(name: str = None):
    """
    Download monitoring history as CSV. If name is provided, downloads history for that URL only.
    Otherwise downloads history for all URLs.
    """
    filepath = monitor.save_monitoring_results(name)
    if filepath is None:
        raise HTTPException(
            status_code=404,
            detail=f"No monitoring data available{f' for {name}' if name else ''}",
        )

    filename = f"{name}-history.csv" if name else "all-history.csv"
    return FileResponse(path=filepath, filename=filename, media_type="text/csv")


@router.post("/monitor", response_model=URLStatusResponse)
async def create_monitor(request: CreateMonitorRequest):
    """Create a new URL monitor"""
    try:
        url_config = monitor.add_url_monitor(request.name, request.url)
        # Return initial status
        return URLStatusResponse(
            name=url_config.name,
            url=url_config.url,
            current_status=URLStatus.UNKNOWN,
            last_check=datetime.now(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/monitor/{name}")
async def delete_monitor(name: str):
    """Delete a URL monitor"""
    result = monitor.delete_url_monitor(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"URL monitor '{name}' not found")
    return {"status": "deleted", "name": name}
