# pwrstat-api

A lightweight REST API that exposes the status of a CyberPower UPS as JSON by wrapping the `pwrstat` command-line utility from [PowerPanel for Linux](https://www.cyberpowersystems.com/product/software/powerpanel-for-linux/).

## Requirements

- Debian-based Linux (the PowerPanel `pwrstatd` daemon must be installed and running)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Installation

Clone the repository and run the installer as root. It creates a dedicated system user, installs the project to `/opt/pwrstat-api`, and registers a systemd service.

```bash
git clone <repo-url>
cd pwrstat-python-api
sudo bash install.sh
```

The service starts automatically and is enabled on boot. To check its status:

```bash
systemctl status pwrstat-api
```

## Configuration

The service reads the following environment variables. Override them by creating a systemd drop-in:

```bash
sudo mkdir -p /etc/systemd/system/pwrstat-api.service.d
sudo tee /etc/systemd/system/pwrstat-api.service.d/local.conf <<EOF
[Service]
Environment=PORT=8080
Environment=HOST=127.0.0.1
Environment=LOG_LEVEL=debug
EOF
sudo systemctl daemon-reload && sudo systemctl restart pwrstat-api
```

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5002` | TCP port to listen on |
| `HOST` | `0.0.0.0` | Interface to bind to |
| `LOG_LEVEL` | `info` | Uvicorn log level (`debug`, `info`, `warning`, `error`) |

## API

### `GET /pwrstat`

Returns all UPS parameters reported by `pwrstat -status` as a JSON object.

**Response `200 OK`**

```json
{
  "Model Name": "CP1500PFCLCD",
  "Firmware Number": "BFZE108.F5 .I",
  "Rating Voltage": "120 V",
  "Rating Power": "1000 Watt(900 VA)",
  "State": "Normal",
  "Power Supply by": "Utility Power",
  "Utility Voltage": "120 V",
  "Output Voltage": "120 V",
  "Battery Capacity": "100 %",
  "Remaining Runtime": "60 min.",
  "Load": "180 Watt(18 %)",
  "Line Interaction": "None",
  "Test Result": "Unknown",
  "Last Power Event": "None"
}
```

**Error responses**

| Status | Condition |
|---|---|
| `429` | More than 60 requests per minute from a single IP |
| `503` | `pwrstat` binary not found, returned a non-zero exit code, timed out, or reported no data |
| `500` | Unexpected internal error |

The full API specification is available in [`openapi.json`](openapi.json). Interactive docs are served at `http://<host>:<port>/docs` when the service is running.

## Development

Install dependencies (including dev tools):

```bash
uv sync
```

**Run tests:**

```bash
uv run pytest
```

**Lint and format:**

```bash
uv run ruff check src/ tests/   # lint
uv run ruff format src/ tests/  # format
```

**Run locally** (requires `pwrstatd` running on the host):

```bash
uv run pwrstat-api
```

## Project structure

```
pwrstat-python-api/
├── src/pwrstat_api/
│   ├── main.py          # FastAPI application and entry point
│   └── parser.py        # pwrstat output parser
├── tests/
│   ├── test_api.py      # Endpoint tests
│   └── test_parser.py   # Parser unit tests
├── openapi.json         # OpenAPI 3.1 specification
├── pwrstat-api.service  # systemd unit file
├── install.sh           # Debian installer
└── pyproject.toml       # Project metadata and tool configuration
```
