# Remove extra/duplicate files on desktop
Remove-Item "C:\Users\Pierre\OneDrive\Bureau\launch_julie.vbs" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\Pierre\OneDrive\Bureau\launch_julie.bat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\Pierre\OneDrive\Bureau\Julie Core.lnk" -Force -ErrorAction SilentlyContinue

Remove-Item "C:\Users\Pierre\Desktop\launch_julie.vbs" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\Pierre\Desktop\launch_julie.bat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\Pierre\Desktop\Julie Core.lnk" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\Pierre\Desktop\launch_julie.lnk" -Force -ErrorAction SilentlyContinue

# Create single clean launch_julie.lnk shortcut on Bureau
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("C:\Users\Pierre\OneDrive\Bureau\launch_julie.lnk")
$sc.TargetPath = "wscript.exe"
$sc.Arguments = "`"C:\Users\Pierre\.openclaw\workspace\Julie-Core\launch_julie.vbs`""
$sc.WorkingDirectory = "C:\Users\Pierre\.openclaw\workspace\Julie-Core"
$sc.Description = "Launch Julie Core Executive Assistant"
$sc.Save()

Write-Host "Desktop cleanup complete. Exactly 1 shortcut exists: launch_julie"
