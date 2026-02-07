# D2R Bot - Implementation Plan

## Implementation Checklist

- [x] Step 1: Project Setup and Core Infrastructure
- [x] Step 2: Screen Capture Module
- [x] Step 3: Template Matching System
- [x] Step 4: Game State Detection
- [x] Step 5: Input Controller with Human-Like Movement
- [x] Step 6: Configuration System
- [x] Step 7: State Machine Foundation
- [x] Step 8: Basic Game Interaction (Menu Navigation)
- [x] Step 9: Town Navigation and NPC Interaction
- [x] Step 10: Combat System (Sorceress)
- [x] Step 11: Health Monitoring and Chicken System
- [x] Step 12: Pindleskin Run Implementation
- [x] Step 13: Loot Detection and Pickup
- [x] Step 14: Inventory and Stash Management
- [x] Step 15: Mephisto Run Implementation
- [x] Step 16: Statistics and Logging System
- [x] Step 17: Error Recovery System
- [x] Step 18: Leveling System (Skill/Stat Allocation)
- [x] Step 19: Full Leveling Journey Integration
- [x] Step 20: Polish, Testing, and Documentation

---

## Step 1: Project Setup and Core Infrastructure

**Objective:** Set up the project structure, dependencies, and basic CLI entry point.

**Implementation Guidance:**
- Create the directory structure as defined in the design document
- Set up a Python virtual environment
- Create `requirements.txt` with core dependencies
- Implement basic CLI using `click` library
- Set up logging infrastructure with `loguru`

**Files to Create:**
```
d2r-bot/
├── src/
│   ├── __init__.py
│   ├── main.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── config/
│   └── .gitkeep
├── assets/
│   └── templates/
│       └── .gitkeep
├── logs/
│   └── .gitkeep
├── tests/
│   └── __init__.py
├── requirements.txt
├── setup.py
└── README.md
```

**Dependencies (requirements.txt):**
```
mss>=9.0.0
opencv-python>=4.8.0
numpy>=1.24.0
pydirectinput>=1.0.4
pytesseract>=0.3.10
PyYAML>=6.0
click>=8.1.0
loguru>=0.7.0
```

**Test Requirements:**
- Verify virtual environment creation
- Verify all dependencies install successfully
- Verify CLI entry point runs without errors
- Verify logger outputs to console and file

**Integration:** This is the foundation - all subsequent steps build on this structure.

**Demo:** Run `python -m src.main --help` and see CLI help output. Run `python -m src.main start` and see "Bot starting..." log message.

---

## Step 2: Screen Capture Module

**Objective:** Implement fast screen capture using mss library with caching.

**Implementation Guidance:**
- Create `src/vision/screen_capture.py`
- Implement `ScreenCapture` class with window detection
- Add frame caching (40ms) to avoid redundant captures
- Support full screen and region capture
- Handle window not found errors gracefully

**Key Code:**
```python
class ScreenCapture:
    def __init__(self, window_title: str = "Diablo II: Resurrected")
    def grab(self) -> np.ndarray
    def grab_region(self, region: Tuple[int, int, int, int]) -> np.ndarray
    def is_game_running(self) -> bool
```

**Test Requirements:**
- Test full screen capture returns valid numpy array
- Test region capture returns correct dimensions
- Test caching works (second call within 40ms returns same image)
- Test window detection finds game window (when running)
- Test graceful handling when game not running

**Integration:** This module will be used by TemplateMatcher and GameStateDetector.

**Demo:** Run a test script that captures the screen every second and saves to `test_captures/` folder. Display capture dimensions and timing info in console.

---

## Step 3: Template Matching System

**Objective:** Implement OpenCV template matching for finding UI elements.

**Implementation Guidance:**
- Create `src/vision/template_matcher.py`
- Implement template loading and caching
- Implement single match and multi-match functions
- Use `TM_CCOEFF_NORMED` method with configurable threshold
- Add duplicate filtering for multi-match (nearby matches)

