import time
import sys
from colorama import Fore, Style, init

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
    from core.senses.voice import Mouth  # <-- Added the Vocal Cords
except ImportError as e:
    print(f"{Fore.RED}Error importing modules: {e}{Style.RESET_ALL}")
    sys.exit(1)


def main():
    print(Fore.CYAN + "="*50)
    print(Fore.CYAN + "   ATLAS OS - HYBRID TERMINAL (TEXT IN, VOICE OUT)")
    print(Fore.CYAN + "="*50)
    
    VOICE_BLEND = {'bm_george': 0.7, 'bm_fable': 0.3}
    
    try:
        print(Fore.YELLOW + " [SYSTEM] Initializing Brain & Subsystems...")
        bus = EventBus()
        ans = AutonomicNervousSystem(bus)
        ans.start()
        
        # Subsystems
        habits = HabitLoop(bus)
        router = Router(bus)
        brain = LLMEngine()
        sleep_system = SleepSystem()
        salience = SalienceFilter(bus)
        tom = TheoryOfMind(bus)
        vta = RewardSystem()           # <-- NEW: The Reward Center
        
        last_intent = "CHAT"
        

        print(Fore.YELLOW + " [SYSTEM] Initializing Vocal Cords (Kokoro)...")
        mouth = Mouth(device="cuda")

        # Bus Subscriptions (Visible background thoughts)
        bus.subscribe("high_salience_event", lambda x: print(Fore.RED + f"\n [AMYGDALA] High Urgency Detected: {x}"))
        bus.subscribe("user_state_updated", lambda x: print(Fore.MAGENTA + f" [THEORY OF MIND] User State: Mood={x['mood']}, Urgency={x['urgency']}"))

        # Dynamic Greeting
        greeting = brain.generate_greeting()
        print(Fore.GREEN + f"\n [ATLAS]: {greeting}\n")
        mouth.speak(greeting, blend_config=VOICE_BLEND)
        
    except Exception as e:
        print(f"{Fore.RED}An error occurred during initialization: {e}")
        return
        
    print(Fore.WHITE + " [CONTROLS] Type your message and press ENTER. Type 'exit' or 'sleep' to shutdown.\n")

    while True:
        try:
            user_input = input(Fore.BLUE + " [USER]: " + Style.RESET_ALL).strip()

            if user_input.lower() in ['exit', 'quit', 'sleep', '!exit']:
                break
            if not user_input:
                continue

            # 1. Check Habits (Instantly spoken)
            habit_response = habits.check_trigger(user_input)
            if habit_response:
                print(Fore.GREEN + f" [ATLAS] (Habit): {habit_response}\n")
                mouth.speak(habit_response, blend_config=VOICE_BLEND)
                continue

            # 2. Parallel Processing
            intent = router.route(user_input)
            print(Fore.YELLOW + f" [ROUTER] Intent: {intent}")
            
            salience.score_importance(user_input)
            user_state = tom.analyze_state(user_input) # We capture the state now

            # --- THE VTA REWARD LOOP ---
            # If you are happy, reward the LAST thing ATLAS did.
            if user_state.get('mood') == 'positive':
                vta.apply_feedback(last_intent, positive=True)
                print(Fore.CYAN + f" [VTA] Positive reinforcement applied to pathway: {last_intent}")
            
            # If you are frustrated, penalize the LAST thing ATLAS did.
            elif user_state.get('mood') == 'frustrated':
                vta.apply_feedback(last_intent, positive=False)
                print(Fore.CYAN + f" [VTA] Negative reinforcement applied to pathway: {last_intent}")

            # Update the tracker for the next turn
            last_intent = intent

            # 3. LLM Generation & Speech Streaming
            print(Fore.GREEN + " [ATLAS]: ", end="")
            response_generator = brain.think(user_input)
            
            current_sentence = ""

            for chunk in response_generator:
                if 'message' in chunk:
                    content = chunk['message']['content']
                    
                    # 1. REMOVE MARKDOWN ASTERISKS BEFORE PRINTING/SPEAKING
                    content = content.replace('*', '').replace('#', '')
                    
                    print(Fore.GREEN + content, end="", flush=True)
                    
                    current_sentence += content

                    # 2. SMARTER SENTENCE CHUNKING (Ignore periods after short numbers)
                    if any(p in content for p in ["!", "?", "\n"]) or (content == "." and len(current_sentence.strip().split()[-1]) > 2):
                        clean_sentence = current_sentence.strip()
                        if len(clean_sentence) > 1:
                            mouth.speak(current_sentence, blend_config=VOICE_BLEND)
                            current_sentence = ""
            
            # Flush and speak any remaining text that didn't end in punctuation
            if current_sentence.strip():
                mouth.speak(current_sentence.strip(), blend_config=VOICE_BLEND)

            print("\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Fore.RED}Runtime Error: {e}")
            time.sleep(1)
            continue

    ans.stop()
    
    # Dynamic Goodbye spoken aloud
    goodbye = brain.generate_goodbye()
    print(Fore.GREEN + f"\n [ATLAS]: {goodbye}")
    mouth.speak(goodbye, blend_config=VOICE_BLEND)
    
    print(Fore.YELLOW + " [SYS] Archiving session...")
    
    sleep_system.sleep(
        conversation=brain.get_conversation_history(),
        session_start=brain.get_session_start(),
        consolidate=True
    )
    
    try:
        mouth.close()
    except:
        pass
        
    print(Fore.YELLOW + " [SYS] Terminal offline.")

if __name__ == "__main__":
    main()