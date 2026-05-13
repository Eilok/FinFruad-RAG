param(
  [Parameter(Mandatory=$true)][string]$Text,
  [string]$Source = "manual"
)

uv run python -m backend.scripts.ingest_kb --text "$Text" --source $Source
