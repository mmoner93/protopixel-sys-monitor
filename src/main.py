import sys

sys.path.append("src")
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from monitoring.service import MonitoringService
from monitoring.models import URLStatusResponse, URLHistoryResponse

app = FastAPI(title="ProtoPixel System Monitor")
monitor = MonitoringService("config.json")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Start the monitoring service when the application starts"""
    asyncio.create_task(monitor.start())


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the monitoring service when the application shuts down"""
    await monitor.stop()


@app.get("/status/{name}", response_model=URLStatusResponse)
async def get_url_status(name: str):
    """Get the current status of a URL"""
    status = monitor.get_url_status(name)
    if status is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return status


@app.get("/history/{name}", response_model=URLHistoryResponse)
async def get_url_history(name: str):
    """Get the history of a URL"""
    history = monitor.get_url_history(name)
    if history is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return history


@app.post("/monitoring/start")
async def start_monitoring():
    """Start the monitoring service"""
    if monitor.running:
        raise HTTPException(status_code=400, detail="Monitoring is already running")
    asyncio.create_task(monitor.start())
    return {"status": "started"}


@app.post("/monitoring/stop")
async def stop_monitoring():
    """Stop the monitoring service"""
    if not monitor.running:
        raise HTTPException(status_code=400, detail="Monitoring is not running")
    await monitor.stop()
    return {"status": "stopped"}


@app.get("/monitoring/status")
async def monitoring_status():
    """Get the current status of the monitoring service"""
    return {"running": monitor.running}


@app.get("/download/csv")
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
