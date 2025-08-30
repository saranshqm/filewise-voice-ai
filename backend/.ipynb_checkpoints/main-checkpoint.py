import google.generativeai as genai
import os
import shutil
import json
import pathlib
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json

API_KEY = ''
with open('../../GPT_SECRET_KEY.json', 'r') as file_to_read:
    json_data = json.load(file_to_read)
    API_KEY = json_data["API_KEY"]
os.environ["API_KEY"] = API_KEY
# uvicorn main:app --reload

# f = open("../../secret_key.txt")
# API_KEY = f.read()

# API_KEY = ""

# models
# Model	RPM	TPM	RPD
# Text-out models
# Gemini 2.5 Pro	5	250,000	100
# Gemini 2.5 Flash	10	250,000	250
# Gemini 2.5 Flash-Lite	15	250,000	1,000
# Gemini 2.0 Flash	15	1,000,000	200
# Gemini 2.0 Flash-Lite	30	1,000,000	200

model_name = 'gemini-2.5-flash-lite' #gemini-2.5-pro

# --- Configuration ---
# IMPORTANT: Set your Gemini API key here
# Recommended: set as environment variable instead of hardcoding.
try:
    genai.configure(api_key=str(os.environ["API_KEY"]))
except AttributeError:
    print("Error: Please set your 'GEMINI_API_KEY' as an environment variable.")
    sys.exit(1)

