# Stops any running instance of the AI Trading Desk backend.
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*run.py*--port 8765*" -or
                   ($_.CommandLine -like "*app.main:app*" -and $_.CommandLine -like "*uvicorn*") }
if ($procs) {
    $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Write-Host "Backend stopped."
} else {
    Write-Host "No running backend found."
}