**Key Code:**
```python
class TemplateMatcher:
    def __init__(self, template_dir: str = "assets/templates")
    def load_template(self, name: str) -> np.ndarray
    def find(self, screen: np.ndarray, template_name: str,
             threshold: float = 0.8) -> Optional[Match]
    def find_all(self, screen: np.ndarray, template_name: str,
                 threshold: float = 0.8) -> List[Match]
```

**Test Requirements:**
- Test template loading from file
- Test single match detection with known image
- Test multi-match detection finds all occurrences
- Test threshold filtering works correctly
- Test duplicate filtering removes nearby matches

**Integration:** Requires ScreenCapture from Step 2. Used by GameStateDetector.

**Demo:** Create a few test templates (e.g., Windows icons). Run script that captures screen, finds templates, and draws rectangles around matches. Save annotated image to show detection working.

---

## Step 4: Game State Detection

**Objective:** Implement game state detection from screenshots.

**Implementation Guidance:**
- Create `src/vision/game_detector.py`
- Implement `GameState` enum with all states
- Create templates for each detectable state
- Implement health/mana orb reading (color-based)
- Implement inventory open detection

**Templates to Create:**
- `screens/main_menu.png`
- `screens/character_select.png`
- `screens/loading.png`
- `screens/death.png`
- `hud/health_orb.png` (for positioning)
- `hud/inventory_open.png`

**Key Code:**
```python
class GameStateDetector:
    def detect_state(self, screen: np.ndarray) -> GameState
    def get_health_percent(self, screen: np.ndarray) -> float
    def get_mana_percent(self, screen: np.ndarray) -> float
    def is_inventory_open(self, screen: np.ndarray) -> bool
```

**Test Requirements:**
- Test state detection with sample screenshots
- Test health reading accuracy (±5%)
- Test mana reading accuracy (±5%)
- Test inventory detection works

**Integration:** Requires TemplateMatcher from Step 3. Central to State Machine.

**Demo:** Run script that continuously captures game screen and prints current detected state, health %, and mana % to console. Update every 500ms.

---

## Step 5: Input Controller with Human-Like Movement

**Objective:** Implement keyboard and mouse input with WindMouse algorithm.

**Implementation Guidance:**
- Create `src/input/controller.py`
- Create `src/input/mouse.py` with WindMouse implementation
- Create `src/input/keyboard.py` for key presses
- Add configurable timing variation
- Implement skill casting helper

**Key Code:**
```python
class InputController:
    def __init__(self, human_like: bool = True)
    def click(self, x: int, y: int, button: str = "left")
    def move_to(self, x: int, y: int)
    def press(self, key: str)
    def cast_skill(self, skill_key: str, target: Optional[Tuple[int, int]])

def wind_mouse(start_x, start_y, dest_x, dest_y, **params) -> None
```

**Test Requirements:**
- Test mouse movement reaches target position
- Test click registers at correct position
- Test key press works
- Test timing variation is applied
- Test WindMouse produces non-linear paths

**Integration:** Used by all game interaction modules.

**Demo:** Run script that moves mouse in a pattern across screen using WindMouse, visibly showing the curved, human-like paths. Then click at several positions and type "test" in a text editor.

---

## Step 6: Configuration System

**Objective:** Implement YAML-based configuration loading.

**Implementation Guidance:**
- Create `src/data/config.py`
- Create `src/data/models.py` for dataclasses
- Implement config loading with defaults
- Implement build loading for Sorceress
- Create default config files

**Files to Create:**
- `config/settings.yaml`
- `config/pickit.yaml`
- `config/builds/blizzard_leveling.yaml`

**Key Code:**
```python
@dataclass
class Config:
    game_path: str
    character_name: str
    chicken_health_percent: int
    # ... all config fields

class ConfigManager:
    def load(self) -> Config
    def get_build(self, name: str) -> Build
    def get_pickit_rules(self) -> PickitRules
```

**Test Requirements:**
- Test config loading from YAML
- Test default values applied when missing
- Test build loading works
- Test pickit rules loading works
- Test invalid config raises helpful error

**Integration:** Used by all modules that need configuration.

