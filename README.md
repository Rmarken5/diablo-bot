# D2R Bot

A computer vision based automation bot for Diablo II: Resurrected. Supports farming runs (Pindleskin, Mephisto) and fully automated leveling from 1-75 with a Blizzard Sorceress.

## Features

- **Farming Runs** - Pindleskin (fast, consistent) and Mephisto (moat trick) with automatic looting
- **Auto Leveling** - Full 1-75 journey: Tristram > Tombs > Cows > Baal through Normal/Nightmare/Hell
- **Smart Looting** - Color-based item quality detection with configurable pickit rules
- **Chicken System** - Emergency game exit when health drops below threshold
- **Inventory Management** - Automatic stashing, belt filling, potion restocking
- **Skill/Stat Allocation** - Auto-allocates points on level-up following your build config
- **Error Recovery** - Stuck detection, disconnect recovery, crash restart with retry limits
- **Statistics** - Per-session and all-time tracking with JSON persistence
- **Human-Like Input** - WindMouse algorithm for natural mouse movement

## Requirements

- Windows 10/11
- Python 3.10+
- Diablo II: Resurrected (purchased copy)
- Game running at **1920x1080 windowed** mode

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd d2r-bot

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac (for development only)

# Install dependencies
pip install -r requirements.txt

# Or install as editable package
pip install -e .
```

### Dependencies

| Package | Purpose |
|---|---|
| mss | Fast screen capture |
| opencv-python | Template matching and image analysis |
| numpy | Image array processing |
| pydirectinput | Mouse/keyboard input (DirectInput) |
| pytesseract | OCR for text recognition |
| PyYAML | Configuration file parsing |
| click | CLI framework |
| loguru | Structured logging |

## Game Setup

Before running the bot, configure D2R:

1. **Resolution**: Set to **1920x1080 windowed** mode (Options > Video)
2. **Character**: Create a Sorceress (the only supported class currently)
3. **Hotkeys**: The bot expects these default bindings (or edit `config/settings.yaml`):

   | Action | Default Key |
   |---|---|
   | Skill Left | F1 |
   | Skill Right | F2 |
   | Teleport | F3 |
   | Blizzard | F4 |
   | Static Field | F5 |
   | Frozen Armor | F6 |
   | Town Portal | T |
   | Show Items | Alt |
   | Inventory | I |
   | Character Screen | C |
   | Skill Tree | K |
   | Potions 1-4 | 1-4 |

4. **Difficulty**: For farming runs, be on the appropriate difficulty. For leveling, the bot manages difficulty progression.

## Usage

### CLI Commands

```bash
# Show all commands
python -m src.main --help

# Start Pindleskin farming (default)
python -m src.main start --run pindle

# Start Mephisto farming
python -m src.main start --run mephisto

# Start leveling mode
python -m src.main start --run level

# Run a fixed number of runs (e.g. 50)
python -m src.main start --run pindle --count 50

# Enable debug logging
python -m src.main --log-level DEBUG start --run pindle

# Write logs to a custom directory
python -m src.main --log-dir /path/to/logs start --run pindle

# View run statistics
python -m src.main stats
python -m src.main stats --format json

# Show version
python -m src.main version
```

### Run Types

#### Pindleskin (`--run pindle`)

The fastest and simplest farming run. Best for starting out.

1. Starts in Act 5 Harrogath
2. Goes to Anya's red portal
3. Enters portal, teleports to Pindleskin
4. Casts Static Field + Blizzard
5. Loots drops
6. Saves & exits, repeats

**Requirements**: Must have completed Anya's quest (red portal available).

#### Mephisto (`--run mephisto`)

Higher potential drops using the moat trick. More complex navigation.

1. Uses waypoint to Durance of Hate Level 2
2. Teleports to find Level 3 entrance
3. Enters Level 3, teleports to moat trick position
4. Attacks Mephisto from across the moat (safe spot)
5. Teleports to corpse, loots, saves & exits

**Requirements**: Act 3 Durance of Hate waypoint.

#### Leveling (`--run level`)

Automated leveling from 1-75 through all difficulties.

| Level Range | Area | Combat Style |
|---|---|---|
| 1-15 | Tristram / Countess (Normal) | Nova |
| 13-24 | Tal Rasha's Tombs (Normal) | Nova |
| 20-25 | Cow Level (Normal) | Nova |
| 25-40 | Baal Runs (Normal) | Nova |
| 41-60 | Baal Runs (Nightmare) | Blizzard |
| 60-70 | Chaos Sanctuary (Hell) | Static + Blizzard |
| 70-75 | Baal Runs (Hell) | Static + Blizzard |

The bot automatically:
- Progresses between leveling areas based on character level
- Transitions between Normal > Nightmare > Hell
- Allocates stat/skill points on level-up per the build config
- Triggers respec at level 26 (Nova > Blizzard transition)
- Does town runs every 5 runs (heal, repair, stash)

## Configuration

All config files are in the `config/` directory.

### `config/settings.yaml`

Main bot settings:

```yaml
general:
  window_title: "Diablo II: Resurrected"
  resolution: [1920, 1080]

