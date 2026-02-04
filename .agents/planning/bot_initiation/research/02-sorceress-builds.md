# Sorceress Builds and Leveling

Research on optimal Sorceress leveling builds and progression for bot automation.

**Primary Source:** https://maxroll.gg

---

## Leveling Progression Overview

The Sorceress uses **2 respecs** during the 1-75 journey:
1. **Levels 1-26:** Lightning/Nova build
2. **Levels 27-35:** Respec to Cold (Blizzard)
3. **Levels 36-75:** Blizzard + Meteor hybrid

---

## Phase 1: Normal Act 1-5 (Levels 1-26)

### Skill Allocation

| Level | Skill Points |
|-------|--------------|
| 2-4 | Charged Bolt |
| 6 | Frost Nova + Static Field |
| 7-9 | Static Field |
| 10 | Telekinesis |
| 11 | Frozen Armor |
| 12-13 | Nova |
| 14-20 | Nova |
| 18 | Teleport (1 point) |
| 21-26 | Nova |

### Stat Allocation
- Levels 2-10: All Vitality
- Levels 11-16: Strength for gear requirements
- Rest: Vitality

### Key Breakpoints
- **Level 13:** Nova becomes primary damage skill
- **Level 17:** Equip Stealth runeword
- **Level 18:** Teleport available
- **Level 26:** Complete Normal, prepare for Nightmare

### Gear Targets
- Short Staff +2/+3 Charged Bolt (shop from Akara)
- Stealth runeword (Tal + Eth) at level 17
- 2-socket helmet/armor for runewords

---

## Phase 2: Nightmare (Levels 27-35) - FIRST RESPEC

### Respec to Cold Tree

**Before Respec (Lightning):**
- Static Field: 5 points
- Teleport: 1 point
- Nova: ~20 points

**After Respec (Cold):**
- Frozen Armor: 1 point
- Ice Blast: 7 points
- Glacial Spike: 9 points
- Blizzard: 3 points
- Static Field: 5 points
- Teleport: 1 point

### Skill Progression
| Level | Skill Points |
|-------|--------------|
| 27-29 | Blizzard |
| 30 | Blizzard + Cold Mastery |
| 31-35 | Blizzard |

### Gear Targets
- Spirit Crystal Sword (Tal + Thul + Ort + Amn)
- Lore helmet (Ort + Sol)
- Target 63% Faster Cast Rate

---

## Phase 3: Hell (Levels 36-75)

### Skill Allocation
| Level | Skill Points |
|-------|--------------|
| 36-43 | Blizzard (max) |
| 44-50 | Glacial Spike |
| 51-56 | Fire Mastery + Meteor prereqs |
| 57-72 | Meteor |
| 73-75 | Glacial Spike |

### Combat Strategy
- Place Blizzard between you and melee enemies
- Use Static Field on tanky monsters first
- Glacial Spike for crowd control
- Skip Cold Immunes until Meteor level 10+
- Use Wand of Lower Resistance on bosses

---

## Leveling Areas by Level Range

| Level Range | Best Areas |
|-------------|------------|
| 1-5 | Den of Evil |
| 5-15 | Tristram Runs, Countess |
| 13-20 | Tal Rasha's Tombs |
| 20-25 | Cow Level (best), Travincal |
| 25-40 | Normal Baal Runs |
| 41-60 | Nightmare Baal Runs |
| 60-75+ | Hell Chaos Sanctuary, Baal |

---

## Farming Locations (Endgame)

### Easy/Safe Runs
- **Pindleskin:** Quick, no immunities concern
- **Mephisto:** Moat trick, great drops

### Intermediate Runs
- **Ancient Tunnels:** No cold immunes (Act 2)
- **Countess:** Rune farming

### Advanced Runs
- **Chaos Sanctuary:** High density, requires dual element
- **Baal Runs:** Best experience

---

## Bot Implementation Notes

### Predefined Build Data Structure
```python
SORC_LEVELING_BUILD = {
    "phase1": {  # Levels 1-26, Nova
        "skills": {
            2: "charged_bolt", 3: "charged_bolt", 4: "charged_bolt",
            6: ["frost_nova", "static_field"],
            7: "static_field", 8: "static_field", 9: "static_field",
            10: "telekinesis", 11: "frozen_armor",
            12: "nova", 13: "nova", 14: "nova", 15: "nova",
            16: "nova", 17: "nova", 18: ["nova", "teleport"],
            19: "nova", 20: "nova", 21: "nova", 22: "nova",
            23: "nova", 24: "nova", 25: "nova", 26: "nova"
        },
        "stats": "vitality_priority",
        "respec_at": 26
    },
    # ... phases 2 and 3
}
```

### Key Detection Points for Bot
1. Level-up detection (stat/skill point available)
2. Respec trigger conditions
3. Gear requirement checks
4. Area transition decisions

---

## References
- [Sorceress Leveling Guide](https://maxroll.gg/d2/guides/sorceress-leveling)
- [General Leveling Strategies](https://maxroll.gg/d2/resources/general-leveling)
- [Blizzard Sorceress Guide](https://maxroll.gg/d2/guides/blizzard-sorceress)