**Demo:** Run script that loads config and prints all settings to console in formatted output. Show build skill progression for levels 1-10.

---

## Step 7: State Machine Foundation

**Objective:** Implement the core state machine that controls bot flow.

**Implementation Guidance:**
- Create `src/state_machine.py`
- Implement `BotState` enum
- Implement state transition logic
- Add hooks for state entry/exit
- Implement main loop with state updates

**Key Code:**
```python
class BotStateMachine:
    def __init__(self, config: Config, detector: GameStateDetector,
                 input_ctrl: InputController)
    def start(self)
    def stop(self)
    def update(self)  # Main loop tick
    def transition_to(self, state: BotState)
    def register_handler(self, state: BotState, handler: Callable)
```

**Test Requirements:**
- Test state transitions work correctly
- Test invalid transitions are rejected
- Test handlers are called on state entry
- Test main loop runs without errors
- Test stop cleanly exits

**Integration:** Integrates GameStateDetector, InputController, Config.

**Demo:** Run bot with mock game states. See console output showing state transitions: IDLE → STARTING_GAME → IN_TOWN → IDLE (on stop). Each transition logged with timestamp.

---

## Step 8: Basic Game Interaction (Menu Navigation)

**Objective:** Implement menu navigation to start a game.

**Implementation Guidance:**
- Add templates for menu buttons
- Implement menu detection and button clicking
- Implement character selection
- Implement game creation/joining
- Handle loading screen waiting

**Templates to Create:**
- `buttons/play_button.png`
- `buttons/single_player.png`
- `buttons/online_button.png`
- `buttons/create_game.png`
- `screens/character_select.png`

**Key Code:**
```python
class MenuNavigator:
    def navigate_to_game(self) -> bool
    def select_character(self, name: str) -> bool
    def create_game(self, name: str, password: str = "") -> bool
    def wait_for_load(self, timeout: float = 30) -> bool
```

**Test Requirements:**
- Test menu button detection
- Test character selection works
- Test game creation succeeds
- Test loading screen detection
- Test timeout handling

**Integration:** Used by StateMachine for STARTING_GAME state.

**Demo:** Start bot, watch it navigate from main menu → character select → create game → enter game world. Bot then transitions to IN_TOWN state and stops.

---

## Step 9: Town Navigation and NPC Interaction

**Objective:** Implement town movement and NPC interaction.

**Implementation Guidance:**
- Create `src/game/town.py`
- Add templates for Act 5 town NPCs (Harrogath)
- Implement NPC detection and clicking
- Implement waypoint interaction
- Implement stash interaction

**Templates to Create:**
- `npcs/malah.png` (healer)
- `npcs/larzuk.png` (smith)
- `npcs/qual_kehk.png` (vendor)
- `npcs/anya.png` (portal)
- `hud/waypoint.png`
- `hud/stash.png`

**Key Code:**
```python
class TownManager:
    def go_to_npc(self, npc_name: str) -> bool
    def interact_with_npc(self, npc_name: str) -> bool
    def use_waypoint(self, destination: str) -> bool
    def open_stash(self) -> bool
    def go_to_portal(self) -> bool  # Anya's red portal
```

**Test Requirements:**
- Test NPC detection in town
- Test clicking NPC opens dialog
- Test waypoint menu opens
- Test stash opens
- Test red portal detection

**Integration:** Used by RunManager and StateMachine.

**Demo:** In Act 5 town, bot walks to stash, opens it, closes it, walks to Malah, interacts, closes dialog, walks to red portal. All actions visible and logged.

---

## Step 10: Combat System (Sorceress)

**Objective:** Implement Sorceress combat with Blizzard and teleport.

**Implementation Guidance:**
- Create `src/game/combat.py`
- Implement skill casting with cooldowns
- Implement teleport movement
- Implement attack pattern (Blizzard placement)
- Add Static Field usage for bosses

