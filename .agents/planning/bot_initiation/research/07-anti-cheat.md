# Anti-Cheat Considerations

Research on Battle.net anti-cheat and safe practices for CV-based bots.

---

## Battle.net Anti-Cheat Overview

Blizzard uses **Warden** as their anti-cheat system across games including D2R.

### What Warden Detects

| Detection Method | Risk Level | Notes |
|-----------------|------------|-------|
| Memory reading/writing | **High** | Direct memory access triggers detection |
| Packet manipulation | **High** | Network packet tampering is detected |
| Known bot signatures | **High** | Hash/signature of known bot executables |
| DLL injection | **High** | Injecting code into game process |
| Process hooking | **High** | Hooking game functions |
| Suspicious mouse patterns | **Medium** | Perfectly linear or instant movements |
| Unusual play patterns | **Medium** | 24/7 play, identical run patterns |
| Screen capture | **Low** | External screenshots generally safe |
| Input simulation | **Low** | SendInput/DirectInput less detectable |

### Why Screen-Based Bots Are Safer

1. **No memory access** - Warden scans for memory read/write
2. **No process injection** - Bot runs as separate process
3. **No known signatures** - Custom Python scripts aren't in signature DB
4. **External operation** - Bot doesn't touch game files or process

---

## Safe Practices

### Input Simulation
- Use `pydirectinput` (DirectInput) not `pyautogui` (VK codes)
- Add human-like mouse movement (WindMouse algorithm)
- Vary timing between actions (±10-20%)
- Avoid perfectly timed sequences

### Play Patterns
- **Take breaks** - Don't run 24/7 continuously
- **Vary activities** - Mix different runs
- **Simulate human behavior** - Occasional pauses, inventory checks
- **Reasonable hours** - Consider simulating sleep schedule

### Detection Timing Example
```python
import random
import time

class HumanizedBot:
    def __init__(self):
        self.runs_completed = 0
        self.session_start = time.time()

    def should_take_break(self):
        # Break every 30-60 runs
        if self.runs_completed > random.randint(30, 60):
            self.runs_completed = 0
            return True

        # Break after 2-4 hours
        session_length = time.time() - self.session_start
        if session_length > random.uniform(2, 4) * 3600:
            self.session_start = time.time()
            return True

        return False

    def take_break(self):
        # Break for 5-15 minutes
        break_time = random.uniform(5, 15) * 60
        time.sleep(break_time)
```

---

## Offline vs Online Risk

| Mode | Detection Risk | Notes |
|------|---------------|-------|
| **Offline (Single Player)** | None | No server connection, no Warden |
| **Online (Battle.net)** | Present | Warden active, ban possible |

### Recommendation
1. **Develop offline** - Test all functionality in single player
2. **Implement safety features** before going online
3. **Use on alternate accounts** if testing online
4. **Accept risk** - Online botting always carries ban risk

---

## Red Flags to Avoid

### Behavioral Red Flags
- Running 24/7 without breaks
- Identical run patterns every time
- Perfect timing on every action
- Instant mouse teleportation
- Inhuman reaction times

### Technical Red Flags
- Memory scanning/reading
- DLL injection
- Process attachment
- Network packet manipulation
- Known bot executable hashes

---

## Risk Mitigation Checklist

```markdown
[ ] Bot runs as separate process (no injection)
[ ] No memory reading/writing
[ ] No packet manipulation
[ ] Human-like mouse movement implemented
[ ] Timing variation on all actions
[ ] Break system implemented
[ ] Run variation (not identical every time)
[ ] Tested extensively offline first
[ ] Using account you're willing to lose
```

---

## Legal Considerations

- Botting violates Blizzard's Terms of Service
- Can result in permanent account ban
- This is for **educational purposes** and **offline/single-player use**
- Online use is at your own risk

---

## Summary

A screen-based, computer vision bot using:
- External screen capture (mss)
- Template matching (OpenCV)
- DirectInput simulation (pydirectinput)
- Human-like timing and movement

Is among the **lowest risk** bot architectures, but:
- No bot is 100% undetectable
- Online botting always carries risk
- Offline testing is completely safe

---

## References
- [Warden (Anti-Cheat) Wiki](https://wowpedia.fandom.com/wiki/Warden)
- [Battle.net Terms of Service](https://www.blizzard.com/en-us/legal)
