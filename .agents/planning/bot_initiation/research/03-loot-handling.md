# Loot Handling Strategies

Research on item filtering, pickup rules, and inventory management for D2R bots.

---

## NIP (Njaguar's Item Parser) System

NIP is the standard format for defining item pickup rules in D2 bots (used by Kolbot, Botty, etc.).

### NIP Rule Structure

```
{properties} # {stats} # {maxquantity}
```

Three sections separated by `#`:
1. **Properties:** Item constants (type, quality, class)
2. **Stats:** Variable attributes and required values
3. **Maxquantity:** Limits on items to keep

### Property Keywords (Section 1)

| Keyword | Description | Example |
|---------|-------------|---------|
| `[type]` | Item category | `boots`, `ring`, `circlet` |
| `[name]` | Specific item name | `shakohelm`, `oculus` |
| `[class]` | Quality tier | `normal`, `exceptional`, `elite` |
| `[quality]` | Magic quality | `magic`, `rare`, `unique`, `set` |
| `[flag]` | Special flags | `ethereal` |
| `[level]` | Item level | Numeric value |
| `[prefix]` | Specific prefix | Affix name |
| `[suffix]` | Specific suffix | Affix name |

### Stat Keywords (Section 2)

| Category | Keywords |
|----------|----------|
| Resistances | `[fireresist]`, `[coldresist]`, `[lightresist]`, `[poisonresist]` |
| Character | `[dexterity]`, `[strength]`, `[vitality]`, `[energy]` |
| Combat | `[tohit]`, `[lifeleech]`, `[manaleech]`, `[enhanceddamage]` |
| Casting | `[fcr]` (faster cast rate) |
| Movement | `[frw]` (faster run/walk), `[fhr]` (faster hit recovery) |
| Other | `[sockets]`, `[maxhp]`, `[maxmana]`, `[magicfind]` |
| Skills | `[amazonskills]`, `[sorceressskills]`, `[druidskills]`, etc. |

### Operators

**Comparison:**
- `==` equals
- `!=` not equal
- `>` greater than
- `>=` greater or equal
- `<` less than
- `<=` less or equal

**Logical:**
- `&&` AND (all conditions required)
- `||` OR (any condition valid)
- `()` grouping

---

## Example Pickit Rules

### Basic Rules

```nip
// Pick all unique items
[quality]==unique

// Pick all set items
[quality]==set

// Pick all runes
[type]==rune

// Pick specific rune, max 3
[name]==helrune # # [maxquantity]==3
```

### Rare Item Rules

```nip
// Rare ring with good stats
[type]==ring && [quality]==rare # [lifeleech]>=4 && [tohit]>=80 && [dexterity]>=10 && [maxhp]>=20

// Rare boots with run/walk and resists
[type]==boots && [quality]==rare # [frw]>=30 && [fireresist]>=20 && [lightresist]>=20

// Rare amulet with FCR and skills
[type]==amulet && [quality]==rare # [fcr]>=10 && [sorceressskills]>=2
```

### Class-Specific Rules

```nip
// Druid pelt with tornado
[type]==pelt && [quality]==rare # ([druidskills]>=2 || [elementalskilltab]>=2) && [skilltornado]>=3

// Sorc orb with skills
[type]==orb && [quality]==rare # [sorceressskills]>=2 && [fcr]>=20
```

---

## Recommended Loot Strategy for Bot

### Phase 1: Early Leveling (Simple)
- Pick all unique and set items
- Pick all runes
- Pick gold
- Pick potions when belt not full
- Pick gems (for crafting)

### Phase 2: Farming (Selective)
- Unique/Set items (always)
- Runes Hel+ (valuable)
- Rares with good base types only
- Specific runeword bases (4os monarch, etc.)
- Charms (skillers, resist, life)

### Phase 3: Optimized (Strict)
- High-value uniques only
- High runes (Ist+)
- Perfect rare rolls
- GG charms

---

## Implementation Approach

### Option 1: NIP Parser (Recommended)
- Parse NIP files at startup
- Evaluate items against rules
- Compatible with existing pickit files
- Community can share/modify rules

### Option 2: Simplified Rule System
- Python dict/YAML configuration
- Easier to implement
- Less flexible than NIP
- Good for MVP

### Hybrid Approach (Recommended for MVP)
```python
SIMPLE_PICKIT = {
    "always_pick": [
        "unique", "set", "rune"
    ],
    "pick_if": {
        "rare_ring": {"min_stats": {"life_leech": 3, "mf": 15}},
        "rare_boots": {"min_stats": {"frw": 30, "resist_total": 40}}
    },
    "never_pick": [
        "white_armor", "low_gold"
    ]
}
```

---

## Inventory Management

### Belt Management
- Keep 4 columns configured (health, mana, rejuv, antidote/thaw)
- Refill from inventory when slots empty
- Buy potions in town when low

### Inventory Space
- Reserve rows for pickups
- Town when full
- Identify items before stashing

### Stash Organization
- Tab 1: Gems and runes
- Tab 2: Uniques/Sets to keep
- Tab 3: Items to trade/evaluate
- Tab 4: Overflow

---

## References
- [NIP Guide](https://github.com/blizzhackers/pickits/blob/master/NipGuide.md)
- [D2R Pickit Examples](https://github.com/bossdjay/d2rpickit/)
- [Botty NIP Config](https://github.com/aeon0/botty)