character:
  name: "BotSorc"
  class: "sorceress"
  build: "blizzard_leveling"   # References config/builds/<name>.yaml

runs:
  enabled:
    - pindleskin
  count: 0                     # 0 = infinite

safety:
  chicken_health: 30           # Exit game below this HP %
  chicken_mana: 0              # Exit game below this mana % (0 = disabled)
  max_deaths: 5                # Stop bot after N deaths

timing:
  action_delay_ms: 50          # Base delay between actions
  human_like: true             # WindMouse movement
  mouse_speed: "normal"        # slow / normal / fast

hotkeys:
  teleport: "f3"
  blizzard: "f4"
  # ... (see file for full list)
```

### `config/pickit.yaml`

Controls which items to pick up:

```yaml
# Always pick up these qualities
pickup_qualities:
  - unique
  - set
  - rune

# Elite bases for runewords
pickup_bases:
  - monarch          # Spirit
  - archon plate     # Enigma
  - eth thresher     # Merc weapon
  # ...

# Minimum gold pile size
gold_threshold: 5000

# Specific rules (first match wins)
rules:
  - quality: rare
    base_type: ring
    pickup: true       # Pick up rare rings

  - quality: magic
    base_type: jewel
    pickup: true       # Pick up magic jewels (facets)

  - base_type: small charm
    pickup: true       # Pick up all small charms

  - quality: normal
    pickup: false      # Skip normal items
```

### `config/builds/blizzard_leveling.yaml`

Defines the skill and stat allocation plan:

```yaml
stats:
  priority: [vitality, strength]
  strength_target: 156         # For Monarch
  dexterity_target: 0

skills:
  hotkeys:
    blizzard: "f4"
    teleport: "f3"
    # ...

  # Skill points by level
  progression:
    # Phase 1: Nova (levels 2-25)
    2: [fire_bolt]
    6: [static_field, telekinesis]
    8: [nova]
    12: [teleport, nova]
    # ...

    # Phase 2: Blizzard (after respec at 26)
    26: [ice_bolt]
    30: [blizzard, cold_mastery]
    50: [glacial_spike]     # Synergy
    70: [ice_blast]         # Synergy

respec:
  level: 26
```

To create a custom build, copy `blizzard_leveling.yaml` and modify it. Reference it in `settings.yaml` under `character.build`.

## Safety Features

### Chicken System

The bot monitors health in a background thread and will emergency-exit the game if HP drops below the configured threshold (default 30%). The exit sequence uses layered fallbacks:

1. Menu navigator (template-based "Save & Exit" detection)
2. Hardcoded button position click
3. Double-Escape as last resort

### Error Recovery

The error handler classifies issues by severity and attempts automatic recovery:

| Error | Severity | Recovery |
|---|---|---|
| Stuck (not moving) | Recoverable | Random teleport |
| Template not found | Recoverable | Wait and retry |
| Action timeout | Recoverable | Press Escape, retry |
| Inventory full | Recoverable | End run, do town trip |
| Character death | Run-ending | Start new run |
| Disconnect | Run-ending | Wait, restart game |
| Game crash | Critical | Restart game process |

After 3 consecutive failed recoveries, the bot escalates to ending the run. After repeated run failures, it stops and alerts.

## Running Tests

Tests use the project's custom test runner (not pytest):

```bash
# Activate venv
source venv/bin/activate      # Linux
venv\Scripts\activate          # Windows

# Run a specific test suite
python -m tests.test_combat
python -m tests.test_inventory
python -m tests.test_leveling