class FileAgent:
    """An AI agent that handles file operations on Windows."""

    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        self.model = genai.GenerativeModel(model_name)
        self.conversation = self.model.start_chat(history=[
            {'role': 'user', 'parts': [self.system_prompt]},
            {'role': 'model', 'parts': ["Understood. I am FileWise. Ready to assist."]}
        ])

    # --- Summarizer ---
    def _summarize_action(self, command: dict, result: dict) -> str:
        """Convert command + result into a human-friendly summary."""
        cmd = command.get("command", "")
        params = command.get("parameters", {})

        if "error" in result:
            return f"❌ Failed to {cmd} with {params}. Reason: {result['error']}"

        if cmd == "create_directory":
            return f"📁 Created directory at '{params.get('path')}'"
        elif cmd == "create_file":
            return f"📄 Created new file at '{params.get('path')}'"
        elif cmd == "read_file":
            return f"📖 Read contents of file '{params.get('path')}'"
        elif cmd == "write_file":
            return f"✏️ Wrote content to file '{params.get('path')}'"
        elif cmd == "move_item":
            return f"📦 Moved '{params.get('source')}' → '{params.get('destination')}'"
        elif cmd == "delete_file":
            return f"🗑️ Deleted file '{params.get('path')}'"
        elif cmd == "delete_directory":
            return f"🗑️ Deleted directory '{params.get('path')}'"
        elif cmd == "list_directory":
            return f"📋 Listed contents of '{params.get('path', '.')}'"
        elif cmd == "search_file":
            return f"🔍 Searched for '{params.get('filename')}' in '{params.get('search_path', '.')}'"
        elif cmd == "clarify":
            return f"❓ Asked for clarification: '{params.get('question')}'"
        elif cmd == "respond":
            return f"💬 Responded with: '{params.get('message')}'"
        else:
            return f"✅ Executed action '{cmd}'"

    def _execute_command(self, response_json):
        """Parses and executes the command from the LLM's JSON response."""
        results = {}
        try:
            command = response_json.get("command")
            params = response_json.get("parameters", {})

            if not command:
                return {"error": "Agent Error: Received a response without a command."}

            command_map = {
                "list_directory": self._list_directory,
                "create_directory": self._create_directory,
                "create_file": self._create_file,
                "read_file": self._read_file,
                "write_file": self._write_file,
                "move_item": self._move_item,
                "delete_file": self._delete_file,
                "delete_directory": self._delete_directory,
                "search_file": self._search_file,
                "clarify": self._clarify,
                "respond": self._respond,
            }

            if command in command_map:
                results = command_map[command](**params)
            else:
                results = {"error": f"Agent Error: Unknown command '{command}'."}

        except Exception as e:
            results = {"error": f"An error occurred during execution: {e}"}

        return results

    # --- File Operation Methods ---
    def _list_directory(self, path="."):
        try:
            items = os.listdir(path)
            return {"directory": os.path.abspath(path), "contents": items}
        except FileNotFoundError:
            return {"error": f"Directory not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _create_directory(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            return {"message": f"Successfully created directory: '{os.path.abspath(path)}'"}
        except Exception as e:
            return {"error": str(e)}

    def _create_file(self, path):
        try:
            pathlib.Path(path).touch()
            return {"message": f"Successfully created empty file: '{os.path.abspath(path)}'"}
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

    def _write_file(self, path, content=""):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"message": f" Successfully wrote content to '{os.path.abspath(path)}'"}
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

    def _delete_file(self, path):
        try:
            os.remove(path)
            return {"message": f"Successfully deleted file: '{os.path.abspath(path)}'"}
        except FileNotFoundError:
            return {"error": f"File not found at '{path}'"}
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

    def _search_file(self, filename, search_path="."):
        results = []
        try:
            for root, _, files in os.walk(search_path):
                if filename in files:
                    results.append(os.path.join(root, filename))
            return {"results": results}
        except Exception as e:
            return {"error": str(e)}

    def _clarify(self, question):
        return {"clarify": question}

    def _respond(self, message):
        return {"response": message}

    def process_request(self, user_prompt, current_dir="."):
        """Process user request via Gemini and return JSON response"""
        full_prompt = (
            f"Current Working Directory: '{current_dir}'\n"
            f"User Request: '{user_prompt}'"
        )
        try:
            response = self.conversation.send_message(full_prompt)
            clean_response = (
                response.text.strip()
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            response_json = json.loads(clean_response)
            result = self._execute_command(response_json)
            summary = self._summarize_action(response_json, result)   # 🔑 Add summary here
            return {"agent_command": response_json, "result": result, "summary": summary}
        except json.JSONDecodeError:
            return {"error": "Failed to decode the AI's JSON response", "raw": response.text}
        except Exception as e:
            return {"error": str(e)}
            
# --- FastAPI setup ---
app = FastAPI(title="FileWise AI Agent")

AGENT_SYSTEM_PROMPT = """You are "FileWise," an expert AI assistant for managing files on a Windows operating system. Your primary goal is to help users perform file operations accurately and safely.

**Core Directives:**

1. **Persona:** You are helpful, precise, and cautious. You must always prioritize data safety.
2. **Environment:** You are operating on a Windows machine. Always use Windows-style file paths (e.g., `C:\\Users\\Username\\Documents`).
3. **Current Location:** You will always be given the "Current Working Directory." Use this as the default location for operations unless the user specifies a full path.

**Capabilities & Command Structure:**

You must translate the user's natural language request into a single, specific JSON object. Do not output any other text outside of this JSON object.

The JSON object must have a `command` field and a `parameters` object. Here are the available commands:

* List files and directories:
  - "command": "list_directory"
  - "parameters": {"path": "path\\to\\directory"}

* Create a directory:
  - "command": "create_directory"
  - "parameters": {"path": "path\\to\\new_directory"}

* Create an empty file:
  - "command": "create_file"
  - "parameters": {"path": "path\\to\\new_file.txt"}

* Read file content:
  - "command": "read_file"
  - "parameters": {"path": "path\\to\\file"}

* Write content to a file:
  - "command": "write_file"
  - "parameters": {"path": "path\\to\\file", "content": "text to write"}

* Rename or Move a file/directory:
  - "command": "move_item"
  - "parameters": {"source": "path\\to\\source", "destination": "path\\to\\destination"}

* Delete a file:
  - "command": "delete_file"
  - "parameters": {"path": "path\\to\\file"}

* Delete a directory (and all contents):
  - "command": "delete_directory"
  - "parameters": {"path": "path\\to\\directory"}

* Search for a file:
  - "command": "search_file"
  - "parameters": {"filename": "name_of_file.ext", "search_path": "path\\to\\start_search"}

* Ask for clarification:
  - "command": "clarify"
  - "parameters": {"question": "Your clarifying question"}

* Respond with a message:
  - "command": "respond"
  - "parameters": {"message": "General response"}

**Critical Safety Rule:**  
Before destructive actions (`delete_file`, `delete_directory`, `move_item`, `write_file`), you MUST first ask for explicit confirmation using the `clarify` command.
"""

agent = FileAgent(system_prompt=AGENT_SYSTEM_PROMPT)


class UserRequest(BaseModel):
    prompt: str
    current_dir: str = "."


@app.post("/file-agent")
def handle_request(request: UserRequest):
    result = agent.process_request(request.prompt, request.current_dir)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result
