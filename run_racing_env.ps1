$basePath = "C:\Users\KLH\New App"
$baseFile = Join-Path $basePath "base_environment.py"
$racingFile = Join-Path $basePath "racing_environment.py"

# Read both files
$baseCode = Get-Content $baseFile -Raw
$racingCode = Get-Content $racingFile -Raw

# Remove the if __name__ guard from racing code so main() always runs
# When executed via MCP, __name__ may be "__builtins__" or similar, not "__main__"
$racingCode = $racingCode -replace "if __name__ == `"__main__`":\s*    main\(\)", "main()"

# Combine: base first, then racing
$combined = $baseCode + "`n`n# ===== RACING ENVIRONMENT =====`n`n" + $racingCode

$payload = @{
    type = "execute_code"
    params = @{
        code = $combined
    }
} | ConvertTo-Json -Depth 10

Write-Output "Sending racing environment script to Blender (port 9876)..."
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
