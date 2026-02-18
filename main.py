import time
import os
import sys
from colorama import Fore, Style, init

init(autoreset=True)

try:
    from core.brain.llm import LLMEngine
    from core.senses.voice import Mouth
    from core.senses.hearing import Ear
except ImportError as e:
    print(f"{Fore.RED}Error importing modules: {e}{Style.RESET_ALL}")
    sys.exit(1)

def main():
    print(Fore.CYAN + "="*50)
    print(Fore.CYAN + "          ATLAS OS - BLACKWELL ARCHITECTURE jv2.0")
    print(Fore.CYAN + "="*50)

    VOICE_BLEND = {'bm_george': 0.7, 'bm_fable': 0.3}
    
    try:
        print(Fore.YELLOW + " [SYSTEM] Initializing Brain (Llama 3.1)...")
        brain = LLMEngine()
        
        print(Fore.YELLOW + " [SYSTEM] Initializing Senses (Whisper CPU)...")
        ear = Ear(device="cuda") 
        
        print(Fore.YELLOW + " [SYSTEM] Initializing Vocal Cords (Hybrid British)...")
        mouth = Mouth(device="cuda")

        print(Fore.GREEN + "\n [ONLINE] All systems operational.")
        mouth.speak("Systems synchronized. I am Atlas. How may I assist you today, sir?", 
                    blend_config=VOICE_BLEND)
        
    except Exception as e:
        print(f"{Fore.RED}An error occurred during initialization: {e}")
        return
        
    print(Fore.WHITE + "\n [CONTROLS] Hold SPACEBAR to speak. Press ESC to shutdown.\n")

    while True:
        try:
            user_input = ear.listen()

            if user_input is None:
                break

            if not user_input.strip():
                continue

            print(Fore.BLUE + f"\n [USER]: {user_input}")
            print(Fore.YELLOW + " [SYSTEM] Processing input...")

            response_generator = brain.think(user_input)
            
            full_response = ""
            current_sentence = ""

            for chunk in response_generator:
                if 'message' not in chunk:
                    continue

                content = chunk['message']['content']
                full_response += content
                current_sentence += content

                if content in [".", "!", "?", "\n"]:
                    clean_sentence = current_sentence.strip()
                    if len(clean_sentence) > 1:
                        mouth.speak(current_sentence, blend_config=VOICE_BLEND)
                        current_sentence = ""
            
            if current_sentence.strip():
                mouth.speak(current_sentence.strip(), blend_config=VOICE_BLEND)

            print("\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Fore.RED}An error occurred during runtime: {e}")
            time.sleep(1)
            continue

    print(Fore.CYAN + "\n" + "="*50)
    print(Fore.CYAN + "[SLEEP] ATLAS entering sleep cycle...")
    print(Fore.CYAN + "\n" + "="*50)

    mouth.speak("Initializing sleep cycle, Sir. Archiving our session.", blend_config=VOICE_BLEND)

    conversation = brain.get_conversation_history()
    session_start = brain.get_session_start()

    if len(conversation) >= 4:
        brain.archivist.archive_session(conversation, session_start)
    else:
        print(Fore.YELLOW + " [SLEEP] Session too short to archive")

    print(Fore.GREEN + "\n" + "="*50)
    print(Fore.GREEN + " [SLEEP] Sleep cycle complete. Sweet dreams, Sir.")
    print(Fore.GREEN + "\n" + "="*50)
    print(Fore.YELLOW + " [SYSTEM] Shutting down. Sleep well, sir...")

if __name__ == "__main__":
    main()