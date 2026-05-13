param(
  [int]$Port = 3000
)

Push-Location webui
try {
  # npm run dev --port $Port
  npm run dev
}
finally {
  Pop-Location
}
