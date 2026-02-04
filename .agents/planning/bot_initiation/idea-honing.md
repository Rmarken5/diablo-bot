# Idea Honing

This document captures the requirements clarification process through a series of questions and answers.

---

## Q1: How should the bot interact with the game?

There are several technical approaches for game automation:

- **Screen reading / Computer Vision**: Captures screen images, uses image recognition to understand game state, simulates mouse/keyboard input
- **Memory reading**: Directly reads game memory to get precise data (positions, stats, items), higher detection risk
- **Packet-based**: Intercepts/sends network packets, most complex and highest risk
- **Hybrid**: Combination of approaches

**Answer:** Screen reading / Computer Vision - Capture screen images, use image recognition to understand game state, and simulate mouse/keyboard input.

---

## Q2: What programming language would you like to use?

Common choices for computer vision bots include:

- **Python**: Rich ecosystem (OpenCV, PyAutoGUI, Tesseract OCR), rapid prototyping, most tutorials available
- **C++**: Best performance, direct OpenCV access, more complex to develop
- **C#**: Good Windows integration, decent CV libraries, middle ground
- **Rust**: High performance with safety guarantees, growing CV ecosystem

**Answer:** Python - Leveraging the rich ecosystem including OpenCV, PyAutoGUI, and OCR libraries.

---

## Q3: What specific farming activities should the bot support?

Common D2R farming targets:

- **Boss runs**: Mephisto, Baal, Diablo, Andariel, Pindleskin, etc.
- **Area farming**: Chaos Sanctuary, Cows, Pits, Ancient Tunnels, etc.
- **Key farming**: Countess, Summoner, Nihlathak
- **Rune farming**: Lower Kurast, Countess, Travincal
- **All of the above** or specific combination

**Answer:** Start with one or two simple runs (Pindleskin and/or Mephisto) as initial targets, with architecture designed to expand to other farming activities later.

---

## Q4: What character class should the bot support initially?

Different classes have different combat mechanics:

- **Sorceress**: Teleport for fast movement, ranged spells (Blizzard, Lightning, Fireball) - most common for MF bots
- **Paladin (Hammerdin)**: Blessed Hammer, Vigor for movement, very powerful but positioning matters
- **Necromancer (Summon)**: Minions do the work, safer but slower
- **Amazon (Javazon)**: Lightning Fury, good for cows/density
- **Other**: Barbarian, Druid, Assassin

**Answer:** Sorceress - Ideal for farming with Teleport for fast navigation and ranged spells for combat.

---

## Q5: Will the bot run on online (Battle.net) or offline (single player)?

This significantly affects the approach:

- **Offline (Single Player)**: No anti-cheat concerns, safe for development/testing, can pause freely, no network latency
- **Online (Battle.net)**: Risk of detection/ban, need to consider anti-cheat, more valuable for trading, network latency considerations
- **Both**: Design for offline first, with potential online support later

**Answer:** Both - Design and test on offline/single player first for safety, with architecture that supports online (Battle.net) later.

---

## Q6: How should the bot handle loot?

Key decisions for item management:

- **Pickit rules**: Pick all items, only rare+ quality, custom filter (like item level, base type, specific uniques)
- **Identification**: Auto-identify with scrolls/Cain, or leave unidentified
- **Inventory management**: When to go to town, how to handle full inventory
- **Stashing**: Auto-stash valuable items, organize stash tabs
- **Gold**: Pick up gold, manage gold amount

**Answer:** Deferred to research phase - Need to research best practices for loot filtering and inventory management approaches.

---

## Q7: For leveling, what level range and approach do you have in mind?

Leveling considerations:

- **Level range**: Low level (1-40), mid level (40-70), high level (70-99), or full journey
- **Leveling areas**: Tristram runs, Tomb runs, Baal runs, Chaos runs, Cow runs, etc.
- **Starting point**: Fresh character from Act 1, or assume character is already at farming level (e.g., 75+)
- **Difficulty progression**: Normal → Nightmare → Hell, or single difficulty

**Answer:** Automate the full leveling journey - From level 1 through Normal, Nightmare, and Hell difficulties. This includes act progression, quest completion, and difficulty transitions.

