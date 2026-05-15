$code = @"
import bpy
objs = bpy.data.objects
total = len(objs)
mesh_count = len([o for o in objs if o.type == 'MESH'])
verts = sum(len(o.data.vertices) for o in objs if o.type == 'MESH' and o.data)
faces = sum(len(o.data.polygons) for o in objs if o.type == 'MESH' and o.data)
print(f"Total objects: {total}")
print(f"Mesh objects: {mesh_count}")
print(f"Total vertices: {verts}")
print(f"Total faces: {faces}")
names = [o.name for o in objs]
print(f"Object names: {names}")
"@

$payload = @{
    type = "execute_code"
    params = @{
        code = $code
    }
} | ConvertTo-Json -Depth 10 -Compress

try {
    $tcp = New-Object System.Net.Sockets.TcpClient('localhost', 9876)
    $tcp.SendTimeout = 5000
    $stream = $tcp.GetStream()
    $data = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $stream.Write($data, 0, $data.Length)
    $stream.Flush()
    Start-Sleep -Seconds 3
    if ($tcp.Connected) {
        $buffer = New-Object byte[] 65536
        $stream.ReadTimeout = 5000
        try {
            $read = $stream.Read($buffer, 0, $buffer.Length)
            if ($read -gt 0) {
                $response = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
                Write-Output $response
            } else {
                Write-Output "No response"
            }
        } catch {
            Write-Output "Read error: $($_.Exception.Message)"
        }
    }
    $tcp.Close()
} catch {
    Write-Error "Error: $($_.Exception.Message)"
}
