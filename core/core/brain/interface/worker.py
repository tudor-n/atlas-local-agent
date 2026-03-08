import ollama
from colorama import Fore
from core.brain.interface.tools import ToolRegistry

class WorkerNode:
    def __init__(self, model_name="qwen2.5-coder:3b"):
        self.model_name = model_name
        
        # Instantiate the new Tool Registry
        self.tools = ToolRegistry()
        
        # The ROBUST JSON Prompt
        self.system_prompt = (
            "You are ATLAS's internal autonomous operator. "
            "Your ONLY job is to execute the user's task by outputting the correct XML tags.\n\n"
            f"{self.tools.tool_schema}\n\n"
            "[STRICT RULES]\n"
            "1. CRITICAL: If the user asks you to 'write', 'create', or 'save' a file, you MUST use the <tool>write_file</tool> tool BEFORE using <tool>finish</tool>. Never finish a file-creation task without actually saving it to disk!\n"
            "2. Output ONLY the raw XML tags. No markdown formatting. No explanations.\n"
            "3. If asked to %text about 'yourself', your identity is ATLAS, a local engineering assistant created by Tudor. NEVER mention Qwen, Alibaba, or being an AI language model.\n"
            "4. Do NOT use placeholder paths like '/path/to/file'. Use the exact filename requested."
            "5. When using <tool>finish</tool>, you MUST include the specific data you found or generated (like numbers, names, or file paths) in the <message> tag. Do not just say 'task complete'.\n"
            "6. DATA TRANSFER: If you use web_search or ask_architect, you MUST copy the exact facts, text, or code they give you and put it inside the <content> tag of your write_file step. Do not use placeholders.\n"
            "7. ERROR HANDLING: If a tool returns an [ERROR], you MUST NOT use the finish tool. You must read the error, think about why it failed, and use another tool to fix it.\n"
            "8. COMPREHENSIVE SUMMARY: When you use the finish tool, your <message> MUST contain the answers to ALL parts of the user's prompt. If they asked for a list of files AND a script execution, you must include the full list of files AND the execution output in your message.\n"
        )

    def execute_task(self, user_task: str) -> str:
        print(Fore.LIGHTBLACK_EX + f" [WORKER] Starting Autonomous Loop for: '{user_task}'...")
        
        # We start a conversation thread for the Worker
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Task: {user_task}\nBegin your task. Output your first XML tool call."}
        ]
        
        execution_log = []
        raw_data_memory = []
        
        # The ReAct Loop (Max 5 steps to prevent infinite loops)
        for step in range(8):
            print(Fore.LIGHTBLACK_EX + f" [WORKER] Thinking (Step {step + 1}/5)...")
            
            try:
                import ollama
                response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    keep_alive=-1,
                    options={"temperature": 0.0, "top_p": 0.1}
                )
                xml_call = response['message']['content'].strip(' `\n')
                
                # Strip markdown just in case
                if xml_call.startswith('xml\n'): xml_call = xml_call[4:]
                
                print(Fore.CYAN + f" [WORKER ACTION]:\n{xml_call[:150]}...\n")
                
                # ── DID HE FINISH? ──
                import re
                tool_match = re.search(r'<tool>(.*?)</tool>', xml_call, re.IGNORECASE)
                
                if not tool_match:
                    print(Fore.RED + " [SYSTEM FEEDBACK]: No <tool> tag found.")
                    messages.append({"role": "assistant", "content": xml_call})
                    messages.append({"role": "user", "content": "[ERROR] No <tool> tag found. You suffered from formatting degradation. You MUST wrap your action in <tool>...</tool> tags. Example:\n<tool>write_file</tool>\n<filepath>main.cpp</filepath>\n<content>...</content>"})
                    continue
                    
                action = tool_match.group(1).strip().lower()
                
                # ── 2. DID HE FINISH? ──
                if action == "finish":
                    # ANTI-LIAR FAILSAFE: Check if the last system feedback was an error
                    if execution_log and messages[-1]["role"] == "user" and "[ERROR]" in messages[-1]["content"]:
                        print(Fore.RED + " [SYSTEM] Blocked ATLAS from finishing. Last action was an error.")
                        messages.append({"role": "assistant", "content": xml_call})
                        messages.append({"role": "user", "content": "[CRITICAL SYSTEM OVERRIDE] You cannot finish. Your last tool execution returned an [ERROR]. You MUST read the error and use a tool (like write_file, patch_file, or execute_bash) to fix it before finishing."})
                        continue

                    final_msg = "Task complete."
                    msg_match = re.search(r'<message>(.*?)</message>', xml_call, re.IGNORECASE | re.DOTALL)
                    if msg_match: final_msg = msg_match.group(1).strip()
                    
                    log_summary = " -> ".join(execution_log)

                    bypass_data = "\n\n".join(raw_data_memory)

                    return f"[SUCCESS] {final_msg} (Steps taken: {log_summary})"
                
                # ── 3. EXECUTE TOOL & FEEDBACK ──
                result = self.tools.execute_tool(xml_call)
                print(Fore.YELLOW + f" [SYSTEM FEEDBACK]: {result[:100]}...")

                if action in ["list_directory", "read_file", "web_search", "execute_bash"]:
                    raw_data_memory.append(f"[{action.upper()} DATA]:\n{result[:1000]}")
                
                execution_log.append(action)
                
                # Add his action and the system's feedback to the history so he can read it!
                messages.append({"role": "assistant", "content": xml_call})
                messages.append({"role": "user", "content": f"System Output:\n{result}\nWhat is your next XML tool call? CRITICAL: Output ONLY ONE tool tag."})
                
            except Exception as e:
                return f"[CRITICAL ERROR] Loop failure on step {step+1}: {e}"
                
        return f"[WARNING] Worker hit the 5-step limit. It might not have finished. Actions taken: {' -> '.join(execution_log)}"
        
    def warmup(self):
        """Silently pre-loads the model into VRAM so the first command has zero latency."""
        print(Fore.LIGHTBLACK_EX + f" [WORKER] Warming up motor cortex ({self.model_name})...")
        try:
            import ollama
            # A tiny dummy prompt just to force the weights into memory
            ollama.generate(model=self.model_name, prompt="status", keep_alive=-1)
        except Exception as e:
            print(Fore.RED + f" [WORKER ERROR] Warm-up failed: {e}")