import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
from .models import (
    Config,
    URLConfig,
    URLStatus,
    StatusCheck,
    URLStatusResponse,
    URLHistoryResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Optional[Config] = None
        self.status_history: Dict[str, List[StatusCheck]] = {}
        self.running = False

    async def load_config(self) -> None:
        """Load configuration from file"""
        with open(self.config_path, "r") as f:
            config_data = json.load(f)
            self.config = Config(**config_data)

        # Initialize history for each URL
        for url_config in self.config.urls:
            if url_config.name not in self.status_history:
                self.status_history[url_config.name] = []

    def cleanup_history(self, url_name: str) -> None:
        """Clean up old entries from URL history"""
        if url_name not in self.status_history:
            return

        cutoff = datetime.now() - timedelta(
            hours=self.config.monitoring.history_retention_hours
        )
        self.status_history[url_name] = [
            check for check in self.status_history[url_name] if check.timestamp > cutoff
        ]

    async def check_url(self, url_config: URLConfig) -> StatusCheck:
        """Check a single URL and return its status"""
        start_time = datetime.now()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url_config.url, timeout=self.config.monitoring.timeout_seconds
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    if response.status < 400:
                        return StatusCheck(
                            timestamp=start_time,
                            status=URLStatus.UP,
                            response_time=response_time,
                        )
                    else:
                        return StatusCheck(
                            timestamp=start_time,
                            status=URLStatus.DOWN,
                            response_time=response_time,
                            error=f"HTTP {response.status}",
                        )
        except asyncio.TimeoutError:
            return StatusCheck(
                timestamp=start_time, status=URLStatus.DOWN, error="Timeout"
            )
        except Exception as e:
            return StatusCheck(
                timestamp=start_time, status=URLStatus.DOWN, error=str(e)
            )

    async def monitor_urls(self) -> None:
        """Monitor all URLs periodically"""
        while self.running:
            tasks = []
            for url_config in self.config.urls:
                tasks.append(self.check_url(url_config))

            results = await asyncio.gather(*tasks)

            # Update history and save new results
            for url_config, result in zip(self.config.urls, results):
                self.status_history[url_config.name].append(result)
                # Save the new result immediately
                self.save_monitoring_result(url_config, result)
                # Cleanup old entries
                self.cleanup_history(url_config.name)

            await asyncio.sleep(self.config.monitoring.check_interval_seconds)

    def get_url_status(self, name: str) -> Optional[URLStatusResponse]:
        """Get current status for a URL"""
        url_config = next((url for url in self.config.urls if url.name == name), None)
        if not url_config or name not in self.status_history:
            return None

        history = self.status_history[name]
        if not history:
            return URLStatusResponse(
                name=name,
                url=url_config.url,
                current_status=URLStatus.UNKNOWN,
                last_check=datetime.now(),
            )

        latest = history[-1]
        return URLStatusResponse(
            name=name,
            url=url_config.url,
            current_status=latest.status,
            last_check=latest.timestamp,
            response_time=latest.response_time,
            error=latest.error,
        )

    def get_url_history(self, name: str) -> Optional[URLHistoryResponse]:
        """Get history for a URL"""
        url_config = next((url for url in self.config.urls if url.name == name), None)
        if not url_config or name not in self.status_history:
            return None

        # Clean up old entries before returning history
        self.cleanup_history(name)

        return URLHistoryResponse(
            name=name, url=url_config.url, history=self.status_history[name]
        )

    async def start(self) -> None:
        """Start the monitoring service"""
        await self.load_config()
        self.running = True
        await self.monitor_urls()

    async def stop(self) -> None:
        """Stop the monitoring service"""
        self.running = False

    def save_monitoring_result(
        self,
        url_config: URLConfig,
        check: StatusCheck,
        filename: str = "monitoring-url.csv",
    ) -> None:
        """Save a single monitoring result to CSV file"""
        import csv
        import os

        # Check if file exists to determine if we need to write headers
        file_exists = os.path.exists(filename)

        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)

            # Write header if this is a new file
            if not file_exists:
                writer.writerow(
                    ["URL Name", "URL", "Timestamp", "Status", "Response Time", "Error"]
                )

            # Write the new result
            writer.writerow(
                [
                    url_config.name,
                    url_config.url,
                    check.timestamp.isoformat(),
                    check.status.value,
                    check.response_time if check.response_time is not None else "",
                    check.error if check.error is not None else "",
                ]
            )

    def save_monitoring_results(self, name: str = None, filename: str = None) -> str:
        """
        Save monitoring history to a CSV file. If name is provided, saves only that URL's history.
        If no name is provided, saves all URLs' history.

        Args:
            name: Optional name of the URL to save history for
            filename: Optional filename, defaults to {name}-history.csv or all-history.csv

        Returns:
            str: Path to the generated CSV file
        """
        import csv
        import os

        if filename is None:
            filename = f"{name}-history.csv" if name else "all-history.csv"

        if name:
            # Get URL configuration for single URL
            url_config = next(
                (url for url in self.config.urls if url.name == name), None
            )
            if not url_config or name not in self.status_history:
                logger.error(f"No history found for URL name: {name}")
                return None

            history = self.status_history.get(name, [])
            if not history:
                logger.info(f"No monitoring data available for URL: {name}")
                return None

            urls_to_save = [(url_config, history)]
        else:
            # Save all URLs
            urls_to_save = [
                (url, self.status_history.get(url.name, []))
                for url in self.config.urls
                if self.status_history.get(url.name, [])
            ]
            if not urls_to_save:
                logger.info("No monitoring data available for any URL")
                return None

        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(
                ["URL Name", "URL", "Timestamp", "Status", "Response Time", "Error"]
            )

            # Write history for the specified URLs
            for url_config, history in urls_to_save:
                for check in history:
                    writer.writerow(
                        [
                            url_config.name,
                            url_config.url,
                            check.timestamp.isoformat(),
                            check.status.value,
                            check.response_time
                            if check.response_time is not None
                            else "",
                            check.error if check.error is not None else "",
                        ]
                    )

            logger.info(f"Monitoring history saved to {filename}")
            return filename
