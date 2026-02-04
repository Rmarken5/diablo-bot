# Input Simulation

Research on keyboard and mouse input for game automation with detection avoidance.

---

## Core Libraries

| Library | Purpose | Detection Risk |
|---------|---------|----------------|
| **pydirectinput** | DirectInput (works with games) | Lower |
| **pyautogui** | Virtual key codes | Higher |
| **win32api** | Low-level Windows API | Medium |

**Recommendation:** Use `pydirectinput` for game input - it uses DirectInput scan codes and SendInput(), which work with DirectX games.

---

## Basic Input with PyDirectInput

```python
import pydirectinput
import time

# Disable fail-safe (mouse to corner stops script)
pydirectinput.FAILSAFE = False

class GameInput:
    def __init__(self):
        self.key_delay = 0.05  # 50ms between key actions

    def press_key(self, key):
        """Press and release a key."""
        pydirectinput.press(key)

    def hold_key(self, key, duration):
        """Hold key for duration."""
        pydirectinput.keyDown(key)
        time.sleep(duration)
        pydirectinput.keyUp(key)

    def click(self, x, y, button='left'):
        """Click at position."""
        pydirectinput.click(x, y, button=button)

    def move_mouse(self, x, y):
        """Move mouse to position."""
        pydirectinput.moveTo(x, y)
```

---

## Human-Like Mouse Movement

### The Problem
- Instant mouse movement is easily detected
- Linear interpolation is also suspicious
- Human movement has natural variation and curves

### Solution: WindMouse Algorithm

WindMouse simulates physics-based mouse movement using:
- **Gravity:** Pulls cursor toward destination
- **Wind:** Random fluctuating force for natural variation
- **Inertia:** Momentum-based movement

```python
import math
import random
import pydirectinput
import time

def wind_mouse(start_x, start_y, dest_x, dest_y,
               G_0=9, W_0=3, M_0=15, D_0=12):
    """
    WindMouse algorithm for human-like mouse movement.

    Parameters:
    - G_0: Gravity (pull toward destination)
    - W_0: Wind magnitude (randomness)
    - M_0: Maximum velocity
    - D_0: Distance threshold for wind behavior change
    """
    sqrt3 = math.sqrt(3)
    sqrt5 = math.sqrt(5)

    current_x, current_y = start_x, start_y
    v_x, v_y = 0, 0
    W_x, W_y = 0, 0

    while True:
        dist = math.hypot(dest_x - current_x, dest_y - current_y)

        if dist < 1:
            break

        # Wind force changes based on distance
        if dist >= D_0:
            W_x = W_x / sqrt3 + (2 * random.random() - 1) * W_0 / sqrt5
            W_y = W_y / sqrt3 + (2 * random.random() - 1) * W_0 / sqrt5
        else:
            W_x /= sqrt3
            W_y /= sqrt3

        # Gravity pulls toward destination
        G_x = G_0 * (dest_x - current_x) / dist
        G_y = G_0 * (dest_y - current_y) / dist

        # Update velocity
        v_x += W_x + G_x
        v_y += W_y + G_y

        # Limit velocity
        v_mag = math.hypot(v_x, v_y)
        if v_mag > M_0:
            v_clamp = M_0 / 2 + random.random() * M_0 / 2
            v_x = v_x / v_mag * v_clamp
            v_y = v_y / v_mag * v_clamp

        # Update position
        current_x += v_x
        current_y += v_y

        # Move mouse
        pydirectinput.moveTo(int(current_x), int(current_y))

        # Small delay for natural speed
        time.sleep(random.uniform(0.001, 0.003))

    # Final move to exact destination
    pydirectinput.moveTo(dest_x, dest_y)


def human_click(x, y, button='left'):
    """Click with human-like mouse movement."""
    current_x, current_y = pydirectinput.position()
    wind_mouse(current_x, current_y, x, y)
    time.sleep(random.uniform(0.05, 0.15))
    pydirectinput.click(button=button)
```

### Alternative: HumanCursor Library

```python
from humancursor import SystemCursor

cursor = SystemCursor()
cursor.move_to([x, y])  # Human-like movement
cursor.click()
```

---

## Timing Variation

### Key Presses
```python
import random

def human_key_press(key):
    """Press key with human-like timing."""
    # Random delay before pressing
    time.sleep(random.uniform(0.02, 0.08))

    pydirectinput.keyDown(key)

    # Random hold duration
    time.sleep(random.uniform(0.03, 0.12))

    pydirectinput.keyUp(key)

    # Random delay after releasing
    time.sleep(random.uniform(0.02, 0.06))
```

### Action Sequences
```python
def human_action_delay():
    """Add human-like delay between actions."""
    # Normal distribution centered around 100ms
    delay = random.gauss(0.1, 0.03)
    delay = max(0.05, min(0.2, delay))  # Clamp to reasonable range
    time.sleep(delay)
```

