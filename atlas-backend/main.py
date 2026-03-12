import time
import sys
import threading
import random
from concurrent.futures import ThreadPoolExecutor
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
    from core.brain.self.user_model import UserModel
    from core.brain.cognition.task_queue import TaskQueue
    from core.brain.cognition.executive import Executive
    from core.senses.voice import Mouth
    from core.senses.hearing import Ear
    from core.brain.sensorimotor.motor import MotorCortex
    from core.brain.interface.worker import WorkerNode
    from config import VOICE_BLEND
except ImportError as e:
    print(f"{Fore.RED}Import error: {e}{Style.RESET_ALL}")
    sys.exit(1)

atlas_busy = threading.Lock()
_ACKS = ["Right away, Sir.", "At once, Sir.", "Processing.", "Initiating now, Sir.", "Consider it done, Sir.", "Executing, Sir."]

def select_mode() -> int:
    print(Fore.CYAN + "=" * 50)
    print(Fore.CYAN + "      ATLAS OS - BLACKWELL ARCHITECTURE v3.0")
    print(Fore.CYAN + "=" * 50)
    print(Fore.YELLOW + " 1. Full Voice (VAD + Voice Out)")
    print(Fore.YELLOW + " 2. Hybrid (Text In, Voice Out)")
    print(Fore.YELLOW + " 3. Silent Terminal (Text In, Text Out)")
    print(Fore.CYAN + "=" * 50)
    while True:
        c = input(Fore.BLUE + " Choice (1/2/3): " + Style.RESET_ALL).strip()
        if c in ('1', '2', '3'): return int(c)
        print(Fore.RED + " Invalid.")

