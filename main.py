import time
import sys
import threading
from colorama import Fore, Style, init
import random

try:
    import msvcrt
except ImportError:
    msvcrt = None

init(autoreset=True)

try:
    from core.brain.interface.bus import EventBus
    from core.brain.interface.router import Router
    from core.brain.interface.llm import LLMEngine
    from core.brain.autonomic.autonomic import AutonomicNervousSystem
    from core.brain.autonomic.sleep import SleepSystem
    from core.brain.sensorimotor.habits import HabitLoop
    from core.brain.limbic.salience import SalienceFilter
    from core.brain.self.theory_of_mind import TheoryOfMind
    from core.brain.limbic.reward import RewardSystem
    from core.brain.self.default_mode import DefaultModeNetwork
    from core.senses.voice import Mouth
    from core.senses.hearing import Ear
    
    # --- NEW: WORKER AND MOTOR IMPORTS ---
    from core.brain.sensorimotor.motor import MotorCortex
    from core.brain.interface.worker import WorkerNode
except ImportError as e:
    print(f"{Fore.RED}Error importing modules: {e}{Style.RESET_ALL}")
    sys.exit(1)

# --- GLOBAL LOCK ---
atlas_busy = threading.Lock()

def select_mode():
    print(Fore.CYAN + "="*50)
    print(Fore.CYAN + "      ATLAS OS - BLACKWELL ARCHITECTURE jv2.0")
    print(Fore.CYAN + "="*50)
    print(Fore.WHITE + " Select Operating Mode:")
    print(Fore.YELLOW + " 1. Full Voice Assistant (Continuous VAD, Voice Out)")
    print(Fore.YELLOW + " 2. Hybrid Console (Text In, Voice Out)")
    print(Fore.YELLOW + " 3. Silent Terminal (Text In, Text Out)")
    print(Fore.CYAN + "="*50)
    
    while True:
        choice = input(Fore.BLUE + " Enter choice (1/2/3): " + Style.RESET_ALL).strip()
        if choice in ['1', '2', '3']: return int(choice)
        print(Fore.RED + " Invalid choice.")