**Key Code:**
```python
class SorceressCombat:
    def __init__(self, config: Config, input_ctrl: InputController)
    def cast_teleport(self, target: Tuple[int, int])
    def cast_blizzard(self, target: Tuple[int, int])
    def cast_static_field(self)
    def attack_pattern(self, target: Tuple[int, int])
    def kite_and_attack(self, target: Tuple[int, int])
```

**Test Requirements:**
- Test teleport casts correctly
- Test Blizzard casts at target
- Test Static Field casts
- Test attack pattern executes
- Test skill cooldowns respected

**Integration:** Requires InputController and Config (for hotkeys).

**Demo:** In-game with Sorceress, run combat test that: casts Frozen Armor, teleports to 3 positions, casts Blizzard at each position, casts Static Field. All skills visible in game.

---

## Step 11: Health Monitoring and Chicken System

**Objective:** Implement health monitoring with automatic chicken (exit game).

**Implementation Guidance:**
- Create health monitoring thread/loop
- Implement chicken trigger at configurable threshold
- Implement fast game exit (save & exit)
- Add potion usage before chicken
- Log all chicken events

**Key Code:**
```python
class HealthMonitor:
    def __init__(self, detector: GameStateDetector, config: Config)
    def start_monitoring(self)
    def stop_monitoring(self)
    def check_health(self) -> bool  # Returns True if safe
    def chicken(self)  # Emergency exit
    def use_health_potion(self)
```

**Test Requirements:**
- Test health detection accuracy
- Test chicken triggers at threshold
- Test game exits cleanly
- Test potion usage works
- Test monitoring runs continuously

**Integration:** Runs alongside main bot loop, can interrupt any state.

**Demo:** Start bot with chicken threshold at 50%. Manually damage character (or mock low health). Watch bot detect low health, attempt potion, then chicken out of game. See logs showing the sequence.

---

## Step 12: Pindleskin Run Implementation

**Objective:** Implement complete Pindleskin farming run.

**Implementation Guidance:**
- Create `src/game/runs/pindle.py`
- Implement run sequence: town → portal → kill → loot → return
- Pindleskin is static location outside red portal
- Implement boss targeting
- Handle run completion and restart

**Run Sequence:**
1. Start in Harrogath
2. Go to Anya's red portal
3. Enter portal
4. Teleport to Pindleskin (short distance)
5. Cast Blizzard/attack
6. Wait for death
7. Loot items
8. Save & Exit or Town Portal
9. Repeat

**Key Code:**
```python
class PindleRun(BaseRun):
    def execute(self) -> RunResult
    def find_pindleskin(self, screen: np.ndarray) -> Optional[Tuple[int, int]]
    def kill_pindleskin(self)
    def loot_area(self)
```

**Test Requirements:**
- Test portal entry works
- Test Pindleskin detection
- Test combat sequence kills boss
- Test run completes successfully
- Test run handles death (chicken)

**Integration:** Full integration of Combat, Town, HealthMonitor, StateMachine.

**Demo:** Execute 3 Pindleskin runs. Watch bot: start game → go to portal → enter → kill Pindleskin → return to town → repeat. Console shows run times and success status.

---

## Step 13: Loot Detection and Pickup

**Objective:** Implement item detection on ground and pickup logic.

**Implementation Guidance:**
- Create `src/game/loot.py`
- Implement item label detection (by color)
- Implement quality detection (unique=gold, set=green, etc.)
- Implement pickup based on pickit rules
- Handle clicking items to pick up

**Key Code:**
```python
class LootManager:
    def scan_for_items(self, screen: np.ndarray) -> List[DetectedItem]
    def should_pickup(self, item: DetectedItem) -> bool
    def pickup_item(self, item: DetectedItem) -> bool
    def pickup_all_valid(self, screen: np.ndarray) -> int  # Returns count
```

**Test Requirements:**
- Test item label detection
- Test color-based quality detection
- Test pickit rules filtering
- Test item pickup works
- Test multiple items picked up

**Integration:** Uses ConfigManager for pickit rules, InputController for clicking.

**Demo:** Drop some items on ground (or kill monsters). Run loot scan, see detected items printed with quality. Bot picks up items matching rules, ignores others.

