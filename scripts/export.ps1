param(
    [string]$ImageName = "telegram_bot",
    [string]$ImageTag = "latest",
    [string]$OutFile = "$PSScriptRoot\..\$($ImageName)-$($ImageTag).tar.gz"
)

Write-Host "Exporting image: ${ImageName}:${ImageTag}"
docker save -o "$PSScriptRoot\..\$ImageName-$ImageTag.tar" "${ImageName}:${ImageTag}"
Write-Host "Compressing..."
Compress-Archive -Path "$PSScriptRoot\..\$ImageName-$ImageTag.tar" -DestinationPath "$OutFile" -Force
Remove-Item "$PSScriptRoot\..\$ImageName-$ImageTag.tar"
Write-Host "Export complete: $OutFile"
