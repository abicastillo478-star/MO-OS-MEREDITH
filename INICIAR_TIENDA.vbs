Set shell = CreateObject("WScript.Shell")
base = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
shell.Run "cmd /c cd /d """ & base & """ && python -m pip install -r requirements.txt && python app.py", 0, False
WScript.Sleep 2500
shell.Run "http://127.0.0.1:5000", 1, False
