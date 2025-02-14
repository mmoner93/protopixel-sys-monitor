import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
