import os
import re
import subprocess

class ToolRegistry:
    def __init__(self, sandbox_path="D:\\atlas_sandbox"):
        self.sandbox_path = sandbox_path
        if not os.path.exists(self.sandbox_path):
            os.makedirs(self.sandbox_path)

        # ── The XML Schema the Worker must follow ──
        self.tool_schema = """
AVAILABLE TOOLS:

1. Read a file
<tool>read_file</tool>
<filepath>filename.txt</filepath>

2. Write to a file
Use this to create or overwrite a file. CRITICAL: You must place the ACTUAL data, code, or search results inside the content tag. Do NOT output placeholder text.
<tool>write_file</tool>
<filepath>filename.txt</filepath>
<content>The actual specific information, text, or code you want to save goes here.</content>

3. Execute a terminal command
<tool>execute_bash</tool>
<command>dir</command>

4. Delete a file
<tool>delete_file</tool>
<filepath>filename.txt</filepath>

5. Finish the task
<tool>finish</tool>
<message>I have completed the task.</message>

6. Consult the Local Architect (Privacy-Safe)
Use this for complex code or new projects. CRITICAL: You MUST include all of the user's specific constraints (like "multi-file", "use python", etc.) in your prompt. Ask the Architect ONLY to write the code. YOU must do the file writing.
<tool>ask_local_architect</tool>
<prompt>Write the C++ code for an OOP Snake game. It MUST be a multi-file project with separated headers. I will handle saving the files.</prompt>

7. Consult the Cloud Architect (Gemini / Claude / OpenAI)
Use this for massive, multi-file projects or extremely complex logic. It is much faster and smarter than the local architect. 
CRITICAL: You MUST include the exact constraints (e.g., "multi-file", "C++") in the prompt.
<tool>ask_cloud_architect</tool>
<prompt>Write a multi-file C++ Chess game. Separate the code with // --- FILENAME: name.cpp --- blocks. I will handle writing the files.</prompt>

8. Search the Web
Use this to search the internet for documentation, syntax, or facts before writing code.
<tool>web_search</tool>
<query>How to use FastAPI in Python</query>

9. Finish the task
Use this when you are completely done. CRITICAL: The <message> tag MUST contain a detailed summary of what you did, including specific facts found, filenames created, and exact results.
<tool>finish</tool>
<message>I used [Tool Name], found [Specific Fact/Result], and saved the output to [Filename].</message>

10. List Directory Contents
Use this to see what files and folders exist in a specific path before trying to read or edit them. Use "." for the current directory.
<tool>list_directory</tool>
<path>.</path>

11. Patch an existing file (Search and Replace)
Use this to edit a specific part of a file without rewriting the whole thing. CRITICAL: The <search> text must exactly match the existing text in the file.
<tool>patch_file</tool>
<filepath>script.py</filepath>
<search>print("hello")</search>
<replace>print("Hello World!")</replace>

12. Execute Terminal Command
Use this to run python scripts, install pip packages, or execute shell commands. Do NOT run interactive commands that require user input.
<tool>execute_bash</tool>
<command>python script.py</command>

INSTRUCTIONS: 
You must output ONLY the XML tags for ONE tool at a time. Do not wrap it in markdown. Do not add conversational text.
"""

    def execute_tool(self, xml_string: str) -> str:
        """Parses the Worker's XML and executes the native Python tool."""
        try:
            # Extract the tool name
            tool_match = re.search(r'<tool>(.*?)</tool>', xml_string, re.IGNORECASE | re.DOTALL)
            if not tool_match:
                return f"[ERROR] No valid <tool> tag found in output."
            
            action = tool_match.group(1).strip()

            if action == "read_file":
                filepath = re.search(r'<filepath>(.*?)</filepath>', xml_string, re.IGNORECASE | re.DOTALL)
                if not filepath: return "[ERROR] Missing <filepath> tag."
                return self._read_file(filepath.group(1).strip())

            elif action == "write_file":
                filepath = re.search(r'<filepath>(.*?)</filepath>', xml_string, re.IGNORECASE | re.DOTALL)
                content = re.search(r'<content>(.*?)</content>', xml_string, re.IGNORECASE | re.DOTALL)
                if not filepath or not content: return "[ERROR] Missing <filepath> or <content> tag."
                
                # Strip CDATA if the LLM uses it
                raw_content = content.group(1).strip()
                if raw_content.startswith("<![CDATA[") and raw_content.endswith("]]>"):
                    raw_content = raw_content[9:-3].strip()
                    
                return self._write_file(filepath.group(1).strip(), raw_content)

            elif action == "delete_file":
                filepath = re.search(r'<filepath>(.*?)</filepath>', xml_string, re.IGNORECASE | re.DOTALL)
                if not filepath: return "[ERROR] Missing <filepath> tag."
                return self._delete_file(filepath.group(1).strip())

            elif action == "execute_bash":
                command = re.search(r'<command>(.*?)</command>', xml_string, re.IGNORECASE | re.DOTALL)
                if not command: return "[ERROR] Missing <command> tag."
                return self._execute_bash(command.group(1).strip())
            
            elif action == "ask_local_architect":
                prompt_match = re.search(r'<prompt>(.*?)</prompt>', xml_string, re.IGNORECASE | re.DOTALL)
                if not prompt_match: return "[ERROR] Missing <prompt> tag."
                return self._ask_local_architect(prompt_match.group(1).strip())

            elif action == "ask_cloud_architect":
                prompt_match = re.search(r'<prompt>(.*?)</prompt>', xml_string, re.IGNORECASE | re.DOTALL)
                if not prompt_match: return "[ERROR] Missing <prompt> tag."
                return self._ask_cloud_architect(prompt_match.group(1).strip())
            
            elif action == "web_search":
                query_match = re.search(r'<query>(.*?)</query>', xml_string, re.IGNORECASE | re.DOTALL)
                if not query_match: return "[ERROR] Missing <query> tag."
                return self._web_search(query_match.group(1).strip())
            
            elif action == "list_directory":
                path_match = re.search(r'<path>(.*?)</path>', xml_string, re.IGNORECASE | re.DOTALL)
                if not path_match: return "[ERROR] Missing <path> tag."
                return self._list_directory(path_match.group(1).strip())
            
            elif action == "patch_file":
                filepath = re.search(r'<filepath>(.*?)</filepath>', xml_string, re.IGNORECASE | re.DOTALL)
                search_text = re.search(r'<search>(.*?)</search>', xml_string, re.IGNORECASE | re.DOTALL)
                replace_text = re.search(r'<replace>(.*?)</replace>', xml_string, re.IGNORECASE | re.DOTALL)
                
                if not filepath or not search_text or not replace_text: 
                    return "[ERROR] Missing filepath, search, or replace tag."
                
                return self._patch_file(filepath.group(1).strip(), search_text.group(1), replace_text.group(1))
            
            elif action == "execute_bash":
                command_match = re.search(r'<command>(.*?)</command>', xml_string, re.IGNORECASE | re.DOTALL)
                if not command_match: return "[ERROR] Missing <command> tag."
                return self._execute_bash(command_match.group(1).strip())

            else:
                return f"[ERROR] Unknown tool requested: {action}"

        except Exception as e:
            return f"[ERROR] Tool execution failed: {e}"

    # ── NATIVE PYTHON TOOLS ──
    def _get_safe_path(self, filename: str) -> str:
        safe_path = os.path.abspath(os.path.join(self.sandbox_path, filename))
        if not safe_path.startswith(os.path.abspath(self.sandbox_path)):
            raise ValueError("Sandbox escape attempt detected.")
        return safe_path

    def _read_file(self, filepath: str) -> str:
        try:
            target = self._get_safe_path(filepath)
            with open(target, 'r', encoding='utf-8') as f:
                return f"[SUCCESS] File contents:\n{f.read()}"
        except Exception as e:
            return f"[ERROR] Read failed: {e}"

    def _write_file(self, filepath: str, content: str) -> str:
        try:
            target = self._get_safe_path(filepath)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"[SUCCESS] Successfully wrote to {filepath}"
        except Exception as e:
            return f"[ERROR] Write failed: {e}"
        
    def _delete_file(self, filepath: str) -> str:
        try:
            target = self._get_safe_path(filepath)
            if os.path.exists(target):
                os.remove(target)
                return f"[SUCCESS] Deleted {filepath}"
            else:
                return f"[ERROR] File not found: {filepath}"
        except Exception as e:
            return f"[ERROR] Delete failed: {e}"

    def _execute_bash(self, command: str) -> str:
        """Executes a terminal command and returns the stdout/stderr."""
        import subprocess
        from colorama import Fore
        
        # --- 🛡️ THE SECURITY BLACKLIST 🛡️ ---
        # Prevent the LLM from hallucinating destructive Windows/Linux commands
        forbidden_keywords = ["del ", "rm ", "rmdir", "format ", "diskpart", "mkfs"]
        command_lower = command.lower()
        
        for keyword in forbidden_keywords:
            if keyword in command_lower or command_lower.startswith(keyword.strip()):
                print(Fore.RED + f"\n [SECURITY BLOCK] ATLAS attempted a destructive command: {command}")
                return f"[ERROR] SECURITY BLOCK: You are not allowed to use '{keyword}' in the terminal. If you need to delete a file, use the <tool>delete_file</tool> XML tool instead."
        # ------------------------------------

        print(Fore.RED + f"\n [TERMINAL] Executing: {command}...")
        
        try:
            # We use shell=True to allow commands like 'dir' or pip installations
            result = subprocess.run(
                command,
                shell=True,
                cwd="D:\\atlas_sandbox", # <--- POINT THIS TO YOUR ACTUAL SANDBOX DIRECTORY!
                capture_output=True,
                text=True,
                timeout=15 
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            # If the command succeeded
            if result.returncode == 0:
                if not output: 
                    return "[SUCCESS] Command executed with no output."
                # Truncate output if it's massive so it doesn't blow out the LLM context limit
                return f"[SUCCESS] Output:\n{output[:1500]}" 
            
            # If the command threw an error
            else:
                return f"[ERROR] Command Failed (Code {result.returncode}):\n{error}\n{output}"
                
        except subprocess.TimeoutExpired:
            return "[ERROR] Command timed out after 15 seconds. Do not run interactive commands that wait for user input."
        except Exception as e:
            return f"[ERROR] Execution failed: {e}"
        
    def _ask_local_architect(self, prompt: str) -> str:
        """Sends a complex coding prompt to the heavyweight local model."""
        import ollama
        from colorama import Fore
        print(Fore.MAGENTA + f"\n [LOCAL ARCHITECT] Waking up Qwen 14B... (Expect high CPU usage)")
        
        # --- 1. THE 'SOFT' ARCHITECT OVERRIDE ---
        # We remove the aggressive "Do NOT" commands so we don't trigger safety filters.
        architect_prompt = (
            "You are an expert Senior C++ Developer. Please provide the raw code for the requested project.\n"
            "Output ONLY the code. No explanations, no pleasantries, no conversational text.\n"
            "If multiple files are needed, clearly separate them using this format:\n"
            "// --- FILENAME: main.cpp ---\n[code here]\n\n"
            f"USER REQUEST: {prompt}\n"
        )
        
        try:
            response = ollama.generate(model="qwen2.5-coder:14b", prompt=architect_prompt)
            code = response['response'].strip()
            
            # --- 2. THE BOUNCER ---
            # If the model still refuses, we block it from going to the Worker.
            refusal_triggers = ["I'm sorry", "I cannot", "I apologize", "As an AI"]
            if any(code.startswith(trigger) for trigger in refusal_triggers):
                print(Fore.RED + " [SYSTEM] Architect refused the prompt. Intercepting...")
                return "[ERROR] The Architect refused to generate the code. It said: " + code[:100] + "... You must rephrase your request to be purely about writing code."

            # --- 3. THE AMNESIA GUARD ---
            return f"[SUCCESS] Local Architect returned this code:\n{code}\n\n[CRITICAL SYSTEM REMINDER TO WORKER]: You have the code. You MUST now use the <tool>write_file</tool> XML tag to save this code to the hard drive!"
            
        except Exception as e:
            return f"[ERROR] Local Architect failed: {e}"

    def _ask_cloud_architect(self, prompt: str) -> str:
        """Sends complex logic to the Gemini Pro API."""
        from colorama import Fore
        import os
        try:
            from google import genai
            print(Fore.CYAN + f"\n [CLOUD ARCHITECT] Transmitting prompt to Gemini Pro API...")
            
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                return "[ERROR] GEMINI_API_KEY environment variable not found."
                
            client = genai.Client(api_key=api_key) 
            
            # We use Gemini 2.5 Pro as it is the current flagship coding model available via the standard API
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=f"You are a Senior Cloud Architect. Return ONLY raw code. No markdown formatting (```python). Do not explain the code. Task: {prompt}",
            )
            
            reply = response.text.strip(' `\n')
            if reply.startswith('python\n'): reply = reply[7:]
            return f"[SUCCESS] Cloud Architect returned this code:\n{reply}"
        except ImportError:
            return "[ERROR] Missing 'google-genai' library. Run 'pip install google-genai'."
        except Exception as e:
            return f"[ERROR] Cloud API failed: {e}"
        
    def _web_search(self, query: str) -> str:
        """Searches the web using DuckDuckGo and returns text snippets."""
        from colorama import Fore
        try:
            from ddgs import DDGS
            print(Fore.YELLOW + f"\n [WEB SURFER] Searching the internet for: '{query}'...")
            
            results = []
            with DDGS() as ddgs:
                # We limit to 3 results so we don't overwhelm Qwen 3B's context window
                for r in ddgs.text(query, max_results=3):
                    results.append(f"Title: {r['title']}\nSnippet: {r['body']}\n")
            
            if not results:
                return "[WARNING] No results found on the web for that query."
                
            formatted_results = "\n---\n".join(results)
            return f"[SUCCESS] Web Search Results:\n{formatted_results}\n\nRead these results and take your next action."
            
        except ImportError:
            return "[ERROR] Missing library. Run 'pip install ddgs'."
        except Exception as e:
            return f"[ERROR] Web search failed: {e}"
        
    def _list_directory(self, path: str) -> str:
        """Returns a mapped tree of the directory up to 2 levels deep."""
        import os
        from colorama import Fore
        print(Fore.CYAN + f"\n [SYSTEM] Mapping directory: {path}...")
        
        try:
            safe_path = self._get_safe_path(path)
            if not os.path.exists(safe_path):
                return f"[ERROR] Directory not found: {path}"
            
            tree = []
            # Walk directory, max depth 2
            start_depth = safe_path.count(os.sep)
            for root, dirs, files in os.walk(safe_path):
                current_depth = root.count(os.sep)
                if current_depth - start_depth > 1:
                    del dirs[:] # Stop going deeper
                    continue
                
                indent = "  " * (current_depth - start_depth)
                folder_name = os.path.basename(root) if root != safe_path else path
                tree.append(f"{indent}📁 {folder_name}/")
                
                for file in files:
                    if not file.endswith(('.pyc', '.exe')): # Ignore junk files
                        tree.append(f"{indent}  📄 {file}")
            
            return "[SUCCESS] Directory contents:\n" + "\n".join(tree)
        except Exception as e:
            return f"[ERROR] Failed to list directory: {e}"
        
    def _patch_file(self, filepath: str, search_text: str, replace_text: str) -> str:
        """Replaces a specific block of text in an existing file."""
        import os
        from colorama import Fore
        try:
            target = self._get_safe_path(filepath)
            if not os.path.exists(target):
                return f"[ERROR] File not found: {filepath}"

            with open(target, 'r', encoding='utf-8') as f:
                content = f.read()

            # Clean up CDATA if the LLM wrapped it
            if search_text.strip().startswith("<![CDATA["): search_text = search_text.strip()[9:-3]
            if replace_text.strip().startswith("<![CDATA["): replace_text = replace_text.strip()[9:-3]

            # We strip trailing/leading whitespace for the match to be more forgiving
            if search_text.strip() not in content:
                return f"[ERROR] The exact search text was not found in the file. You must use <tool>read_file</tool> first to get the exact string."

            updated_content = content.replace(search_text.strip(), replace_text.strip(), 1)

            with open(target, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            print(Fore.GREEN + f" [SYSTEM] Successfully patched {filepath}")
            return f"[SUCCESS] Patched {filepath}. The exact text block was replaced."
        except Exception as e:
            return f"[ERROR] Failed to patch file: {e}"