---

## Step 14: Inventory and Stash Management

**Objective:** Implement inventory space tracking and stashing items.

**Implementation Guidance:**
- Create inventory grid detection
- Implement space calculation
- Implement item identification (via Cain)
- Implement stash organization
- Implement potion restocking

**Key Code:**
```python
class InventoryManager:
    def get_free_space(self, screen: np.ndarray) -> int
    def is_full(self) -> bool
    def identify_items(self)  # Use Cain
    def stash_items(self)
    def buy_potions(self)
    def fill_belt(self)
```

**Test Requirements:**
- Test inventory space detection
- Test full inventory detection
- Test item identification works
- Test stashing moves items
- Test potion buying works

**Integration:** Used by TownManager and RunManager.

**Demo:** With items in inventory, bot: opens inventory (shows space count) → goes to Cain (identifies) → goes to stash (deposits items) → goes to vendor (buys potions) → fills belt. All visible.

---

## Step 15: Mephisto Run Implementation

**Objective:** Implement Mephisto farming run with moat trick.

**Implementation Guidance:**
- Create `src/game/runs/mephisto.py`
- Implement Durance Level 2 navigation
- Implement moat trick positioning
- Handle teleporting through random layout
- Implement Mephisto targeting

**Run Sequence:**
1. Use waypoint to Durance of Hate Level 2
2. Navigate to Level 3 stairs
3. Enter Level 3
4. Teleport to moat position
5. Kill Mephisto (moat trick)
6. Loot
7. Return to town

**Key Code:**
```python
class MephistoRun(BaseRun):
    def execute(self) -> RunResult
    def navigate_durance_2(self) -> bool
    def find_level_3_entrance(self) -> Optional[Tuple[int, int]]
    def position_for_moat_trick(self)
    def kill_mephisto(self)
```

**Test Requirements:**
- Test Durance 2 navigation
- Test Level 3 entry detection
- Test moat positioning
- Test Mephisto kill
- Test full run completion

**Integration:** Builds on all previous steps.

**Demo:** Execute Mephisto run. Bot: waypoints to Durance 2 → teleports to stairs → enters Level 3 → positions at moat → kills Mephisto → loots → returns. Success logged.

---

## Step 16: Statistics and Logging System

**Objective:** Implement comprehensive statistics tracking and reporting.

**Implementation Guidance:**
- Create `src/data/statistics.py`
- Track runs, items, deaths, chickens, times
- Persist stats to JSON file
- Implement session vs all-time stats
- Add console summary output

**Key Code:**
```python
class StatisticsTracker:
    def record_run(self, result: RunResult)
    def record_item(self, item: DetectedItem)
    def get_session_stats(self) -> SessionStats
    def print_summary(self)
    def export_json(self, filepath: str)
```

**Test Requirements:**
- Test run recording
- Test item recording
- Test persistence works
- Test stats calculation correct
- Test summary formatting

**Integration:** Called by RunManager after each run.

**Demo:** Run 5 Pindle runs. After completion, see stats summary: "Session: 5 runs, 3 uniques, 2 rares, 0 deaths, avg 45s/run". Stats saved to `stats/session_20240101.json`.

---

## Step 17: Error Recovery System

**Objective:** Implement robust error detection and recovery.

**Implementation Guidance:**
- Create `src/utils/error_handler.py`
- Implement stuck detection
- Implement disconnect recovery
- Implement game crash detection
- Add retry logic with limits
- Add critical error alerting

**Key Code:**
```python
class ErrorHandler:
    def handle(self, error: BotError) -> ErrorResolution
    def detect_stuck(self) -> bool
    def attempt_unstuck(self) -> bool
    def recover_from_disconnect(self) -> bool
    def restart_game(self) -> bool
```

**Test Requirements:**
- Test stuck detection works
- Test unstuck attempts recovery
- Test disconnect triggers reconnect
- Test crash triggers restart
- Test max retries stops bot

**Integration:** Integrated into StateMachine main loop.

