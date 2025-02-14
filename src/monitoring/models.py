from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class URLStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class StatusCheck(BaseModel):
    timestamp: datetime
    status: URLStatus
    response_time: Optional[float] = None
    error: Optional[str] = None


class URLConfig(BaseModel):
    name: str = Field(min_length=1, description="Name of the URL to monitor")
    url: str = Field(
        min_length=1, pattern="^https?://", description="Valid HTTP(S) URL to monitor"
    )


class MonitoringConfig(BaseModel):
    check_interval_seconds: int = Field(
        gt=0, description="Interval between checks in seconds"
    )
    timeout_seconds: int = Field(gt=0, description="Timeout for each check in seconds")
    history_retention_hours: int = Field(
        gt=0, description="Number of hours to retain history"
    )


class Config(BaseModel):
    urls: List[URLConfig]
    monitoring: MonitoringConfig


class URLStatusResponse(BaseModel):
    name: str
    url: str
    current_status: URLStatus
    last_check: datetime
    response_time: Optional[float] = None
    error: Optional[str] = None


class URLHistoryResponse(BaseModel):
    name: str
    url: str
    history: List[StatusCheck]
