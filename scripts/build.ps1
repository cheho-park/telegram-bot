param(
    [string]$ImageName = "telegram_bot",
    [string]$ImageTag = "latest"
)

Write-Host "Building Docker image: ${ImageName}:${ImageTag}"
docker build -t "${ImageName}:${ImageTag}" .

Write-Host "Done. Run with: docker run --env-file .env -it ${ImageName}:${ImageTag}"
