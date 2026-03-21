import os
import re
import subprocess
from colorama import Fore
import docker
from config import SANDBOX_PATH, ARCHITECT_LOCAL_MODEL, BASH_TIMEOUT, OLLAMA_KEEP_ALIVE, DOCKER_IMAGE, CONTAINER_NAME
from core.brain.interface.vram_manager import vram

try:
    docker_client = docker.from_env()
except docker.errors.DockerException:
    print(Fore.RED + " [SYSTEM] WARNING: Docker is not running. Sandbox is offline.")
    docker_client = None

def get_or_create_sandbox():
    """Ensures the worker container is running and the shared volume exists."""
    if not docker_client: return None
    
    os.makedirs(SANDBOX_PATH, exist_ok=True)
    
    try:
        container = docker_client.containers.get(CONTAINER_NAME)
        if container.status != 'running':
            container.start()
        return container
    except docker.errors.NotFound:
        print(Fore.MAGENTA + f" [SANDBOX] Booting new secure container ({DOCKER_IMAGE})...")
        return docker_client.containers.run(
            DOCKER_IMAGE,
            command="tail -f /dev/null",
            name=CONTAINER_NAME,
            volumes={SANDBOX_PATH: {'bind': '/workspace', 'mode': 'rw'}}, 
            working_dir='/workspace',
            detach=True,
            network_mode="bridge" 
        )

