# Computer Vision for D2R Bot

Research on screen capture, template matching, and image recognition for game automation.

---

## Core Libraries

| Library | Purpose | Install |
|---------|---------|---------|
| **mss** | Fast screen capture | `pip install mss` |
| **opencv-python** | Image processing, template matching | `pip install opencv-python` |
| **numpy** | Array operations | `pip install numpy` |
| **pytesseract** | OCR text recognition | `pip install pytesseract` |
| **pydirectinput** | DirectInput for games | `pip install pydirectinput` |

---

## Screen Capture with MSS

MSS is ~30x faster than PyAutoGUI for screenshots.

```python
from mss import mss
import numpy as np
import cv2

class ScreenCapture:
    def __init__(self):
        self.sct = mss()

    def grab_screen(self, region=None):
        """Capture screen region as numpy array."""
        if region:
            monitor = {
                "left": region[0],
                "top": region[1],
                "width": region[2],
                "height": region[3]
            }
        else:
            monitor = self.sct.monitors[1]  # Primary monitor

        screenshot = self.sct.grab(monitor)
        # Convert to numpy array (BGR format for OpenCV)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def grab_game_window(self, window_title="Diablo II: Resurrected"):
        """Capture specific game window."""
        # Use win32gui to find window position
        import win32gui
        hwnd = win32gui.FindWindow(None, window_title)
        rect = win32gui.GetWindowRect(hwnd)
        region = (rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1])
        return self.grab_screen(region)
```

### Caching Strategy (from Botty)
```python
import time

class CachedScreenCapture:
    def __init__(self, cache_duration_ms=40):
        self.sct = mss()
        self.cache_duration = cache_duration_ms / 1000
        self.last_grab_time = 0
        self.cached_image = None

    def grab(self):
        current_time = time.time()
        if current_time - self.last_grab_time > self.cache_duration:
            self.cached_image = self._capture()
            self.last_grab_time = current_time
        return self.cached_image
```

---

## Template Matching with OpenCV

### Basic Template Matching

```python
import cv2
import numpy as np

def find_template(screenshot, template, threshold=0.8):
    """
    Find template in screenshot.
    Returns: (x, y, confidence) or None if not found
    """
    result = cv2.matchTemplate(
        screenshot,
        template,
        cv2.TM_CCOEFF_NORMED
    )

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        return (max_loc[0], max_loc[1], max_val)
    return None
```

### Finding Multiple Matches

```python
def find_all_templates(screenshot, template, threshold=0.8):
    """Find all occurrences of template above threshold."""
    result = cv2.matchTemplate(
        screenshot,
        template,
        cv2.TM_CCOEFF_NORMED
    )

    locations = np.where(result >= threshold)
    matches = []

    for pt in zip(*locations[::-1]):
        matches.append({
            "x": pt[0],
            "y": pt[1],
            "confidence": result[pt[1], pt[0]]
        })

    # Remove duplicates (nearby matches)
    return filter_nearby_matches(matches, min_distance=10)
```

### Template Matching Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| `TM_CCOEFF_NORMED` | Normalized correlation | Best general purpose |
| `TM_CCORR_NORMED` | Normalized cross-correlation | Similar brightness |
| `TM_SQDIFF_NORMED` | Normalized squared difference | Exact matches |

**Recommendation:** Use `TM_CCOEFF_NORMED` with threshold 0.8-0.9

---

## Game State Detection

### Detecting Screens/Menus

```python
class GameStateDetector:
    def __init__(self, template_dir="assets/templates"):
        self.templates = {
            "main_menu": cv2.imread(f"{template_dir}/main_menu.png"),
            "in_game": cv2.imread(f"{template_dir}/in_game_hud.png"),
            "inventory": cv2.imread(f"{template_dir}/inventory_open.png"),
            "death": cv2.imread(f"{template_dir}/death_screen.png"),
            "loading": cv2.imread(f"{template_dir}/loading.png"),
        }

    def get_current_state(self, screenshot):
        """Determine current game state from screenshot."""
        for state_name, template in self.templates.items():
            if find_template(screenshot, template, threshold=0.85):
                return state_name
        return "unknown"
```

### Health/Mana Detection

Two approaches:

**1. Color-based (faster):**
```python
def get_health_percentage(screenshot, health_orb_region):
    """Detect health by red pixel ratio in orb area."""
    orb = screenshot[
        health_orb_region[1]:health_orb_region[3],
        health_orb_region[0]:health_orb_region[2]
    ]

    # Red color range in BGR
    lower_red = np.array([0, 0, 150])
    upper_red = np.array([80, 80, 255])

    mask = cv2.inRange(orb, lower_red, upper_red)
    red_pixels = cv2.countNonZero(mask)
    total_pixels = orb.shape[0] * orb.shape[1]

    return red_pixels / total_pixels
```

**2. Template-based (more accurate):**
- Create templates for health at 100%, 75%, 50%, 25%, 10%
- Match against current state

---

## OCR for Text Recognition

### Reading Item Names

```python
import pytesseract
from PIL import Image

def read_item_text(screenshot, item_region):
    """Extract text from item tooltip."""
    # Crop to item region
    item_img = screenshot[
        item_region[1]:item_region[3],
        item_region[0]:item_region[2]
    ]

    # Preprocess for OCR
    gray = cv2.cvtColor(item_img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

    # OCR
    text = pytesseract.image_to_string(thresh)
    return text.strip()
```

### Color-Coded Text Detection

D2R item quality by color:
| Quality | Color (BGR) |
|---------|-------------|
| Normal | White (255, 255, 255) |
| Magic | Blue (255, 128, 0) |
| Rare | Yellow (0, 255, 255) |
| Unique | Gold (0, 165, 255) |
| Set | Green (0, 255, 0) |
| Rune | Orange (0, 128, 255) |

```python
def detect_item_quality(item_name_region):
    """Detect item quality by text color."""
    # Sample pixels from item name
    avg_color = np.mean(item_name_region, axis=(0, 1))

    # Compare to known colors
    qualities = {
        "unique": (0, 165, 255),
        "set": (0, 255, 0),
        "rare": (0, 255, 255),
        "magic": (255, 128, 0),
    }

    for quality, color in qualities.items():
        if color_distance(avg_color, color) < 50:
            return quality
    return "normal"
```

---

## Minimap Reading

### Detecting Minimap Elements

```python
class MinimapReader:
    def __init__(self):
        self.templates = {
            "waypoint": cv2.imread("assets/minimap/waypoint.png"),
            "portal": cv2.imread("assets/minimap/portal.png"),
            "exit": cv2.imread("assets/minimap/exit.png"),
            "monster": cv2.imread("assets/minimap/monster_dot.png"),
        }

    def find_elements(self, minimap_region):
        """Find all elements on minimap."""
        elements = {}
        for name, template in self.templates.items():
            matches = find_all_templates(minimap_region, template)
            if matches:
                elements[name] = matches
        return elements
```

---

## Performance Optimization

### Tips for Fast Detection

1. **Resize images** before matching (if precision allows)
2. **Use grayscale** when color not needed
3. **Cache templates** at startup
4. **Region of interest** - only scan relevant areas
5. **Multi-threading** for parallel detection tasks

```python
# Example: Resize for faster matching
def fast_find(screenshot, template, scale=0.5, threshold=0.8):
    small_screen = cv2.resize(screenshot, None, fx=scale, fy=scale)
    small_template = cv2.resize(template, None, fx=scale, fy=scale)

    result = find_template(small_screen, small_template, threshold)
    if result:
        # Scale coordinates back
        return (int(result[0]/scale), int(result[1]/scale), result[2])
    return None
```

---

## Template Creation Guidelines

1. **Capture at target resolution** (1920x1080)
2. **Avoid dynamic elements** (text, numbers)
3. **Include sufficient context** but not too much
4. **Test variations** (different lighting, states)
5. **Name consistently** (`menu_play_button.png`, `hud_health_orb.png`)

---

## References
- [OpenCV Template Matching](https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html)
- [LearnCodeByGaming Tutorial](https://learncodebygaming.com/blog/opencv-object-detection-in-games-python-tutorial-1)
- [MSS Documentation](https://python-mss.readthedocs.io/)
- [PyTesseract](https://pypi.org/project/pytesseract/)
