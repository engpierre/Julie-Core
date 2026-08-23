Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Pierre\.openclaw\workspace\Julie-Core"

' 1. Check if port 8080 is already active (don't launch duplicate servers)
Dim httpCheck
Set httpCheck = CreateObject("MSXML2.ServerXMLHTTP.6.0")
On Error Resume Next
httpCheck.open "GET", "http://127.0.0.1:8080/index.html", False
httpCheck.send

If Err.Number <> 0 Then
    ' Port 8080 is offline -> Launch app_eel.py cleanly in background
    Err.Clear
    WshShell.Run ".\.venv\Scripts\python.exe app_eel.py", 0, False
    WScript.Sleep 3000 ' Wait for server bind
End If
On Error GoTo 0

' 2. Launch MS Edge in App Mode
WshShell.Run """C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"" --app=http://127.0.0.1:8080/index.html", 1, False