class ToolRegistry:
    def __init__(self, sandbox_path=SANDBOX_PATH):
        self.sandbox_path = sandbox_path
        os.makedirs(self.sandbox_path, exist_ok=True)

        self.tool_schema = """
AVAILABLE TOOLS:

1. Read a file
<tool>read_file</tool>
<filepath>filename.txt</filepath>

2. Write to a file
<tool>write_file</tool>
<filepath>filename.txt</filepath>
<content>exact content here</content>

3. Execute a terminal command
<tool>execute_bash</tool>
<command>dir</command>

4. Delete a file
<tool>delete_file</tool>
<filepath>filename.txt</filepath>

5. Finish the task
<tool>finish</tool>
<message>Specific summary: what was done, filenames created, results found.</message>

6. Consult the Local Architect
<tool>ask_local_architect</tool>
<prompt>Write Python code for X. Include all constraints. I will handle file writing.</prompt>

7. Consult the Cloud Architect (Gemini)
<tool>ask_cloud_architect</tool>
<prompt>Write a multi-file C++ project. Separate files with // --- FILENAME: x.cpp ---</prompt>

8. Search the Web
<tool>web_search</tool>
<query>How to use FastAPI in Python</query>

9. List Directory Contents
<tool>list_directory</tool>
<path>.</path>

10. Patch an existing file (Search and Replace)
<tool>patch_file</tool>
<filepath>script.py</filepath>
<search>exact existing text</search>
<replace>new text</replace>

11. Save a fact to long-term memory
<tool>remember</tool>
<fact>The user prefers tabs over spaces in Python.</fact>

12. Schedule a task for later
<tool>schedule_task</tool>
<task>Remind user to check the server logs.</task>
<delay_minutes>30</delay_minutes>

13. Read a URL / webpage
<tool>read_url</tool>
<url>https://docs.python.org/3/library/asyncio.html</url>

14. Execute Python expression directly
<tool>python_repl</tool>
<code>sum(range(1, 101))</code>

INSTRUCTIONS: Output ONLY ONE XML tool block at a time. No markdown. No commentary.
"""

    def execute_tool(self, xml_string: str) -> str:
        try:
            tool_match = re.search(r'<tool>(.*?)</tool>', xml_string, re.IGNORECASE | re.DOTALL)
            if not tool_match:
                return "[ERROR] No valid <tool> tag found."
            action = tool_match.group(1).strip().lower()

            if action == "read_file":
                fp = re.search(r'<filepath>(.*?)</filepath>', xml_string, re.IGNORECASE | re.DOTALL)
                if not fp: return "[ERROR] Missing <filepath>."
                return self._read_file(fp.group(1).strip())

            elif action == "write_file":
                fp = re.search(r'<filepath>(.*?)</filepath>', xml_string, re.IGNORECASE | re.DOTALL)
                ct = re.search(r'<content>(.*?)</content>', xml_string, re.IGNORECASE | re.DOTALL)
                if not fp or not ct: return "[ERROR] Missing <filepath> or <content>."
                raw = ct.group(1).strip()
                if raw.startswith("<![CDATA[") and raw.endswith("]]>"):
                    raw = raw[9:-3].strip()
                return self._write_file(fp.group(1).strip(), raw)

            elif action == "delete_file":
                fp = re.search(r'<filepath>(.*?)</filepath>', xml_string, re.IGNORECASE | re.DOTALL)
                if not fp: return "[ERROR] Missing <filepath>."
                return self._delete_file(fp.group(1).strip())

            elif action == "execute_bash":
                cmd = re.search(r'<command>(.*?)</command>', xml_string, re.IGNORECASE | re.DOTALL)
                if not cmd: return "[ERROR] Missing <command>."
                return self._execute_bash(cmd.group(1).strip())

            elif action == "ask_local_architect":
                pm = re.search(r'<prompt>(.*?)</prompt>', xml_string, re.IGNORECASE | re.DOTALL)
                if not pm: return "[ERROR] Missing <prompt>."
                return self._ask_local_architect(pm.group(1).strip())

            elif action == "ask_cloud_architect":
                pm = re.search(r'<prompt>(.*?)</prompt>', xml_string, re.IGNORECASE | re.DOTALL)
                if not pm: return "[ERROR] Missing <prompt>."
                return self._ask_cloud_architect(pm.group(1).strip())

            elif action == "web_search":
                qm = re.search(r'<query>(.*?)</query>', xml_string, re.IGNORECASE | re.DOTALL)
                if not qm: return "[ERROR] Missing <query>."
                return self._web_search(qm.group(1).strip())

            elif action == "list_directory":
                pm = re.search(r'<path>(.*?)</path>', xml_string, re.IGNORECASE | re.DOTALL)
                if not pm: return "[ERROR] Missing <path>."
                return self._list_directory(pm.group(1).strip())

            elif action == "patch_file":
                fp = re.search(r'<filepath>(.*?)</filepath>', xml_string, re.IGNORECASE | re.DOTALL)
                st = re.search(r'<search>(.*?)</search>', xml_string, re.IGNORECASE | re.DOTALL)
                rt = re.search(r'<replace>(.*?)</replace>', xml_string, re.IGNORECASE | re.DOTALL)
                if not fp or not st or not rt: return "[ERROR] Missing filepath, search, or replace."
                return self._patch_file(fp.group(1).strip(), st.group(1), rt.group(1))

            elif action == "remember":
                fm = re.search(r'<fact>(.*?)</fact>', xml_string, re.IGNORECASE | re.DOTALL)
                if not fm: return "[ERROR] Missing <fact>."
                return self._remember(fm.group(1).strip())

            elif action == "schedule_task":
                tm = re.search(r'<task>(.*?)</task>', xml_string, re.IGNORECASE | re.DOTALL)
                dm = re.search(r'<delay_minutes>(.*?)</delay_minutes>', xml_string, re.IGNORECASE | re.DOTALL)
                if not tm: return "[ERROR] Missing <task>."
                delay = int(dm.group(1).strip()) * 60 if dm else 0
                return self._schedule_task(tm.group(1).strip(), delay)

            elif action == "read_url":
                um = re.search(r'<url>(.*?)</url>', xml_string, re.IGNORECASE | re.DOTALL)
                if not um: return "[ERROR] Missing <url>."
                return self._read_url(um.group(1).strip())

            elif action == "python_repl":
                cm = re.search(r'<code>(.*?)</code>', xml_string, re.IGNORECASE | re.DOTALL)
                if not cm: return "[ERROR] Missing <code>."
                return self._python_repl(cm.group(1).strip())

            else:
                return f"[ERROR] Unknown tool: '{action}'"

        except Exception as e:
            return f"[ERROR] Tool execution failed: {e}"

    def _get_safe_path(self, filename: str) -> str:
        safe = os.path.abspath(os.path.join(self.sandbox_path, filename))
        if not safe.startswith(os.path.abspath(self.sandbox_path)):
            raise ValueError("Sandbox escape attempt blocked.")
        return safe

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
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"[SUCCESS] Wrote to {filepath}"
        except Exception as e:
            return f"[ERROR] Write failed: {e}"

    def _delete_file(self, filepath: str) -> str:
        try:
            target = self._get_safe_path(filepath)
            if os.path.exists(target):
                os.remove(target)
                return f"[SUCCESS] Deleted {filepath}"
            return f"[ERROR] File not found: {filepath}"
        except Exception as e:
            return f"[ERROR] Delete failed: {e}"

    def _execute_bash(self, command: str) -> str:
        """Executes a terminal command safely inside the Docker sandbox."""
        print(Fore.YELLOW + f" [SANDBOX EXEC]: {command}")
        
        container = get_or_create_sandbox()
        if not container:
            return "[ERROR] Docker sandbox is unavailable. Please start Docker Desktop."
            
        try:
            exit_code, output = container.exec_run(
                ["/bin/sh", "-c", command], 
                workdir="/workspace"
            )
            
            result_str = output.decode('utf-8', errors='replace').strip()
            
            if exit_code != 0:
                return f"[ERROR] Command failed with exit code {exit_code}.\nOutput:\n{result_str}"
                
            return result_str if result_str else "[SUCCESS] Command executed silently."
            
        except Exception as e:
            return f"[CRITICAL ERROR] Sandbox execution failed: {str(e)}"

    def _ask_local_architect(self, prompt: str) -> str:
        import ollama
        print(Fore.MAGENTA + " [LOCAL ARCHITECT] Generating...")

        # Register if not yet registered (lazy — architect is rarely called)
        vram.register("architect", ARCHITECT_LOCAL_MODEL)

        arch_prompt = (
            "You are an expert Senior Software Engineer. Output ONLY raw code.\n"
            "No explanations. No markdown fences. No pleasantries.\n"
            "If multiple files: separate with // --- FILENAME: name.ext ---\n"
            f"REQUEST: {prompt}\n"
        )
        try:
            vram.ensure_loaded("architect")
            code = ollama.generate(
                model=ARCHITECT_LOCAL_MODEL, prompt=arch_prompt,
                keep_alive=vram.get_keep_alive("architect"),
            )['response'].strip()
            # Immediately release the heavy model so the butler can reload
            vram.release("architect")

            refusals = ["I'm sorry", "I cannot", "I apologize", "As an AI"]
            if any(code.startswith(r) for r in refusals):
                return "[ERROR] Architect refused. Rephrase as a pure code request."
            return f"[SUCCESS] Architect code:\n{code}\n\n[REMINDER] Use write_file to save this to disk."
        except Exception as e:
            vram.release("architect")
            return f"[ERROR] Local Architect failed: {e}"

    def _ask_cloud_architect(self, prompt: str) -> str:
        try:
            from google import genai
            from config import GEMINI_API_KEY
            print(Fore.CYAN + " [CLOUD ARCHITECT] Transmitting to Gemini...")
            if not GEMINI_API_KEY:
                return "[ERROR] GEMINI_API_KEY not set."
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=f"Senior Software Architect. Return ONLY raw code. No markdown fences. No explanations.\nTask: {prompt}",
            )
            reply = response.text.strip()
            reply = re.sub(r'^```[a-zA-Z]*\n?', '', reply)
            reply = re.sub(r'\n?```$', '', reply).strip()
            return f"[SUCCESS] Cloud Architect code:\n{reply}"
        except ImportError:
            return "[ERROR] Missing 'google-genai'. Run: pip install google-genai"
        except Exception as e:
            return f"[ERROR] Cloud API failed: {e}"

    def _web_search(self, query: str) -> str:
        try:
            from ddgs import DDGS
            print(Fore.YELLOW + f" [WEB] Searching: '{query}'")
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=3):
                    results.append(f"Title: {r['title']}\nSnippet: {r['body']}\n")
            if not results:
                return "[WARNING] No results found."
            return f"[SUCCESS] Web Results:\n" + "\n---\n".join(results)
        except ImportError:
            return "[ERROR] Missing 'ddgs'. Run: pip install ddgs"
        except Exception as e:
            return f"[ERROR] Search failed: {e}"

    def _list_directory(self, path: str) -> str:
        try:
            safe = self._get_safe_path(path)
            if not os.path.exists(safe):
                return f"[ERROR] Path not found: {path}"
            tree = []
            start_depth = safe.rstrip(os.sep).count(os.sep)
            for root, dirs, files in os.walk(safe):
                depth = root.rstrip(os.sep).count(os.sep) - start_depth
                if depth > 1:
                    del dirs[:]
                    continue
                indent = "  " * depth
                tree.append(f"{indent}📁 {os.path.basename(root) or path}/")
                for f in sorted(files):
                    if not f.endswith(('.pyc', '.exe')):
                        tree.append(f"{indent}  📄 {f}")
            return "[SUCCESS] Directory:\n" + "\n".join(tree)
        except Exception as e:
            return f"[ERROR] List failed: {e}"

    def _patch_file(self, filepath: str, search_text: str, replace_text: str) -> str:
        try:
            target = self._get_safe_path(filepath)
            if not os.path.exists(target):
                return f"[ERROR] File not found: {filepath}"
            with open(target, 'r', encoding='utf-8') as f:
                content = f.read()
            for tag in ["<![CDATA[", "]]>"]:
                search_text = search_text.replace(tag, "")
                replace_text = replace_text.replace(tag, "")
            if search_text.strip() not in content:
                return "[ERROR] Search text not found. Use read_file first to get the exact string."
            updated = content.replace(search_text.strip(), replace_text.strip(), 1)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(updated)
            return f"[SUCCESS] Patched {filepath}."
        except Exception as e:
            return f"[ERROR] Patch failed: {e}"

    def _remember(self, fact: str) -> str:
        try:
            from core.brain.cognition.memory import MemorySystem
            mem = MemorySystem()
            saved = mem.save_memory(fact, importance=7.0, tags=["worker_saved"])
            if saved:
                return f"[SUCCESS] Committed to long-term memory: '{fact[:80]}'"
            return "[SUCCESS] Similar fact already in memory."
        except Exception as e:
            return f"[ERROR] Memory save failed: {e}"

    def _schedule_task(self, task: str, delay_seconds: int = 0) -> str:
        try:
            from core.brain.cognition.task_queue import TaskQueue
            from core.brain.interface.bus import EventBus
            tq = TaskQueue(EventBus())
            entry = tq.add(task, due_in_seconds=delay_seconds)
            minutes = delay_seconds // 60
            return f"[SUCCESS] Task scheduled in {minutes}m: '{task[:60]}'"
        except Exception as e:
            return f"[ERROR] Scheduling failed: {e}"

    def _read_url(self, url: str) -> str:
        try:
            import urllib.request
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._skip = False
                    self.text = []
                def handle_starttag(self, tag, attrs):
                    if tag in ('script', 'style', 'nav', 'footer', 'header'):
                        self._skip = True
                def handle_endtag(self, tag):
                    if tag in ('script', 'style', 'nav', 'footer', 'header'):
                        self._skip = False
                def handle_data(self, data):
                    if not self._skip and data.strip():
                        self.text.append(data.strip())

            print(Fore.YELLOW + f" [URL READER] Fetching: {url}")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            parser = _TextExtractor()
            parser.feed(html)
            text = ' '.join(parser.text)
            text = re.sub(r'\s+', ' ', text).strip()
            return f"[SUCCESS] Page content:\n{text[:3000]}"
        except Exception as e:
            return f"[ERROR] URL read failed: {e}"

    def _python_repl(self, code: str) -> str:
        forbidden = ['import os', 'import sys', 'subprocess', 'open(', 'exec(', 'eval(', '__import__']
        for f in forbidden:
            if f in code:
                return f"[ERROR] SECURITY BLOCK: '{f}' not allowed in python_repl."
        try:
            import io, contextlib
            stdout_capture = io.StringIO()
            local_ns = {}
            with contextlib.redirect_stdout(stdout_capture):
                exec(compile(code, '<repl>', 'exec'), {"__builtins__": __builtins__}, local_ns)
            output = stdout_capture.getvalue().strip()
            if not output and local_ns:
                last_val = list(local_ns.values())[-1]
                output = repr(last_val)
            return f"[SUCCESS] Result:\n{output[:1000]}" if output else "[SUCCESS] Executed with no output."
        except Exception as e:
            return f"[ERROR] Python REPL: {e}"