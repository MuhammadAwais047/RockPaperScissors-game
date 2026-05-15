$code = [System.IO.File]::ReadAllText("C:\Users\KLH\New App\combined_racing_blender.py")

$payload = @{
    type = "execute_code"
    params = @{
        code = $code
    }
} | ConvertTo-Json -Depth 10 -Compress

Write-Output "Sending racing environment to Blender (port 9876)..."
Write-Output "Script size: $($code.Length) characters"

try {
    $tcp = New-Object System.Net.Sockets.TcpClient('localhost', 9876)
    $tcp.SendTimeout = 15000
    $stream = $tcp.GetStream()
    $data = [System.Text.Encoding]::UTF8.GetBytes($payload)
    Write-Output "Connected! Sending data..."
    $stream.Write($data, 0, $data.Length)
    $stream.Flush()
    Write-Output "Sent! Waiting 15 seconds for Blender to generate the scene..."
    Start-Sleep -Seconds 15
    if ($tcp.Connected) {
        $buffer = New-Object byte[] 65536
        $stream.ReadTimeout = 5000
        try {
            $read = $stream.Read($buffer, 0, $buffer.Length)
            if ($read -gt 0) {
                $response = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
                Write-Output "=== Blender Response ==="
                Write-Output $response
                Write-Output "=== End Response ==="
            } else {
                Write-Output "No response data (scene generation may still be in progress)"
            }
        } catch {
            Write-Output "Read timed out - scene is likely still being generated"
        }
    } else {
        Write-Output "Connection closed by server"
    }
    $tcp.Close()
} catch {
    Write-Error "Error: $($_.Exception.Message)"
}
Write-Output "Done."
