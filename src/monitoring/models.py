from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel


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
    name: str
    url: str


class MonitoringConfig(BaseModel):
    check_interval_seconds: int
    timeout_seconds: int
    history_retention_hours: int


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
