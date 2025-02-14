# ProtoPixel System Monitor

A monitoring system for checking the status of configured URLs.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

## Development

1. Run the development server:

    - On terminal run:

    ```bash
    uvicorn src.main:app --reload
    ```

    - On VSCODE, run the `FastAPI` configuration.

2. Run the tests:

    - On terminal run:

    ```bash
    pytest
    ```

    - On VSCODE, run the `Python: Run All Tests` configuration.

## Configuration

Create a `config.json` file in the root directory:

```json
{
    "urls": [
        {
            "name": "example",
            "url": "https://example.com"
        }
    ],
    "monitoring": {
        "check_interval_seconds": 60,
        "timeout_seconds": 5,
        "history_retention_hours": 24
    }
}
```

## API Documentation

When the server is running, visit:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Developing steps

1. Init a git repository.
2. Create branches for dev and initial setup.
3. Create a FastAPI project.
4. Create a monitoring service.
5. Create the models.
6. Create the routes.
7. Create the configuration file.
8. Create the tests.
9. Create the Dockerfile.
10. Create the docker-compose file.
11. Refactor the tests into separeted files.

## Improvements

- Add a database to store the monitoring history.
- Add ORM to interact with the database.
- Implement user authentication with JWT or OAuth.
- Implement new endpoint to modify the configuration file timers at runtime.
- Implement a frontend to display the monitoring history.