---

## Skill Casting

### Basic Skill Use
```python
class SkillCaster:
    def __init__(self):
        self.skill_keys = {
            "teleport": "w",
            "blizzard": "q",
            "glacial_spike": "e",
            "static_field": "r",
            "frozen_armor": "a",
        }
        self.last_cast_time = {}

    def cast_skill(self, skill_name, target_x=None, target_y=None):
        """Cast a skill, optionally at a target location."""
        key = self.skill_keys.get(skill_name)
        if not key:
            return False

        # Press skill key
        human_key_press(key)

        # If targeted skill, click at location
        if target_x and target_y:
            human_click(target_x, target_y)
        else:
            # For self-cast, right-click
            human_click(*pydirectinput.position(), button='right')

        self.last_cast_time[skill_name] = time.time()
        return True

    def cast_at_cursor(self, skill_name):
        """Cast skill at current cursor position."""
        key = self.skill_keys.get(skill_name)
        if key:
            human_key_press(key)
            pydirectinput.click(button='right')
```

### FCR-Aware Casting
```python
class FCRAwareCaster:
    # Frames per cast based on FCR%
    FCR_BREAKPOINTS = {
        0: 13,
        9: 12,
        20: 11,
        37: 10,
        63: 9,
        105: 8,
        200: 7,
    }

    def __init__(self, fcr_percent):
        self.frames_per_cast = self._get_frames(fcr_percent)
        self.cast_delay = self.frames_per_cast / 25  # 25 FPS

    def _get_frames(self, fcr):
        frames = 13  # Default
        for threshold, f in sorted(self.FCR_BREAKPOINTS.items()):
            if fcr >= threshold:
                frames = f
        return frames

    def cast_teleport(self, x, y):
        """Cast teleport respecting FCR."""
        human_click(x, y, button='right')
        time.sleep(self.cast_delay)
```

---

## Inventory Interaction

```python
class InventoryManager:
    # Grid positions for 1920x1080
    INVENTORY_TOP_LEFT = (1280, 380)
    SLOT_SIZE = 29
    COLS = 10
    ROWS = 4

    def get_slot_position(self, row, col):
        """Get screen position of inventory slot."""
        x = self.INVENTORY_TOP_LEFT[0] + col * self.SLOT_SIZE + self.SLOT_SIZE // 2
        y = self.INVENTORY_TOP_LEFT[1] + row * self.SLOT_SIZE + self.SLOT_SIZE // 2
        return (x, y)

    def click_slot(self, row, col):
        """Click an inventory slot."""
        x, y = self.get_slot_position(row, col)
        human_click(x, y)

    def pickup_item(self, item_x, item_y):
        """Pick up item from ground."""
        human_click(item_x, item_y)

    def use_potion(self, belt_slot):
        """Use potion from belt (1-4)."""
        human_key_press(str(belt_slot))
```

---

## Town Interaction

```python
class TownInteraction:
    def __init__(self):
        self.npc_templates = {
            "akara": cv2.imread("assets/npcs/akara.png"),
            "charsi": cv2.imread("assets/npcs/charsi.png"),
            "cain": cv2.imread("assets/npcs/cain.png"),
            "stash": cv2.imread("assets/stash.png"),
        }

    def interact_with_npc(self, npc_name, screen):
        """Find and interact with NPC."""
        template = self.npc_templates.get(npc_name)
        if not template:
            return False

        match = find_template(screen, template)
        if match:
            human_click(match[0], match[1])
            return True
        return False

    def use_waypoint(self, destination_act, destination_wp):
        """Use waypoint to travel."""
        # Click waypoint
        # Wait for menu
        # Click destination act tab
        # Click destination waypoint
        pass
```

---

## Detection Avoidance Tips

1. **Vary timing** - Never use fixed delays
2. **Human-like mouse paths** - Use WindMouse or similar
3. **Occasional "mistakes"** - Click slightly off target sometimes
4. **Take breaks** - Don't run 24/7 without pauses
5. **Vary run patterns** - Don't do identical actions every run
6. **Match human speed** - 5-10 px/ms mouse movement

### Random Variation Helper
```python
def vary(value, percent=10):
    """Add random variation to a value."""
    variation = value * (percent / 100)
    return value + random.uniform(-variation, variation)

# Usage
delay = vary(0.1, 20)  # 0.1 ± 20%
```

---

## References
- [PyDirectInput PyPI](https://pypi.org/project/PyDirectInput/)
- [WindMouse Algorithm](https://ben.land/post/2021/04/25/windmouse-human-mouse-movement/)
- [HumanCursor](https://github.com/riflosnake/HumanCursor)
- [LearnCodeByGaming Bot Tutorial](https://learncodebygaming.com/blog/how-to-build-a-bot-with-opencv)
