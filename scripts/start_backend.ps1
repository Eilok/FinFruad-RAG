param(
  [string]$HostIP = "0.0.0.0",
  [int]$Port = 8000
)

uv run uvicorn backend.app:app --host $HostIP --port $Port --reload