---

## Q8: How should the bot handle death and recovery?

Death handling strategies:

- **Corpse retrieval**: Return to body to recover gear, or keep backup gear in stash
- **Chicken (exit game)**: Detect low health and quickly exit game to prevent death
- **Safe spots**: Identify and use safe positions when health is low
- **Potion management**: When to use potions, belt management, restocking
- **Repeated deaths**: When to give up on an area and try alternative approach

**Answer:** Chicken - Detect low health and quickly exit/save game to prevent death. This avoids corpse retrieval complexity and gear loss.

---

## Q9: What kind of user interface do you want for the bot?

Interface options:

- **CLI (Command Line)**: Simple text-based, run scripts with arguments, good for starting out
- **GUI (Desktop App)**: Visual interface with buttons, settings panels, real-time status
- **Web UI**: Browser-based dashboard, could run locally or remotely
- **Overlay**: Transparent overlay on top of the game showing bot status
- **Headless + Config File**: No UI, just configuration files, runs in background

**Answer:** CLI (Command Line) - Simple text-based interface to start, configure, and monitor the bot. Good for initial development with option to add GUI later.

---

## Q10: What operating system will you run the bot on?

D2R runs on Windows and Mac. The bot's screen capture and input simulation libraries depend on the OS:

- **Windows**: Most common, best library support (win32api, pyautogui works well)
- **macOS**: Possible but fewer resources/examples, some library limitations
- **Linux (via Wine/Proton)**: Experimental, additional complexity

**Answer:** Windows - Best library support and most common platform for D2R botting.

---

## Q11: How should the bot handle skill and stat point allocation during leveling?

For automated full leveling, the bot needs to allocate points:

- **Predefined build**: Follow a fixed build guide (e.g., Blizzard Sorc, Lightning Sorc) with predetermined skill/stat order
- **Configurable build**: User specifies skill priority and stat distribution in config file
- **Adaptive**: Bot decides based on current gear/situation (complex)
- **Manual only**: Bot notifies user when points are available, user allocates manually

**Answer:** Predefined build - Follow a fixed build guide with predetermined skill and stat allocation order. Start with a proven leveling build (e.g., Blizzard Sorc).

---

## Q12: What level of logging and statistics do you want?

Monitoring the bot's performance:

- **Basic**: Simple console output showing current action and errors
- **Detailed logging**: Log file with timestamps, all actions, state transitions
- **Run statistics**: Track runs completed, items found, deaths, run times
- **Dashboard/Reports**: Generate summaries, graphs, item drop history
- **Screenshots**: Capture screenshots of valuable drops or errors

**Answer:**
- Phase 1: Detailed logging (log file with timestamps, actions, state transitions) + Run statistics (runs completed, items found, deaths, run times)
- Phase 2: Dashboards and reports (summaries, graphs, item history)

---

## Q13: How should the bot handle errors and unexpected situations?

Error recovery strategies:

- **Game crashes**: Detect crash, restart game, resume botting
- **Disconnects**: Detect disconnect, reconnect, resume
- **Stuck detection**: Recognize when bot is stuck, attempt recovery or restart run
- **Unknown screens**: Handle unexpected UI states gracefully
- **Pause and alert**: Stop and notify user when critical errors occur
- **Auto-retry limits**: Maximum retries before stopping

**Answer:** Full auto-recovery with pause on critical errors - Automatically handle game crashes, disconnects, and stuck situations. Pause and alert the user when critical/unrecoverable errors occur.

---

## Q14: What game resolution and display settings should the bot support?

Screen capture depends on display configuration:

- **Fixed resolution**: Support one specific resolution (e.g., 1920x1080) - simpler to develop
- **Multiple resolutions**: Support common resolutions (1080p, 1440p, 4K) - more flexible
- **Window mode**: Windowed, fullscreen, or borderless windowed
- **Scaling**: Handle Windows display scaling (100%, 125%, 150%)

**Answer:** Fixed resolution 1920x1080, windowed mode - Simplifies screen capture and template matching by targeting a single resolution.

