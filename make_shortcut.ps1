# Creates a Comparyson shortcut (with the app icon) on the current user's Desktop.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$desktop\Comparyson.lnk")
$lnk.TargetPath = $pythonw
$lnk.Arguments = "`"$root\app.py`""
$lnk.WorkingDirectory = $root
$lnk.IconLocation = "$root\assets\logo.ico"
$lnk.Description = "Comparyson - directory comparison"
$lnk.Save()
Write-Host "Created $desktop\Comparyson.lnk"