def main():
    mode = select_mode()

    try:
        bus = EventBus()
        ans = AutonomicNervousSystem(bus)
        task_queue = TaskQueue(bus)
        ans.set_task_queue(task_queue)
        ans.start()

        habits = HabitLoop(bus)
        router = Router(bus)
        brain = LLMEngine(bus=bus)
        sleep_system = SleepSystem()
        salience = SalienceFilter(bus)
        tom = TheoryOfMind(bus)
        vta = RewardSystem()
        user_model = UserModel()
        executive = Executive(bus)
        motor = MotorCortex()
        worker = WorkerNode()
        worker.warmup()

        ear = None
        mouth = None
        if mode in (1, 2): mouth = Mouth(device="cuda")
        if mode == 1:
            ear = Ear(device="cuda")
            ear.start_listening()

        def handle_proactive(text: str):
            if atlas_busy.acquire(blocking=False):
                try:
                    brain.session_history.append(f"ATLAS: {text}")
                    print(f"\r{Fore.GREEN} [ATLAS] (Proactive): {text}")
                    print(Fore.BLUE + " [USER]: ", end="", flush=True)
                    if mouth:
                        stop_event = threading.Event()
                        if mode == 1 and ear: ear.set_interrupt_target(stop_event)
                        if msvcrt:
                            while msvcrt.kbhit(): msvcrt.getch()
                        t = threading.Thread(target=mouth.speak, args=(text, VOICE_BLEND, stop_event), daemon=True)
                        t.start()
                        while t.is_alive():
                            if mode in (2, 3) and msvcrt and msvcrt.kbhit():
                                msvcrt.getch()
                                stop_event.set()
                                break
                            elif mode == 1 and stop_event.is_set():
                                break
                            time.sleep(0.05)
                finally:
                    if mode == 1 and ear: ear.set_interrupt_target(None)
                    atlas_busy.release()

        def handle_task_due(task: dict):
            text = f"Sir, a scheduled task is due: {task['task'][:80]}"
            handle_proactive(text)
            task_queue.complete(task['id'])

        bus.subscribe("task_due", handle_task_due)
        bus.subscribe("high_salience_event", lambda x: print(Fore.RED + f"\n [AMYGDALA] High urgency: {x}"))
        bus.subscribe("user_state_updated", lambda x: print(Fore.MAGENTA + f" [ToM] Mood={x['mood']} Urgency={x['urgency']}"))

        dmn = DefaultModeNetwork(bus, interoception=brain.interoception, brain=brain)
        dmn.start_wandering(callback=handle_proactive)

        last_intent = "CHAT"
        greeting = brain.generate_greeting()
        print(Fore.GREEN + f"\n [ATLAS]: {greeting}")
        if mouth: mouth.speak(greeting, blend_config=VOICE_BLEND)

    except Exception as e:
        print(Fore.RED + f"Init error: {e}")
        return

    print(Fore.WHITE + "\n [CONTROLS] 'exit' or 'sleep' to shut down.\n")

    with ThreadPoolExecutor(max_workers=3) as pool:
        while True:
            try:
                if mode == 1:
                    user_input = ear.wait_for_input()
                    if not user_input: continue
                    clean = user_input.lower().strip().replace(".", "")
                    if any(w in clean for w in ['exit', 'quit', 'sleep', 'shutdown', 'atlas exit']): break
                else:
                    user_input = input(Fore.BLUE + "\n [USER]: " + Style.RESET_ALL).strip()
                    if user_input.lower() in ['exit', 'quit', 'sleep', '!exit']: break
                    if msvcrt:
                        while msvcrt.kbhit(): msvcrt.getch()

                if not user_input.strip(): continue

                with atlas_busy:
                    if mode == 1: print(Fore.BLUE + f" [USER]: {user_input}")

                    habit_response = habits.check_trigger(user_input)
                    if habit_response:
                        print(Fore.GREEN + f" [ATLAS] (Habit): {habit_response}")
                        if mouth: mouth.speak(habit_response, blend_config=VOICE_BLEND)
                        continue

                    intent_future = pool.submit(router.route, user_input)
                    salience_future = pool.submit(salience.score_importance, user_input)
                    tom_future = pool.submit(tom.analyze_state, user_input)

                    intent = intent_future.result()
                    score = salience_future.result()
                    user_state = tom_future.result()

                    print(Fore.YELLOW + f" [ROUTER] {intent} | [SALIENCE] {score}/10 | [ToM] {user_state['mood']}")

                    pool.submit(user_model.update_from_interaction, user_input, user_state['mood'], intent)

                    if user_state.get('mood') == 'positive':
                        vta.apply_feedback(last_intent, positive=True)
                    elif user_state.get('mood') == 'frustrated':
                        vta.apply_feedback(last_intent, positive=False)
                    last_intent = intent

                    sleep_system.tick(brain.session_history)

                    llm_input = user_input

                    if intent == "COMMAND":
                        ack = random.choice(_ACKS)
                        print(Fore.GREEN + f" [ATLAS]: {ack}")
                        if mouth: mouth.speak(ack, blend_config=VOICE_BLEND)

                        synthesized = brain.synthesize_task(user_input)
                        print(Fore.MAGENTA + f" [ORCHESTRATOR] Task: '{synthesized[:100]}'")

                        if synthesized.startswith("[MULTI_STEP]"):
                            raw_steps = synthesized.replace("[MULTI_STEP]", "").strip()
                            steps = [s.strip() for s in raw_steps.split("|") if s.strip()]
                            if len(steps) < 2:
                                steps = executive.plan_execution(user_input)
                            print(Fore.MAGENTA + f" [EXECUTIVE] {len(steps)}-step plan: {steps}")
                            sys_result = worker.execute_plan(steps)
                        else:
                            sys_result = worker.execute_task(synthesized)

                        llm_input = (
                            f"Task requested: '{user_input}'.\n"
                            f"Execution Result: {sys_result}\n\n"
                            "[INSTRUCTION]: If [ERROR], inform the user of the exact error. If [SUCCESS], summarize concisely."
                        )

                    print(Fore.GREEN + " [ATLAS]: ", end="")
                    response_gen = brain.think(llm_input, intent=intent, user_state=user_state, task_queue=task_queue)
                    current_sentence = ""
                    stop_event = threading.Event()
                    interrupted = False

                    if mode == 1 and ear: ear.set_interrupt_target(stop_event)

                    for chunk in response_gen:
                        if stop_event.is_set():
                            interrupted = True
                            print(Fore.RED + "\n [ATLAS] (Interrupted)")
                            break
                        elif mode in (2, 3) and msvcrt and msvcrt.kbhit():
                            msvcrt.getch()
                            stop_event.set()
                            interrupted = True
                            print(Fore.RED + "\n [ATLAS] (Interrupted)")
                            break
                        if 'message' in chunk:
                            content = chunk['message']['content'].replace('*', '').replace('#', '')
                            print(Fore.GREEN + content, end="", flush=True)
                            if mouth:
                                current_sentence += content
                                if any(p in content for p in ["!", "?", "\n"]) or (content == "." and len(current_sentence.strip().split()[-1:][0] if current_sentence.strip().split() else "") > 2):
                                    if len(current_sentence.strip()) > 1:
                                        mouth.speak(current_sentence, blend_config=VOICE_BLEND, stop_event=stop_event)
                                        current_sentence = ""

                    if mouth and current_sentence.strip() and not interrupted:
                        mouth.speak(current_sentence.strip(), blend_config=VOICE_BLEND, stop_event=stop_event)

                    if mode == 1 and ear: ear.set_interrupt_target(None)
                    print("\n")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(Fore.RED + f"Runtime error: {e}")
                time.sleep(0.5)

    ans.stop()
    if hasattr(dmn, 'running'): dmn.running = False
    if mode == 1 and ear: ear.stop_listening()

    goodbye = brain.generate_goodbye()
    print(Fore.GREEN + f"\n [ATLAS]: {goodbye}")
    if mouth: mouth.speak(goodbye, blend_config=VOICE_BLEND)

    print(Fore.YELLOW + " [SYS] Archiving session...")
    stats = sleep_system.sleep(brain.get_conversation_history(), brain.get_session_start(), consolidate=True)
    if stats.get("consolidation") and stats["consolidation"].get("consolidated", 0) > 0:
        print(Fore.MAGENTA + f" [CONSOLIDATOR] Merged {stats['consolidation']['consolidated']} facts.")

    if mouth:
        try: mouth.close()
        except: pass
    print(Fore.YELLOW + " [SYS] Terminal offline.")

if __name__ == "__main__":
    main()