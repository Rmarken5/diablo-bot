# Navigation and Pathfinding

Research on navigating D2R's randomly generated maps.

---

## How D2R Maps Work

D2R uses a **jigsaw puzzle system** where fixed map tiles combine in various arrangements. The tiles themselves never change, but their arrangement is randomized each game.

### Map Types

| Type | Description | Example |
|------|-------------|---------|
| **Static** | Completely fixed layout | Den of Evil |
| **Semi-static** | Fixed borders, random internals | Blood Moor |
| **Dynamic** | Fully randomized tiles | Maggot Lair |

---

## Navigation System: Left/Right/Straight

D2R maps use a directional navigation system based on character perspective:

- **Left:** Exit is to your left relative to entrance
- **Right:** Exit is to your right relative to entrance
- **Straight:** Exit is directly ahead

### Act 1 Examples

| Area | Direction Pattern |
|------|-------------------|
| Forgotten Tower Levels | Left, Left, Left, Left, Left |
| Catacombs | Varies per level |
| Jail | Right, Right, Right |

### Key Insight
Maps can be "backwards" (requiring three right turns despite being marked "Left"), so understanding exit orientation relative to entrance is crucial.

---

## Landmark-Based Navigation

### Reliable Landmarks

| Landmark | Indicates |
|----------|-----------|
| Waypoint | Central hub, navigation anchor |
| Rock faces/cliffs | Area boundaries |
| Staircases | Level transitions |
| Camp markers (poles) | Side areas/special locations |
| Rivers (jungle acts) | Natural pathways |

### Act-Specific Tips

**Act 1:**
- Follow grass/dirt transitions
- Camps indicate nearby POIs

**Act 2:**
- Desert has predictable tile patterns
- Use waypoint placement to estimate area size

**Act 3:**
- Rivers are navigation highways
- Follow water to find exits

**Act 5:**
- Linear progression mostly
- Crystalline areas have distinct patterns

---

## Bot Navigation Strategies

### Strategy 1: Teleport + Explore (Sorceress)

```python
class TeleportNavigator:
    """Navigate by teleporting in a direction until finding target."""

    def navigate_to_exit(self, current_screen):
        # 1. Determine approximate direction (from map knowledge)
        direction = self.get_expected_direction()

        # 2. Teleport in that direction
        while not self.found_exit(current_screen):
            self.teleport_direction(direction)
            current_screen = self.capture_screen()

            # 3. Correct if hitting walls
            if self.hit_obstacle():
                direction = self.adjust_direction(direction)
```

### Strategy 2: Minimap Scanning

```python
class MinimapNavigator:
    """Use minimap to find objectives."""

    def find_on_minimap(self, target_template):
        minimap = self.capture_minimap_region()

        # Look for exit arrows, waypoints, etc.
        matches = template_match(minimap, target_template)
        if matches:
            return self.minimap_to_world_coords(matches[0])
        return None

    def navigate_to_minimap_target(self, target):
        while not self.at_target(target):
            direction = self.calculate_direction(target)
            self.move_towards(direction)
```

### Strategy 3: Landmark Recognition

```python
class LandmarkNavigator:
    """Navigate using recognized landmarks."""

    def __init__(self):
        self.landmarks = {
            "waypoint": cv2.imread("assets/waypoint.png"),
            "exit_stairs": cv2.imread("assets/exit_stairs.png"),
            "entrance": cv2.imread("assets/entrance.png"),
        }

    def scan_for_landmarks(self, screen):
        found = {}
        for name, template in self.landmarks.items():
            match = find_template(screen, template)
            if match:
                found[name] = match
        return found
```

---

## Specific Run Navigation

### Pindleskin Run
1. Start in Harrogath (Act 5 town)
2. Take red portal (Anya's portal to Nihlathak's Temple)
3. Pindleskin is always just outside portal
4. **Static location** - no pathfinding needed

### Mephisto Run
1. Start at Durance of Hate Level 2 waypoint
2. Navigate to Level 3 (random layout)
3. Teleport to center island (Mephisto location)
4. Use "moat trick" - stand across moat, Mephisto can't reach

**Durance Level 2 Navigation:**
- Tiles connect in predictable patterns
- Exit is always opposite general direction from entrance
- Small rooms lead to dead ends
- Large chambers may contain exit

---

## Teleport-Specific Considerations

### Teleport Mechanics
- Fixed distance per cast
- Cooldown based on FCR (Faster Cast Rate)
- Can teleport through walls/obstacles
- Random slight variation in landing position

### FCR Breakpoints for Teleport

| FCR | Frames | Casts/sec |
|-----|--------|-----------|
| 0% | 13 | 1.92 |
| 9% | 12 | 2.08 |
| 20% | 11 | 2.27 |
| 37% | 10 | 2.50 |
| 63% | 9 | 2.78 |
| 105% | 8 | 3.13 |
| 200% | 7 | 3.57 |

**Target:** 63% FCR for efficient teleporting

### Teleport Navigation Algorithm

```python
def teleport_to_target(target_x, target_y, current_x, current_y):
    """Navigate using teleport."""
    teleport_distance = 40  # Approximate teleport distance

    while distance(current_x, current_y, target_x, target_y) > teleport_distance:
        # Calculate direction to target
        angle = math.atan2(target_y - current_y, target_x - current_x)

        # Click at teleport range in that direction
        click_x = current_x + teleport_distance * math.cos(angle)
        click_y = current_y + teleport_distance * math.sin(angle)

        cast_teleport(click_x, click_y)
        wait_for_teleport_animation()

        # Update position (from minimap or screen)
        current_x, current_y = get_current_position()
```

---

## Handling Getting Stuck

```python
class StuckDetector:
    def __init__(self):
        self.position_history = []
        self.stuck_threshold = 5  # Same position for 5 checks

    def check_stuck(self, current_pos):
        self.position_history.append(current_pos)
        if len(self.position_history) > self.stuck_threshold:
            self.position_history.pop(0)

        # Check if all recent positions are similar
        if len(self.position_history) >= self.stuck_threshold:
            if all_positions_similar(self.position_history):
                return True
        return False

    def unstuck(self):
        """Try to get unstuck."""
        # Strategy 1: Teleport in random direction
        random_direction = random.uniform(0, 2 * math.pi)
        self.teleport_direction(random_direction)

        # Strategy 2: If still stuck, save and exit game
        if self.check_stuck(self.get_position()):
            self.chicken()  # Exit game
```

---

## References
- [D2R Map Reading Guide](https://maxroll.gg/d2/resources/map-reading)
- [Botty Navigation Source](https://github.com/aeon0/botty)
