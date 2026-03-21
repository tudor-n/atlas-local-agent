import re
import ollama
from colorama import Fore
from core.brain.interface.tools import ToolRegistry
from config import WORKER_MODEL, WORKER_MAX_STEPS
from core.brain.interface.vram_manager import vram



class WorkerNode:
    def __init__(self, model_name=WORKER_MODEL):
        self.model_name = model_name
        self.tools = ToolRegistry()
        vram.register("worker", self.model_name)
        self.system_prompt = (
            "You are ATLAS's internal autonomous operator. Execute tasks by outputting XML tool calls.\n\n"
            f"{self.tools.tool_schema}\n\n"
            "[ABSOLUTE RULES - violation causes task failure]\n"
            "1. Output ONLY raw XML. No markdown fences, no explanations, no commentary.\n"
            "2. NEVER write '// --- FILENAME: x ---' or any file header comment into the content tag. Write ONLY the pure file content.\n"
            "3. For CREATE tasks: use write_file directly. Do NOT read_file a file that does not exist yet.\n"
            "4. For MODIFY tasks: use read_file first, then patch_file or write_file.\n"
            "5. Identity: you are ATLAS. Never mention Qwen, models, or AI.\n"
            "6. finish <message> MUST contain specific facts: filenames, outputs, results. Never say 'task complete' with no details.\n"
            "7. After [ERROR]: state what failed and why, then output a corrected XML call.\n"
            "8. After 3 consecutive [ERROR] responses: use finish with the error details rather than looping forever.\n"
            "9. NEVER read_file a file you are about to create. NEVER.\n"
            "10. For web_search/read_url/ask_architect: the result you get IS the data. Copy it into write_file content.\n"
        )

    def _strip_markdown(self, text: str) -> str:
        stripped = text.strip()
        if '```' in stripped:
            lines = stripped.split('\n')
            cleaned = []
            in_fence = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_fence = not in_fence
                    continue
                cleaned.append(line)
            stripped = '\n'.join(cleaned).strip()
        return stripped

    def execute_task(self, user_task: str, context: str = "") -> str:
        print(Fore.LIGHTBLACK_EX + f" [WORKER] Starting: '{user_task[:80]}'")
        vram.ensure_loaded("worker")
        task_content = f"Task: {user_task}"
        if context:
            task_content += f"\n\n[CONTEXT FROM PREVIOUS STEP]:\n{context}"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{task_content}\n\nOutput your first XML tool call now."}
        ]
        execution_log = []
        raw_data_memory = []
        consecutive_errors = 0

        for step in range(WORKER_MAX_STEPS):
            print(Fore.LIGHTBLACK_EX + f" [WORKER] Step {step + 1}/{WORKER_MAX_STEPS}")
            try:
                response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    keep_alive=vram.get_keep_alive("worker"),
                    options={"temperature": 0.0, "top_p": 0.05, "num_predict": 1200}
                )
                xml_call = self._strip_markdown(response['message']['content'])
                print(Fore.CYAN + f" [WORKER ACTION]: {xml_call[:150]}")

                extracted = extract_tool_call(xml_call)
                action = extracted.get("tool")

                if not action:
                    messages.append({"role": "assistant", "content": xml_call})
                    messages.append({"role": "user", "content": "[SYSTEM] No <tool> tag found. You must output XML only. Example:\n<tool>write_file</tool>\n<filepath>hello.py</filepath>\n<content>print('hello')</content>"})
                    continue

                action = action.strip().lower()

                if action == "finish":
                    last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
                    if execution_log and "[ERROR]" in last_user_msg and consecutive_errors > 0:
                        messages.append({"role": "assistant", "content": xml_call})
                        messages.append({"role": "user", "content": "[SYSTEM] Cannot finish after an unresolved [ERROR]. Fix the error first."})
                        continue
                    
                    final_msg = extracted["parameters"].get("message", "Task complete.")
                    
                    log_str = " -> ".join(execution_log)
                    result = f"[SUCCESS] {final_msg} (Steps: {log_str})"
                    if raw_data_memory:
                        result += f"\n\n[RAW DATA]:\n" + "\n\n".join(raw_data_memory)
                    return result

                if action == "write_file":
                    raw_content = extracted["parameters"].get("content")
                    if raw_content:
                        cleaned_content = re.sub(r'^//\s*---\s*FILENAME:.*?---\s*\n?', '', raw_content, flags=re.MULTILINE).strip()
                        if cleaned_content != raw_content.strip():
                            xml_call = xml_call.replace(raw_content, f"\n{cleaned_content}\n")

                result = self.tools.execute_tool(xml_call)

                if action == "write_file":
                    content_match = re.search(r'<content>(.*?)</content>', xml_call, re.IGNORECASE | re.DOTALL)
                    if content_match:
                        raw_content = content_match.group(1)
                        cleaned_content = re.sub(r'^//\s*---\s*FILENAME:.*?---\s*\n?', '', raw_content, flags=re.MULTILINE).strip()
                        if cleaned_content != raw_content.strip():
                            xml_call = xml_call.replace(content_match.group(1), f"\n{cleaned_content}\n")

                result = self.tools.execute_tool(xml_call)
                is_error = "[ERROR]" in result
                print(Fore.YELLOW + f" [FEEDBACK]: {result[:150]}")

                if action in ["list_directory", "read_file", "web_search", "execute_bash", "read_url"]:
                    raw_data_memory.append(f"[{action.upper()}]:\n{result[:800]}")

                if is_error:
                    consecutive_errors += 1
                    execution_log.append(f"{action}[FAILED]")
                    if consecutive_errors >= 3:
                        return f"[FAILED] Stuck after {consecutive_errors} errors. Last: {result[:200]}"
                    reflection = (
                        f"[SYSTEM FEEDBACK]:\n{result}\n\n"
                        f"[REFLECTION] Step {step+1} failed. Before your next tool call:\n"
                        "- What did the error say exactly?\n"
                        "- What was wrong with your approach?\n"
                        "- What specific tool and arguments will fix it?\n"
                        "Output ONE corrected XML tool call."
                    )
                    messages.append({"role": "assistant", "content": xml_call})
                    messages.append({"role": "user", "content": reflection})
                else:
                    consecutive_errors = 0
                    execution_log.append(action)
                    messages.append({"role": "assistant", "content": xml_call})
                    messages.append({"role": "user", "content": f"[SYSTEM FEEDBACK]:\n{result}\n\nOutput your next XML tool call, or use finish if done."})

            except Exception as e:
                return f"[CRITICAL ERROR] Step {step + 1}: {e}"

        return f"[WARNING] Reached {WORKER_MAX_STEPS}-step limit. Steps taken: {' -> '.join(execution_log)}"

    def execute_plan(self, steps: list) -> str:
        print(Fore.MAGENTA + f" [WORKER] Executing {len(steps)}-step plan...")
        context = ""
        results = []
        for i, step in enumerate(steps):
            print(Fore.MAGENTA + f" [PLAN] Step {i+1}/{len(steps)}: {step[:80]}")
            result = self.execute_task(step, context=context)
            results.append(f"Step {i+1} ({step[:40]}): {result[:300]}")
            if "[FAILED]" in result or "[CRITICAL ERROR]" in result:
                print(Fore.RED + f" [PLAN] Aborted at step {i+1}.")
                break
            context = result[:500]
        return "\n".join(results)

    def warmup(self):
        print(Fore.LIGHTBLACK_EX + f" [WORKER] Warming up ({self.model_name})...")
        try:
            vram.ensure_loaded("worker")
        except Exception as e:
            print(Fore.RED + f" [WORKER] Warmup failed: {e}")
def extract_tool_call(llm_output: str) -> dict:
    """
    A robust, forgiving extractor for LLM XML tool calls.
    Handles capitalization, hallucinated attributes, and line breaks.
    """
    result = {"tool": None, "parameters": {}}
    
    tool_match = re.search(r'<tool\b[^>]*>(.*?)</tool>', llm_output, re.IGNORECASE | re.DOTALL)
    
    if tool_match:
        attr_match = re.search(r'<tool\b[^>]*name=["\']([^"\']+)["\']', llm_output, re.IGNORECASE)
        if attr_match:
            result["tool"] = attr_match.group(1).strip()
        else:
            result["tool"] = tool_match.group(1).strip()
            
    param_matches = re.finditer(r'<([a-zA-Z0-9_]+)\b[^>]*>(.*?)</\1>', llm_output, re.IGNORECASE | re.DOTALL)
    for match in param_matches:
        tag_name = match.group(1).lower()
        tag_content = match.group(2).strip()
        
        if tag_name != 'tool':
            result["parameters"][tag_name] = tag_content

    return result