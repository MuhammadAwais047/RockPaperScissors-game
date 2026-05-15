$basePath = "C:\Users\KLH\New App"
$baseFile = Join-Path $basePath "base_environment.py"
$castleFile = Join-Path $basePath "castle_environment.py"

# Read both files
$baseCode = Get-Content $baseFile -Raw
$castleCode = Get-Content $castleFile -Raw

# Remove the if __name__ guard from castle code so main() always runs
# When executed via MCP, __name__ may be "__builtins__" or similar, not "__main__"
$castleCode = $castleCode -replace "if __name__ == `"__main__`":\s*    main\(\)", "main()"

# Combine: base first, then castle
$combined = $baseCode + "`n`n# ===== CASTLE ENVIRONMENT =====`n`n" + $castleCode

$payload = @{
    type = "execute_code"
    params = @{
        code = $combined
    }
} | ConvertTo-Json -Depth 10

Write-Output "Sending European castle environment script to Blender (port 9876)..."
Write-Output "Script size: $($combined.Length) characters"

try {
    $tcp = New-Object System.Net.Sockets.TcpClient('localhost', 9876)
    $tcp.SendTimeout = 10000
    $stream = $tcp.GetStream()
    $data = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $stream.Write($data, 0, $data.Length)
    $stream.Flush()
    Write-Output "Sent! Waiting for response..."
    Start-Sleep -Seconds 10
    if ($tcp.Connected) {
        $buffer = New-Object byte[] 32768
        $read = $stream.Read($buffer, 0, $buffer.Length)
        if ($read -gt 0) {
            $response = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
            Write-Output "Response from Blender:"
            Write-Output $response
        } else {
            Write-Output "No response data received (script is likely still running in Blender)"
        }
    } else {
        Write-Output "Connection closed by Blender (script is running)"
    }
    $tcp.Close()
} catch {
    Write-Error "Error: $($_.Exception.Message)"
}
