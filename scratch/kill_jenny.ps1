$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*Jenny*" }
foreach ($p in $procs) {
    Write-Host "Terminating PID $($p.ProcessId): $($p.CommandLine)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Host "Jenny audit and termination complete."
