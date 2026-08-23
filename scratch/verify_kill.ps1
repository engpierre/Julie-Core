$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*Jenny\main.py*" }
if ($procs) {
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Killed remaining Jenny process"
} else {
    Write-Host "ZERO Jenny processes active."
}
