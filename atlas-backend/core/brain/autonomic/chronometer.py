from datetime import datetime, timedelta
class Chronometer:
    def __init__(self):
        self.boot_time=datetime.now()

    def now(self) -> datetime:
        return datetime.now()
    
    def today(self) -> str:
        return self.now().strftime("%Y-%m-%d")
    
    def timestamp(self) -> str:
        return self.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def uptime(self)->str:
        delta=self.now()-self.boot_time
        hours, remainder = divmod(int(delta.total_seconds()),3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} {minutes}m {seconds}s"
    
    def get_time_context(self) -> str:
        now=self.now()
        context = f"""[CURRENT TIME AWARENESS]
- Date: {now.strftime("%A, %B %d, %Y")}
- Time: {now.strftime("%I:%M %p")}
- Session started: {self.boot_time.strftime("%I:%M %p")}
- Uptime: {self.uptime()}"""
        return context
    
    def relative_date(self, date: datetime) -> str:
        today=self.now().date()
        target = date.date()
        delta = (today-target).days

        if delta==0:
            return "today"
        elif delta==1:
            return "yesterday"
        elif delta < 7:
            return f"{delta} days ago"
        elif delta < 14:
            return f"last {date.strftime('%A')}"
        else:
            return f"on {date.strftime('%B %d')}"
        
    def parse_relative_time(self, phrase: str) -> datetime:
        phrase = phrase.lower().strip()
        now = self.now()
        if "today" in phrase:
            return now
        elif "yesterday" in phrase:
            return now - timedelta(days=1)
        elif "last week" in phrase:
            return now - timedelta(weeks=1)
        elif "days ago" in phrase:
            try:
                days = int(''.join(filter(str.isdigit, phrase)))
                return now - timedelta(days=days)
            except:
                return now
        else:
            return now

if __name__ == "__main__":
    clock = Chronometer()
    
    print("\n" + "="*50)
    print(" CHRONOMETER TEST")
    print("="*50)
    
    print(f"\n Current timestamp: {clock.timestamp()}")
    print(f" Today: {clock.today()}")
    print(f" Uptime: {clock.uptime()}")
    
    print("\n Time context for LLM:")
    print(clock.get_time_context())
    
    print("\n Relative dates:")
    print(f" Now → {clock.relative_date(clock.now())}")
    print(f" Yesterday → {clock.relative_date(clock.now() - timedelta(days=1))}")
    print(f" 5 days ago → {clock.relative_date(clock.now() - timedelta(days=5))}")