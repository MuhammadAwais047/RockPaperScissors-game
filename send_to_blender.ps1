$code = @'
import bpy

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Add UV sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(-2, 0, 1))
sphere = bpy.context.active_object
sphere.name = "UV Sphere"

# Add monkey head (Suzanne)
bpy.ops.mesh.primitive_monkey_add(size=1, location=(2, 0, 1))
suzanne = bpy.context.active_object
suzanne.name = "Suzanne"

print("Done! Added UV Sphere and Suzanne")
'@

$payload = @{
    type = "execute_code"
    params = @{
        code = $code
    }
} | ConvertTo-Json -Depth 10

try {
    $tcp = New-Object System.Net.Sockets.TcpClient('localhost', 9876)
    $stream = $tcp.GetStream()
    $data = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $stream.Write($data, 0, $data.Length)
    $stream.Flush()
    Start-Sleep -Seconds 3
    $buffer = New-Object byte[] 8192
    $read = $stream.Read($buffer, 0, $buffer.Length)
    $response = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
    Write-Output $response
    $tcp.Close()
} catch {
    Write-Error $_.Exception.Message
}
