# models
# Model	RPM	TPM	RPD
# Gemini 2.5 Pro	     5	   250,000	 100
# Gemini 2.5 Flash	    10	   250,000	 250
# Gemini 2.5 Flash-Lite	15	   250,000	1000
# Gemini 2.0 Flash	    15	1,000,000	 200
# Gemini 2.0 Flash-Lite	30	1,000,000	 200

import google.generativeai as genai
import os
import shutil
import json
import pathlib
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import subprocess

API_KEY = ''
with open('../../GPT_SECRET_KEY.json', 'r') as file_to_read:
    json_data = json.load(file_to_read)
    API_KEY = json_data["API_KEY"]
os.environ["API_KEY"] = API_KEY

model_name = "gemini-2.5-flash-lite"

try:
    genai.configure(api_key=str(os.environ["API_KEY"]))
except AttributeError:
    print("Error: Please set your 'GEMINI_API_KEY' as an environment variable.")
    sys.exit(1)


class FileAgent:
    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        self.model = genai.GenerativeModel(model_name)
        self.conversation = self.model.start_chat(history=[
            {"role": "user", "parts": [self.system_prompt]},
            {"role": "model", "parts": ["Understood. I am FileWise. Ready to assist."]}
        ])
        self.pending_command = None

        # Common Windows applications mapping
        self.windows_apps = {
            "notepad": "notepad.exe", # works
            "notepad++": "notepad++.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "outlook": "outlook.exe",
            "calculator": "calc.exe", # works
            "paint": "mspaint.exe", # works
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "explorer": "explorer.exe",
            "task manager": "taskmgr.exe",
            "control panel": "control.exe",
            "calendar": "outlook.exe /select outlook:calendar",
            "vlc": "vlc.exe",
            "media player": "wmplayer.exe",
            "photos": "ms-photos:",
            "camera": "microsoft.windows.camera:",
            "settings": "ms-settings:", # works
            "store": "ms-windows-store:"
        }

    # -------------------- Utility Methods --------------------

    def _summarize_action(self, command: dict, result: dict) -> str:
        cmd = command.get("command", "")
        params = command.get("parameters", {})
        if "error" in result:
            return f"❌ Failed to {cmd} with {params}. Reason: {result['error']}"
        return f"✅ {cmd} executed with {params}"

    # -------------------- list files --------------------
    
    def _list_directory(self, path=".",recursive=True): ## works
        try:
            items = os.listdir(path)
            return {"directory": os.path.abspath(path), "contents": items}
        except FileNotFoundError:
            return {"error": f"Directory not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}

    # -------------------- App & File Opening --------------------

    def _open_application(self, application): ### works on some applications
        try:
            app_name_lower = application.lower().strip()
            if app_name_lower in self.windows_apps:
                app_command = self.windows_apps[app_name_lower]
                if app_command.startswith(("ms-", "microsoft.")):
                    subprocess.Popen(f"start {app_command}", shell=True)
                else:
                    subprocess.Popen(app_command, shell=True)
                return {"message": f"Opened {application}"}
            subprocess.Popen(f"start {application}", shell=True)
            return {"message": f"Attempted to open {application}"}
        except Exception as e:
            return {"error": str(e)}

    def _read_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"path": os.path.abspath(path), "content": content}
        except FileNotFoundError:
            return {"error": f"File not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _open_file(self, path, application=None):
        try:
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                return {"error": f"File not found at '{abs_path}'"}
            if application:
                app_lower = application.lower()
                if app_lower in self.windows_apps:
                    application = self.windows_apps[app_lower]
                os.system(f'start "" "{application}" "{abs_path}"')
            else:
                os.startfile(abs_path)  # Use default program
            return {"message": f"Opened file '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _open_folder(self, path): ### works with keywords as well
        try:
            abs_path = os.path.abspath(path)
            if not os.path.isdir(abs_path):
                return {"error": f"Folder not found: '{abs_path}'"}
            os.startfile(abs_path)
            return {"message": f"Opened folder '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    # -------------------- Execution --------------------

    def _execute_code(self, path=None, language=None, **kwargs): ### works fine
        # normalize aliases (in case model still sends file_path)
        if not path and "file_path" in kwargs:
            path = kwargs["file_path"]
        try:
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                return {"error": f"File not found at '{abs_path}'"}
            ext = os.path.splitext(abs_path)[1].lower()
    
            if ext == ".py":
                # open new terminal and run Python script, keep it open
                subprocess.Popen(f'start cmd /K python "{abs_path}"', shell=True)
            elif ext in [".bat", ".cmd"]:
                subprocess.Popen(f'start cmd /K "{abs_path}"', shell=True)
            elif ext == ".ps1":
                subprocess.Popen(f'start powershell -NoExit -File "{abs_path}"', shell=True)
            elif ext == ".js":
                subprocess.Popen(f'start cmd /K node "{abs_path}"', shell=True)
            elif ext == ".sh":
                subprocess.Popen(f'start cmd /K wsl bash "{abs_path}"', shell=True)
            elif ext == ".exe":
                subprocess.Popen(f'start "" "{abs_path}"', shell=True)
            elif ext == ".html":
                os.system(f'start "" "{abs_path}"')
            else:
                return {"error": f"Unsupported file type: {ext}"}
    
            return {"message": f"Executed '{abs_path}' in new terminal (terminal remains open)"}
        except Exception as e:
            return {"error": str(e)}


    # -------------------- File Operations --------------------

    def _create_file(self, path, content="", open_after=False): ## works
        try:
            abs_path = os.path.abspath(path)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            if open_after:
                os.startfile(abs_path)
            return {"message": f"Created file '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _write_file(self, path, content="", open_after=False): ## works
        try:
            abs_path = os.path.abspath(path)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            if open_after:
                os.startfile(abs_path)
            return {"message": f"Wrote to '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _search_item(self, **kwargs): ## works
        keyword = kwargs.get("keyword", "")
        search_path = os.path.abspath(kwargs.get("search_path", "."))
        search_type = kwargs.get("search_type", "both")
        results = {"files": [], "folders": []}
        try:
            for root, dirs, files in os.walk(search_path):
                if search_type in ["both", "folder"]:
                    for d in dirs:
                        if keyword.lower() in d.lower():
                            results["folders"].append(os.path.join(root, d))
                if search_type in ["both", "file"]:
                    for f in files:
                        if keyword.lower() in f.lower():
                            results["files"].append(os.path.join(root, f))
            if len(results["folders"]) == 1 and not results["files"]:
                self._open_folder(results["folders"][0])
            elif len(results["files"]) == 1 and not results["folders"]:
                self._open_file(results["files"][0])
            return {"results": results, "keyword": keyword}
        except Exception as e:
            return {"error": str(e)}
    def _move_item(self, source, destination):
        try:
            shutil.move(source, destination)
            return {"message": f"Successfully moved '{os.path.abspath(source)}' to '{os.path.abspath(destination)}'"}
        except FileNotFoundError:
            return {"error": f"Source '{source}' not found."}
        except Exception as e:
            return {"error": str(e)}

    def _copy_item(self, source, destination):
        try:
            abs_source = os.path.abspath(source)
            abs_destination = os.path.abspath(destination)
    
            if not os.path.exists(abs_source):
                return {"error": f"Source '{abs_source}' not found."}
    
            if os.path.isdir(abs_source):
                # copy entire directory
                if os.path.exists(abs_destination):
                    return {"error": f"Destination '{abs_destination}' already exists."}
                shutil.copytree(abs_source, abs_destination)
            else:
                # copy single file
                os.makedirs(os.path.dirname(abs_destination), exist_ok=True)
                shutil.copy2(abs_source, abs_destination)
    
            return {
                "message": f"Successfully copied '{abs_source}' to '{abs_destination}'"
            }
        except Exception as e:
            return {"error": str(e)}


    def _delete_file(self, path): #works
        try:
            os.remove(path)
            return {"message": f"Successfully deleted file: '{os.path.abspath(path)}'"}
        except FileNotFoundError:
            return {"error": f"File not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _create_directory(self, path, exist_ok=True): #works
        """
        Create a directory at the specified path.
    
        Parameters:
        - path: str → full or relative path of the directory to create
        - exist_ok: bool → if True, do not raise an error if the directory already exists
    
        Returns a JSON object with success or error message.
        """
        try:
            abs_path = os.path.abspath(path)
            os.makedirs(abs_path, exist_ok=exist_ok)
            return {"message": f"Directory created at '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}


    def _delete_directory(self, path):
        try:
            shutil.rmtree(path)
            return {"message": f"Successfully deleted directory and its contents: '{os.path.abspath(path)}'"}
        except FileNotFoundError:
            return {"error": f"Directory not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}
    
    def _clarify(self, question):
        return {"clarify": question}

    def _respond(self, message):
        return {"response": message}

    # -------------------- Command Execution --------------------

    def _execute_command(self, response_json):
        try:
            if "workflow" in response_json:
                workflow_results = []
                for step in response_json["workflow"]:
                    result = self._execute_single_command(step)
                    workflow_results.append({
                        "command": step,
                        "result": result,
                        "summary": self._summarize_action(step, result)
                    })
                return {"workflow": workflow_results}
            else:
                return self._execute_single_command(response_json)
        except Exception as e:
            return {"error": f"Execution error: {str(e)}"}

    def _execute_single_command(self, command_json):
        command = command_json.get("command")
        params = command_json.get("parameters", {})
    
        # normalize aliases before execution
        if "file_path" in params and "path" not in params:
            params["path"] = params.pop("file_path")
        if "folder_path" in params and "path" not in params:
            params["path"] = params.pop("folder_path")
    
        if command == "execute_file":
            command = "execute_code"
        
        command_map = {
            "create_file": self._create_file,
            "write_file": self._write_file,
            "open_file": self._open_file,
            "open_folder": self._open_folder,
            "execute_code": self._execute_code,
            "execute_file": self._execute_code,
            "search_item": self._search_item,
            "open_application": self._open_application,
            "list_directory": self._list_directory,
            "read_file": self._read_file,
            "move_item": self._move_item,
            "delete_file": self._delete_file,
            "delete_directory": self._delete_directory,
            "clarify": self._clarify,
            "respond": self._respond,
            "copy_item": self._copy_item,
            "create_directory": self._create_directory
        }
        if command in command_map:
            return command_map[command](**params)
        return {"error": f"Unknown command '{command}'"}


    # -------------------- Request Handling --------------------

    def process_request(self, user_prompt, current_dir="."):
        full_prompt = f"Current Directory: '{current_dir}'\nUser: '{user_prompt}'"
        try:
            response = self.conversation.send_message(full_prompt)
            clean = response.text.strip().replace("```json", "").replace("```", "").strip()
            response_json = json.loads(clean)
            result = self._execute_command(response_json)
            return {"agent_command": response_json, "result": result}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON from model", "raw": response.text}
        except Exception as e:
            return {"error": str(e)}


# -------------------- FastAPI Setup --------------------

app = FastAPI(title="FileWise AI Agent")

AGENT_SYSTEM_PROMPT = r"""You are "FileWise", an advanced AI assistant for managing files and folders on a Windows operating system. You exist to execute file operations hands-free with precision, safety, and flexibility.
🚨 STRICT OUTPUT RULES 🚨  
Always use **consistent parameter names** across all commands. Do not invent synonyms.  
- For files and folders → always use "path"  
- For move/copy/cut → always use "source" and "destination"  
- For search → always use "keyword", "search_path", "search_type"  
- For applications → always use "application"  

Example (GOOD ✅):
{
  "command": "open_file",
  "parameters": {"path": "C:\\Users\\me\\report.pdf"}
}

Example (BAD ❌):
{
  "command": "open_file",
  "parameters": {"file_path": "C:\\Users\\me\\report.pdf"}
}


Core Directives
Persona: Be careful, reliable, and user-centric. Always ensure actions are safe and clarify when destructive changes may occur.

Environment: Operate on a Windows machine, always using Windows-style file paths (e.g., C:\Users\Username\Documents).

Default Context: A Current Working Directory (CWD) may be provided. Use this as the default location unless the user specifies a full path.

Chained Operations: If a user requests multiple actions in a single command (e.g., "search for report.pdf, copy it to Documents, then open it"), you must generate a workflow chain.

Enhanced Search: When searching for items, search for BOTH files and folders unless specifically requested otherwise. Use the 'search_item' command instead of 'search_file'.

Application Opening: You can now open Windows applications using the 'open_application' command. Common applications include: notepad, excel, word, powerpoint, calculator, paint, chrome, firefox, etc.

Response Format
Always translate user input into JSON only.

Single Action Examples:
{
  "command": "open_file",
  "parameters": {"path": "C:\\Users\\me\\report.pdf"}
}

{
  "command": "open_application",
  "parameters": {"application": "excel"}
}

Multiple Actions (Workflow) Example:
{
  "workflow": [
    {
      "command": "search_item",
      "parameters": {"keyword": "report.pdf", "search_path": "C:\\", "search_type": "both"}
    },
    {
      "command": "copy_item",
      "parameters": {
        "source": "C:\\Found\\report.pdf",
        "destination": "C:\\Users\\me\\Documents"
      }
    },
    {
      "command": "open_application",
      "parameters": {"application": "excel"}
    },
    {
      "command": "open_file",
      "parameters": {"path": "C:\\Users\\me\\Documents\\report.pdf", "application": "excel"}
    }
  ]
}

Supported Commands [FOLLOW THEM STRICTLY]:
- List directory → list_directory
- Create directory → create_directory
- Create file → create_file
- Read file → read_file
- Write file → write_file
- Open file → open_file
- Open folder → open_folder
- Move item → move_item
- Copy item → copy_item
- Cut item → cut_item
- Delete file → delete_file
- Delete directory → delete_directory
- Search files AND folders → search_item (use this instead of search_file)
- Execute code → execute_code
- Open Windows application → open_application

IMPORTANT SEARCH COMMAND UPDATE:
- Use "search_item" NOT "search_file"
- Parameters: "keyword" (not "filename"), "search_path", "search_type" ("file", "folder", or "both")
- Example: {"command": "search_item", "parameters": {"keyword": "project", "search_path": "C:\\", "search_type": "both"}}

CODE EXECUTION UPDATE:
- When executing code files (.py, .bat, .js), the terminal will remain open after execution
- This allows you to see the output and any error messages

APPLICATION OPENING:
- Use "open_application" command for opening Windows apps
- Supported apps: notepad, excel, word, powerpoint, calculator, paint, chrome, firefox, edge, cmd, powershell, etc.
- You can also specify custom applications by name

Workflow Building:
- Preserve command order as implied in user's request
- If ambiguous, insert clarify command first
- Handle multiple search results gracefully
"""

agent = FileAgent(system_prompt=AGENT_SYSTEM_PROMPT)


class UserRequest(BaseModel):
    prompt: str
    current_dir: str = "."


@app.post("/file-agent")
def handle_request(request: UserRequest):
    result = agent.process_request(request.prompt, request.current_dir)
    print(result)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
