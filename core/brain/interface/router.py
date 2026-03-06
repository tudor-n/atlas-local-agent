import re
from colorama import Fore
import ollama
from config import BUTLER_MODEL

_ACTION = frozenset([
    "write","make","create","build","erase","delete","remove","generate",
    "run","execute","install","compile","deploy","launch","open","start",
    "stop","kill","restart","patch","fix","update","upgrade","refactor",
    "rename","move","copy","search","fetch","find","get","calculate",
    "compute","remind","schedule","add","show","list","read","check"
])
_TARGET = frozenset([
    "project","c++","cpp","script","file","directory","folder","python",
    "code","architect","worker","bash","terminal","command","repo",
    "repository","git","docker","server","api","module","class","function",
    "method","library","package","test","program","application","app",
    "database","db","sql","html","css","js","javascript","typescript",
    "rust","go","java","kotlin","swift","web","url","website","page",
    "sandbox","task","reminder","log","logs","repl","version","sum","primes"
])
_MEMORY_PHRASES = [
    "do you remember","can you recall","what do you know about me",
    "did i tell you","what did we","last time","last session","previously",
    "what projects am i","what do you know","who am i","my name",
    "what language do i","my editor","my preference","what was the first"
]
_COMMAND_PHRASES = [
    "search the web","search for","fetch the","read the file","run the",
    "execute the","create a file","write a file","build a","make a",
    "use the architect","use the worker","use the cloud","use the local",
    "remind me","schedule a","list all files","list the files",
    "use the python repl","calculate using","patch the","fix the",
    "install the","delete the file","create a folder","create the folder",
    "read the url","fetch the url","fetch the content"
]

class Router:
    def __init__(self, bus, model_name=BUTLER_MODEL):
        self.bus = bus
        self.model = model_name
        self.valid_intents = {"CHAT", "COMMAND", "MEMORY", "QUERY", "IMAGINE"}

    def route(self, user_input: str) -> str:
        lower = user_input.lower()
        tokens = set(re.findall(r'\b\w+\b', lower))

        for phrase in _COMMAND_PHRASES:
            if phrase in lower:
                self.bus.publish("intent_COMMAND", user_input)
                return "COMMAND"

        if (_ACTION & tokens) and (_TARGET & tokens):
            self.bus.publish("intent_COMMAND", user_input)
            return "COMMAND"

        for phrase in _MEMORY_PHRASES:
            if phrase in lower:
                self.bus.publish("intent_MEMORY", user_input)
                return "MEMORY"

        imagine_words = frozenset(["imagine","what if","suppose","hypothetically","brainstorm","could we","would happen"])
        if imagine_words & tokens:
            self.bus.publish("intent_IMAGINE", user_input)
            return "IMAGINE"

        words = lower.split()
        if len(words) <= 8:
            intent = "CHAT"
            self.bus.publish(f"intent_{intent}", user_input)
            return intent

        prompt = (
            "Classify into ONE word: CHAT, COMMAND, MEMORY, QUERY, IMAGINE.\n"
            "COMMAND = any task involving files, code, tools, web, terminal, scheduling, calculations.\n"
            "MEMORY = asking what you know/remember about the user personally.\n"
            "QUERY = factual question about the world.\n"
            "IMAGINE = hypothetical/brainstorming.\n"
            "CHAT = casual conversation only.\n"
            "When in doubt between COMMAND and QUERY, choose COMMAND.\n"
            f"Input: '{user_input}'\nIntent:"
        )
        try:
            response = ollama.generate(
                model=self.model, prompt=prompt,
                options={"temperature": 0.0, "num_predict": 5}
            )['response'].strip().upper()
            intent = ''.join(c for c in response if c.isalpha())[:10]
            if intent not in self.valid_intents:
                intent = "CHAT"
        except:
            intent = "CHAT"

        self.bus.publish(f"intent_{intent}", user_input)
        return intent