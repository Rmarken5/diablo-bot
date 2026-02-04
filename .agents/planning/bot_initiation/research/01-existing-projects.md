# Existing D2R Bot Projects

Research on existing open-source D2R bots to learn from their approaches.

---

## Primary Reference: Botty (aeon0/botty)

**Repository:** https://github.com/aeon0/botty

**Status:** Archived (July 2022) but remains an excellent reference implementation.

### Overview
- **Language:** Python 100%
- **Approach:** Pixel/screen-based bot using OpenCV for template matching
- **Purpose:** D2R single player automation (educational)

### Supported Features
- **Characters:** Sorceress (Blizzard, Lightning, Nova, Hydra), Hammerdin, FoH Paladin, Trapsin, Barbarian, Necromancer
- **Farming Runs:** Pindleskin, Eldritch, Shenk, Nihlathak, Arcane Sanctuary, Travincal, Diablo

### Technical Architecture

#### Core Libraries
| Library | Purpose |
|---------|---------|
| **mss** | Ultra-fast screen capture (~30x faster than PyAutoGUI) |
| **OpenCV (cv2)** | Template matching, image processing |
| **pydirectinput** | DirectInput for keyboard/mouse (works with DirectX games) |
| **pytesseract** | OCR for text recognition |
| **numpy** | Image array manipulation |

#### Key Technical Details
- Screen capture is cached for 40ms (1 frame) to avoid redundant grabs
- Template matching scores > 0.9 indicate reliable matches
- Uses DirectInput (not Virtual Key Codes) for game compatibility
- Configuration-driven via INI files

### Directory Structure
```
botty/
├── config/         # INI configuration files, NIP pickit rules
├── src/            # Core bot logic
├── assets/         # Templates, documentation
├── test/           # Test suite
└── dependencies/   # External requirements
```

### Configuration System
- **params.ini:** Main config (difficulty, character type, hotkeys, runs)
- **game.ini:** Game-specific settings
- Supports multiple character builds with class-specific settings
- Configurable attack lengths, healing thresholds, potion management

### Key Takeaways for Our Bot
1. **Use mss for screen capture** - Much faster than alternatives
2. **Use pydirectinput for input** - Required for DirectX games
3. **Template matching with OpenCV** - Proven approach for game state detection
4. **Configuration-driven design** - INI files for easy customization
5. **Modular run system** - Each farming run as a separate module

---

## References
- [aeon0/botty GitHub](https://github.com/aeon0/botty)
- [PyDirectInput PyPI](https://pypi.org/project/PyDirectInput/)
- [python-mss GitHub](https://github.com/BoboTiG/python-mss)

