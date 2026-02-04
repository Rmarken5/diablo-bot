# D2R Bot

A computer vision based automation bot for Diablo II: Resurrected.

## Features

- **Farming Runs:** Pindleskin, Mephisto
- **Auto Leveling:** Full 1-75 journey support
- **Smart Looting:** Configurable pickit rules
- **Safety:** Chicken system (exit on low health)
- **Statistics:** Detailed run tracking and logging

## Requirements

- Windows 10/11
- Python 3.10+
- Diablo II: Resurrected
- Game running at 1920x1080 windowed mode

## Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## Usage

```bash
# Show help
python -m src.main --help

# Start Pindleskin runs
python -m src.main start --run pindle

# Start with debug logging
python -m src.main --log-level DEBUG start --run pindle

# Show version
python -m src.main version
```

## Configuration

Configuration files are in the `config/` directory:

- `settings.yaml` - General bot settings
- `pickit.yaml` - Item pickup rules
- `builds/` - Character build definitions

## Project Structure

```
d2r-bot/
├── src/
│   ├── main.py          # CLI entry point
│   ├── vision/          # Screen capture and analysis
│   ├── input/           # Keyboard/mouse control
│   ├── game/            # Game logic (runs, combat, town)
│   ├── data/            # Config and statistics
│   └── utils/           # Logging and helpers
├── config/              # Configuration files
├── assets/templates/    # Image templates for detection
├── logs/                # Log files
├── stats/               # Statistics data
└── tests/               # Test suite
```

## Development Status

- [x] Step 1: Project Setup
- [ ] Step 2: Screen Capture
- [ ] Step 3: Template Matching
- [ ] ... (see implementation plan)

## Disclaimer

This bot is for educational purposes and offline/single-player use only. Using automation tools online may violate Blizzard's Terms of Service and result in account bans.
