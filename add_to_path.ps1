$localBin = "$env:USERPROFILE\.local\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*\.local\bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$localBin", "User")
    Write-Host "Added $localBin to User PATH"
} else {
    Write-Host "$localBin is already in User PATH"
}
