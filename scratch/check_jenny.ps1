Get-Process | Where-Object { $_.ProcessName -like "*jenny*" -or $_.Path -like "*Jenny*" } | Select-Object Id, ProcessName, Path