# Run all test suites
for f in tests/test_*.py; do python -m "${f%.py}" | tail -3; done
```

### Test Suites

| Test File | Module | Tests |
|---|---|---|
| test_combat.py | SorceressCombat | 19 |
| test_config.py | ConfigManager | 10 |
| test_error_handler.py | ErrorHandler, StuckDetector | 25 |
| test_game_detector.py | GameStateDetector | 12 |
| test_health.py | HealthMonitor | 21 |
| test_input.py | InputController | 9 |
| test_inventory.py | InventoryManager | 24 |
| test_leveling.py | LevelManager | 29 |
| test_leveling_run.py | LevelingRun, LevelingManager | 26 |
| test_loot.py | LootManager | 30 |
| test_menu.py | MenuNavigator | 14 |
| test_mephisto.py | MephistoRun | 15 |
| test_pindle.py | PindleRun | 19 |
| test_screen_capture.py | ScreenCapture | 7 |
| test_state_machine.py | BotStateMachine | 13 |
| test_statistics.py | StatisticsTracker | 18 |
| test_template_matcher.py | TemplateMatcher | 11 |
| test_town.py | TownManager | 20 |

Note: `test_screen_capture.py` requires a display server and will fail in headless environments.

## Project Structure

```
d2r-bot/
├── src/
│   ├── main.py              # CLI entry point
│   ├── state_machine.py     # Bot state machine (35+ states)
│   ├── vision/
│   │   ├── screen_capture.py    # mss-based capture with 40ms cache
│   │   ├── template_matcher.py  # OpenCV TM_CCOEFF_NORMED matching
│   │   └── game_detector.py     # Game state, health/mana orb reading
│   ├── input/
│   │   ├── controller.py    # Mouse/keyboard abstraction
│   │   ├── mouse.py         # WindMouse algorithm
│   │   └── keyboard.py      # Key press with human-like timing
│   ├── game/
│   │   ├── combat.py        # SorceressCombat (30+ skills, cooldowns)
│   │   ├── health.py        # HealthMonitor (background thread, chicken)
│   │   ├── inventory.py     # Grid tracking, stash, belt management
│   │   ├── leveling.py      # Skill/stat allocation per build
│   │   ├── loot.py          # Color-based quality detection, pickit
│   │   ├── menu.py          # Game entry/exit navigation
│   │   ├── town.py          # NPC interaction, waypoints, portals
│   │   └── runs/
│   │       ├── base.py      # BaseRun (health monitoring, timing)
│   │       ├── pindle.py    # Pindleskin run
│   │       ├── mephisto.py  # Mephisto moat trick run
│   │       └── leveling.py  # Leveling phases + journey manager
│   ├── data/
│   │   ├── models.py        # Config, Build, PickitRules dataclasses
│   │   ├── config.py        # YAML config loading
│   │   └── statistics.py    # Run/item tracking, JSON persistence
│   └── utils/
│       ├── logger.py        # loguru setup
│       └── error_handler.py # Error classification and recovery
├── config/
│   ├── settings.yaml        # Main bot config
│   ├── pickit.yaml          # Item pickup rules
│   └── builds/
│       └── blizzard_leveling.yaml  # Blizzard Sorc build
├── assets/templates/        # Screenshot templates for detection
├── logs/                    # Runtime logs
├── stats/                   # Session statistics (JSON)
└── tests/                   # Test suite (300+ tests)
```

## Troubleshooting

### Bot doesn't detect the game window
- Ensure D2R is running in **1920x1080 windowed** mode (not fullscreen)
- Check `window_title` in `settings.yaml` matches your game window title exactly

### Bot clicks in wrong positions
- Verify resolution is exactly 1920x1080 - all screen positions are hardcoded for this resolution
- Make sure no Windows display scaling is applied (set to 100%)

### Chicken triggers too often
- Increase `chicken_health` threshold in `settings.yaml` (e.g., 40-50%)
- Ensure your character has enough health/resistances for the content

### Bot gets stuck navigating
- The error recovery system should teleport randomly to unstick
- If it happens repeatedly, the area layout may not match expected positions
- Check logs in `logs/` for detailed error information

### Template matching fails
- Templates in `assets/templates/` must match your game's visual style
- Different D2R graphics settings can affect template matching accuracy
- Use `--log-level DEBUG` to see matching confidence scores

### Tests fail
- `test_screen_capture` requires a display - expected to fail in headless/CI
- Ensure you're running from the project root with the venv activated
- Check that all dependencies are installed: `pip install -r requirements.txt`

## Architecture

The bot uses a **state machine** architecture with these main components:

1. **Vision Layer** - Captures screen, matches templates, detects game state
2. **Input Layer** - Sends mouse/keyboard input with human-like patterns
3. **Game Logic** - Combat, health monitoring, loot, town, leveling
4. **Run System** - Orchestrates farming runs and leveling sequences
5. **Data Layer** - Configuration loading, statistics tracking

All components use **dependency injection** - pass `None` for any dependency and the module gracefully degrades or uses defaults. This makes testing straightforward (mock what you need).

## Disclaimer

This bot is for educational purposes and offline/single-player use only. Using automation tools online may violate Blizzard's Terms of Service and result in account bans.