def main():
    mode = select_mode()
    VOICE_BLEND = {'bm_george': 0.7, 'bm_fable': 0.3}
    
    try:
        bus = EventBus()
        ans = AutonomicNervousSystem(bus)
        ans.start()
        
        habits = HabitLoop(bus)
        router = Router(bus)
        brain = LLMEngine(bus=bus)
        sleep_system = SleepSystem()
        salience = SalienceFilter(bus)
        tom = TheoryOfMind(bus)
        vta = RewardSystem()
        
        # --- NEW: INITIALIZE THE HANDS ---
        motor = MotorCortex()
        worker = WorkerNode()
        worker.warmup()

        ear = None
        mouth = None
        if mode in [1, 2]: mouth = Mouth(device="cuda")
        
        if mode == 1: 
            ear = Ear(device="cuda")
            ear.start_listening()

        def handle_proactive(text):
            if atlas_busy.acquire(blocking=False):
                try:
                    if hasattr(brain, 'history'):
                        brain.history.append({"role": "assistant", "content": text})
                    elif hasattr(brain, 'messages'):
                        brain.messages.append({"role": "assistant", "content": text})
                    
                    print(f"\r{Fore.GREEN} [ATLAS] (Proactive): {text}")
                    print(Fore.BLUE + " [USER]: ", end="", flush=True)

                    if mouth:
                        stop_event = threading.Event()
                        
                        if mode == 1 and ear:
                            ear.set_interrupt_target(stop_event)
                        
                        if msvcrt:
                            while msvcrt.kbhit():
                                msvcrt.getch()
                                
                        speak_thread = threading.Thread(target=mouth.speak, args=(text, VOICE_BLEND, stop_event))
                        speak_thread.start()
                        
                        while speak_thread.is_alive():
                            if mode in [2, 3] and msvcrt and msvcrt.kbhit():
                                key = msvcrt.getch()
                                msvcrt.ungetch(key)
                                stop_event.set()
                                print(f"\r{Fore.RED} [ATLAS] (Interrupted)          ")
                                print(Fore.BLUE + " [USER]: ", end="", flush=True)
                                break
                            
                            elif mode == 1 and stop_event.is_set():
                                print(f"\r{Fore.RED} [ATLAS] (Interrupted)          ")
                                print(Fore.BLUE + " [USER]: ", end="", flush=True)
                                break
                                
                            time.sleep(0.05)
                            
                finally:
                    if mode == 1 and ear:
                        ear.set_interrupt_target(None)
                    atlas_busy.release()
                    
        dmn = DefaultModeNetwork(bus, interoception=brain.interoception, brain=brain)
        dmn.start_wandering(callback=handle_proactive)
        
        last_intent = "CHAT"
        bus.subscribe("high_salience_event", lambda x: print(Fore.RED + f"\n [AMYGDALA] High Urgency Detected: {x}"))
        bus.subscribe("user_state_updated", lambda x: print(Fore.MAGENTA + f" [THEORY OF MIND] User State: Mood={x['mood']}, Urgency={x['urgency']}"))
        
        greeting = brain.generate_greeting()
        print(Fore.GREEN + f"\n [ATLAS]: {greeting}")
        if mouth: mouth.speak(greeting, blend_config=VOICE_BLEND)
            
    except Exception as e:
        print(f"{Fore.RED}Init Error: {e}")
        return

    if mode == 1:
        print(Fore.WHITE + "\n [CONTROLS] Speak naturally to interact. Say 'exit' or 'sleep' to shutdown.\n")
    else:
        print(Fore.WHITE + "\n [CONTROLS] Type your message and press ENTER. Type 'exit' or 'sleep' to shutdown.\n")

    # --- MAIN EVENT LOOP ---
    while True:
        try:
            if mode == 1:
                user_input = ear.wait_for_input() 
                if not user_input: continue
                
                clean_input = user_input.lower().strip().replace(".", "")
                exit_words = ['exit', 'quit', 'sleep', 'shutdown', 'outflows', 'atlas exit']
                
                if any(word in clean_input for word in exit_words): 
                    break
            else:
                user_input = input(Fore.BLUE + "\n [USER]: " + Style.RESET_ALL).strip()
                if user_input.lower() in ['exit', 'quit', 'sleep', '!exit']: break

                if msvcrt:
                    while msvcrt.kbhit():
                      msvcrt.getch()
                
            if not user_input or not user_input.strip(): continue

            with atlas_busy:
                if mode == 1: print(Fore.BLUE + f" [USER]: {user_input}")

                habit_response = habits.check_trigger(user_input)
                if habit_response:
                    print(Fore.GREEN + f" [ATLAS] (Habit): {habit_response}")
                    if mouth: mouth.speak(habit_response, blend_config=VOICE_BLEND)
                    continue

                intent = router.route(user_input)
                print(Fore.YELLOW + f" [ROUTER] Intent mapped to: {intent}")
                
                score = salience.score_importance(user_input)
                print(Fore.LIGHTYELLOW_EX + f" [SALIENCE] Cognitive load score: {score}/10")
                
                user_state = tom.analyze_state(user_input)

                if user_state.get('mood') == 'positive': 
                    vta.apply_feedback(last_intent, positive=True)
                    print(Fore.CYAN + f" [VTA] (+) Rewarded {last_intent}. New Weight: {vta.get_weight(last_intent):.2f}")
                elif user_state.get('mood') == 'frustrated': 
                    vta.apply_feedback(last_intent, positive=False)
                    print(Fore.CYAN + f" [VTA] (-) Penalized {last_intent}. New Weight: {vta.get_weight(last_intent):.2f}")
                last_intent = intent

                # --- NEW: THE WORKER INTERCEPTION ---
                llm_input = user_input
                
                if intent == "COMMAND":
                    # 1. Audible acknowledgment
                    import random
                    acks = [
                        "Right away, Sir.", 
                        "At once, Sir.", 
                        "Processing your request.", 
                        "Initiating task now, Sir.", 
                        "Consider it done, Sir.",
                        "Executing, Sir."
                    ]
                    ack = random.choice(acks)
                    print(Fore.GREEN + f" [ATLAS]: {ack}")
                    if mouth: mouth.speak(ack, blend_config=VOICE_BLEND)
                    
                    # 2. Main Butler translates the conversational command into a hard spec
                    synthesized_task = brain.synthesize_task(user_input)
                    print(Fore.MAGENTA + f" [ORCHESTRATOR] Translated task: '{synthesized_task}'")
                    
                    # 3. Worker synthesizes the XML AND executes the tool natively
                    sys_result = worker.execute_task(synthesized_task)
                    
                    # 4. Modify the input going to the Butler to include the result
                    llm_input = (
                        f"Task requested: '{user_input}'.\n"
                        f"System Execution Result: {sys_result}\n\n"
                        "[CRITICAL INSTRUCTION]: If the Execution Result contains an [ERROR], you MUST inform the user about the exact error and do NOT pretend the task succeeded. If it is [SUCCESS], summarize what was done concisely."
                    )
                # ------------------------------------

                print(Fore.GREEN + " [ATLAS]: ", end="")
                
                # Pass the dynamically modified input and explicit intent
                response_generator = brain.think(llm_input, intent=intent)
                current_sentence = ""
                
                stop_event = threading.Event()
                interrupted = False

                if mode == 1 and ear:
                    ear.set_interrupt_target(stop_event)

                for chunk in response_generator:
                    if mode == 1 and stop_event.is_set():
                        interrupted = True
                        time.sleep(0.1) 
                        print(Fore.RED + "\n [ATLAS] (Interrupted)")
                        break
                    
                    elif mode in [2, 3] and msvcrt and msvcrt.kbhit():
                        key = msvcrt.getch()
                        msvcrt.ungetch(key)
                        stop_event.set()
                        interrupted = True
                        time.sleep(0.1)
                        print(Fore.RED + "\n [ATLAS] (Interrupted)")
                        break
                    
                    if 'message' in chunk:
                        content = chunk['message']['content'].replace('*', '').replace('#', '')
                        print(Fore.GREEN + content, end="", flush=True)
                        
                        if mouth:
                            current_sentence += content
                            if any(p in content for p in ["!", "?", "\n"]) or (content == "." and len(current_sentence.strip().split()[-1]) > 2):
                                clean = current_sentence.strip()
                                if len(clean) > 1:
                                    mouth.speak(current_sentence, blend_config=VOICE_BLEND, stop_event=stop_event)
                                    current_sentence = ""
                                    
                if mouth and current_sentence.strip() and not interrupted:
                    mouth.speak(current_sentence.strip(), blend_config=VOICE_BLEND, stop_event=stop_event)

                if mode == 1 and ear:
                    ear.set_interrupt_target(None)

                if interrupted: time.sleep(0.5)
                print("\n")

        except KeyboardInterrupt: break
        except Exception as e:
            print(f"{Fore.RED}Runtime Error: {e}")
            time.sleep(1)

    # --- SHUTDOWN SEQUENCE ---
    ans.stop()
    if dmn.running: dmn.running = False
    if mode == 1 and ear: ear.stop_listening()
    
    goodbye = brain.generate_goodbye()
    print(Fore.GREEN + f"\n [ATLAS]: {goodbye}")
    if mouth: mouth.speak(goodbye, blend_config=VOICE_BLEND)
        
    print(Fore.YELLOW + " [SYS] Archiving session and consolidating memories...")
    sleep_stats = sleep_system.sleep(conversation=brain.get_conversation_history(), session_start=brain.get_session_start(), consolidate=True)
    
    if sleep_stats["consolidation"]:
        c_stats = sleep_stats["consolidation"]
        if c_stats["consolidated"] > 0:
            print(Fore.MAGENTA + f" [CONSOLIDATOR] Merged {c_stats['consolidated']} related facts into denser memories.")
        else:
            print(Fore.LIGHTBLACK_EX + f" [CONSOLIDATOR] No related facts needed merging (Total facts: {c_stats['remaining']}).")
            
    if mouth:
        try: mouth.close()
        except: pass
    print(Fore.YELLOW + " [SYS] Terminal offline.")

if __name__ == "__main__":
    main()