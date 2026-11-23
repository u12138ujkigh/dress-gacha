' Silent launcher: no console window at all.
' ChrW(&H542F)&ChrW(&H52A8) = "启动" (kept as code points so this .vbs stays pure ASCII).
Set sh = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
app = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = ChrW(&H542F) & ChrW(&H52A8) & ".ps1"
cmd = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & app & "\" & ps1 & """"
sh.Run cmd, 0, False
