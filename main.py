import time
import sys
import threading
from colorama import Fore, Style, init

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
except ImportError as e:
    print(f"{Fore.RED}Error importing modules: {e}{Style.RESET_ALL}")
    sys.exit(1)

# --- GLOBAL LOCK ---
# This prevents reactive and proactive thoughts from talking over each other
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
        brain = LLMEngine()
        sleep_system = SleepSystem()
        salience = SalienceFilter(bus)
        tom = TheoryOfMind(bus)
        vta = RewardSystem()
        
        ear = None
        mouth = None
        if mode in [1, 2]: mouth = Mouth(device="cuda")
        
        # Initialize and START the continuous ear for Mode 1
        if mode == 1: 
            ear = Ear(device="cuda")
            ear.start_listening()

        # --- THE PROACTIVE HANDLER ---
        def handle_proactive(text):
            if atlas_busy.acquire(blocking=False):
                try:
                    if hasattr(brain, 'history'):
                        brain.history.append({"role": "assistant", "content": text})
                    elif hasattr(brain, 'messages'):
                        brain.messages.append({"role": "assistant", "content": text})
                    
                    # Cleanly overwrite the current input line, print the thought, then restore the input prompt
                    print(f"\r{Fore.GREEN} [ATLAS] (Proactive): {text}")
                    print(Fore.BLUE + " [USER]: ", end="", flush=True)

                    if mouth:
                        stop_event = threading.Event()
                        
                        # Hand the kill-switch to the Ear if in Voice Mode!
                        if mode == 1 and ear:
                            ear.set_interrupt_target(stop_event)
                        
                        # Flush the keyboard buffer BEFORE we start listening for text interruptions
                        if msvcrt:
                            while msvcrt.kbhit():
                                msvcrt.getch()
                                
                        speak_thread = threading.Thread(target=mouth.speak, args=(text, VOICE_BLEND, stop_event))
                        speak_thread.start()
                        
                        while speak_thread.is_alive():
                            # Text Mode Interruption
                            if mode in [2, 3] and msvcrt and msvcrt.kbhit():
                                key = msvcrt.getch()
                                msvcrt.ungetch(key)
                                stop_event.set()
                                import random
                                ack = random.choice(["I'm sorry, Sir. Go ahead.", "You were saying?", "...Yes, Sir?"])
                                print(f"\r{Fore.RED} [ATLAS] (Interrupted): {ack}")
                                print(Fore.BLUE + " [USER]: ", end="", flush=True)
                                break
                            
                            # Voice Mode Interruption (Tripped automatically by VAD hearing speech)
                            elif mode == 1 and stop_event.is_set():
                                import random
                                ack = random.choice(["I'm sorry, Sir. Go ahead.", "You were saying?", "...Yes, Sir?"])
                                print(f"\r{Fore.RED} [ATLAS] (Interrupted): {ack}")
                                print(Fore.BLUE + " [USER]: ", end="", flush=True)
                                break
                                
                            time.sleep(0.05)
                finally:
                    # Remove the kill-switch target so the Ear doesn't accidentally trigger later
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

    # Display correct controls
    if mode == 1:
        print(Fore.WHITE + "\n [CONTROLS] Speak naturally to interact. Say 'exit' or 'sleep' to shutdown.\n")
    else:
        print(Fore.WHITE + "\n [CONTROLS] Type your message and press ENTER. Type 'exit' or 'sleep' to shutdown.\n")

    # --- MAIN EVENT LOOP ---
    while True:
        try:
            # 1. Gather Input
            if mode == 1:
                user_input = ear.wait_for_input() # VAD + Whisper handles this now!
                if not user_input: continue
                
                # Check for voice exit commands
                clean_input = user_input.lower().strip().replace(".", "")
                exit_words = ['exit', 'quit', 'sleep', 'shutdown', 'outflows', 'atlas exit']
                if any(word in clean_input for word in exit_words): 
                    break
            else:
                user_input = input(Fore.BLUE + "\n [USER]: " + Style.RESET_ALL).strip()
                if user_input.lower() in ['exit', 'quit', 'sleep', '!exit']: break
                    
            if not user_input or not user_input.strip(): continue

            # Acquire lock so DMN doesn't fire while we are actively interacting
            with atlas_busy:
                if mode == 1: print(Fore.BLUE + f" [USER]: {user_input}")

                habit_response = habits.check_trigger(user_input)
                if habit_response:
                    print(Fore.GREEN + f" [ATLAS] (Habit): {habit_response}")
                    if mouth: mouth.speak(habit_response, blend_config=VOICE_BLEND)
                    continue

                intent = router.route(user_input)
                salience.score_importance(user_input)
                user_state = tom.analyze_state(user_input)

                if user_state.get('mood') == 'positive': vta.apply_feedback(last_intent, positive=True)
                elif user_state.get('mood') == 'frustrated': vta.apply_feedback(last_intent, positive=False)
                last_intent = intent

                print(Fore.GREEN + " [ATLAS]: ", end="")
                response_generator = brain.think(user_input)
                current_sentence = ""
                
                stop_event = threading.Event()
                interrupted = False

                # Hand the kill-switch to the Ear for reactive responses
                if mode == 1 and ear:
                    ear.set_interrupt_target(stop_event)

                for chunk in response_generator:
                    # Voice Mode Interruption (VAD sets stop_event automatically)
                    if mode == 1 and stop_event.is_set():
                        interrupted = True
                        time.sleep(0.1) # Let audio buffer clear
                        import random
                        ack = random.choice(["Yes, Sir?", "I'm listening.", "Proceed, Sir."])
                        print(Fore.RED + f"\n [ATLAS] (Interrupted): {ack}")
                        if mouth: mouth.speak(ack, blend_config=VOICE_BLEND)
                        break
                    
                    # Text Mode Interruption
                    elif mode in [2, 3] and msvcrt and msvcrt.kbhit():
                        key = msvcrt.getch()
                        msvcrt.ungetch(key)
                        stop_event.set()
                        interrupted = True
                        time.sleep(0.1)
                        import random
                        ack = random.choice(["Yes, Sir?", "I'm listening.", "Proceed, Sir."])
                        print(Fore.RED + f"\n [ATLAS] (Interrupted): {ack}")
                        if mouth: mouth.speak(ack, blend_config=VOICE_BLEND)
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

                # Reset Ear target at end of interaction
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
        
    print(Fore.YELLOW + " [SYS] Archiving session...")
    sleep_system.sleep(conversation=brain.get_conversation_history(), session_start=brain.get_session_start(), consolidate=True)
    if mouth:
        try: mouth.close()
        except: pass
    print(Fore.YELLOW + " [SYS] Terminal offline.")

if __name__ == "__main__":
    main()