**Demo:** Simulate errors: 1) Get character stuck → bot detects, teleports random direction, continues. 2) Kill game process → bot detects, restarts game, resumes. 3) Trigger 4 errors → bot stops with alert.

---

## Step 18: Leveling System (Skill/Stat Allocation)

**Objective:** Implement automatic skill and stat point allocation.

**Implementation Guidance:**
- Create `src/game/leveling.py`
- Detect level up (points available)
- Implement skill tree navigation
- Implement stat allocation
- Follow predefined build progression

**Key Code:**
```python
class LevelManager:
    def check_points_available(self, screen: np.ndarray) -> Tuple[int, int]
    def allocate_stat_points(self, count: int)
    def allocate_skill_points(self, skills: List[str])
    def needs_respec(self, level: int) -> bool
    def perform_respec(self)
```

**Test Requirements:**
- Test point detection
- Test stat allocation UI navigation
- Test skill allocation UI navigation
- Test build progression followed
- Test respec detection

**Integration:** Uses Config for build, triggered by StateMachine.

**Demo:** Level up character (or mock level up). Bot: detects points → opens stat screen → allocates vitality → opens skill screen → allocates Nova → closes screens. Allocation matches build config.

---

## Step 19: Full Leveling Journey Integration

**Objective:** Implement automated leveling from 1-75.

**Implementation Guidance:**
- Create leveling run sequences for each phase
- Implement area progression (Tristram → Tombs → Baal)
- Handle difficulty transitions
- Implement quest completion (as needed)
- Handle respec at level 26

**Key Code:**
```python
class LevelingManager:
    def get_current_phase(self, level: int) -> LevelingPhase
    def get_leveling_area(self, level: int) -> str
    def execute_leveling_run(self) -> RunResult
    def handle_difficulty_transition(self)
    def should_progress(self) -> bool
```

**Test Requirements:**
- Test phase detection by level
- Test area selection correct
- Test difficulty transition works
- Test respec triggers at right level
- Test quest completion (Ancients)

**Integration:** Full integration of all systems for autonomous leveling.

**Demo:** Start level 20 Sorceress. Bot: determines phase (Normal Baal runs) → executes Baal run sequence → gains levels → allocates points → continues until level 26 → respecs to Blizzard. Extended demo showing progression.

---

## Step 20: Polish, Testing, and Documentation

**Objective:** Final polish, comprehensive testing, and documentation.

**Implementation Guidance:**
- Write unit tests for all modules
- Perform integration testing
- Write user documentation (README)
- Add CLI help text
- Performance optimization
- Code cleanup and comments

**Deliverables:**
- Complete test suite with >80% coverage
- README with setup and usage instructions
- Troubleshooting guide
- Performance benchmarks
- Clean, documented code

**Test Requirements:**
- All unit tests pass
- Integration tests pass
- 8-hour stability test (offline)
- Memory leak check
- Performance meets targets (>1 run/minute for Pindle)

**Integration:** Final validation of entire system.

**Demo:** Run full demo sequence: Start bot → 10 Pindle runs → 5 Mephisto runs → show stats → stop bot. Present README and run test suite. All green, stable operation demonstrated.

---

## Implementation Notes

### Development Order Rationale

The steps are ordered to:
1. **Build foundation first** (Steps 1-7): Core infrastructure before game logic
2. **Enable early testing** (Steps 8-9): Can test with real game early
3. **Incremental features** (Steps 10-15): Each step adds visible functionality
4. **Full run before polish** (Steps 12, 15): Working runs before optimization
5. **Robustness last** (Steps 16-17): Error handling after happy path works

### Testing Approach

- **Offline first**: All development and testing in single player
- **Mock when needed**: Mock game states for unit tests
- **Real game integration**: Integration tests with actual game
- **Incremental demos**: Each step has verifiable demo

### Risk Mitigation

- **Template versioning**: Store templates with game version
- **Graceful degradation**: Fall back to safe states on errors
- **Extensive logging**: Debug issues with detailed logs
- **Quick iteration**: Small steps allow fast debugging
