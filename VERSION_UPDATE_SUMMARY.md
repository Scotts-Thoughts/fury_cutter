# Version Update Summary - Gen1 & Gen2 Support

## Changes Made

Added support for three new Pokemon game versions:

### 1. Pokemon Crystal (Generation 2)
- **OCR Region**: X=1548, Y=40, Width=355, Height=34
- **OCR Pattern**: "team" (e.g., "Falkner's Team")
- **Platform**: GameBoy (Game Boy Color)
- **Gameplay Region**: X=400, Y=36, Width=1120, Height=1008
- **Trainers** (23 total):
  - Gym Leaders: Falkner, Bugsy, Whitney, Morty, Chuck, Pryce, Jasmine, Clair
  - Elite Four: Will, Koga, Bruno, Karen
  - Champions: Lance, Red
  - Kanto Gym Leaders: Brock, Misty, Lt. Surge, Janine, Erika, Blaine, Sabrina
  - Special: Rival, Blue

### 2. Pokemon Yellow (Generation 1)
- **OCR Region**: X=1548, Y=40, Width=355, Height=34
- **OCR Pattern**: "team" (e.g., "Rival 2's Team")
- **Platform**: GameBoy (Game Boy)
- **Gameplay Region**: X=400, Y=36, Width=1120, Height=1008
- **Trainers** (14 total):
  - Gym Leaders: Brock, Misty, Lt. Surge, Erika, Koga, Blaine, Sabrina, Giovanni
  - Elite Four: Lorelei, Bruno, Agatha, Lance
  - Special: Rival, Champion

### 3. Pokemon Red (Generation 1)
- **OCR Region**: X=1548, Y=40, Width=355, Height=34
- **OCR Pattern**: "team" (e.g., "Rival 2's Team")
- **Platform**: GameBoy (Game Boy)
- **Gameplay Region**: X=400, Y=36, Width=1120, Height=1008
- **Trainers** (14 total):
  - Same as Yellow (see above)

## Technical Changes

### 1. Platform and Generation Enum Updates
- Added `GEN1 = 1` and `GEN2 = 2` to the `Generation` enum.
- Added `GAMEBOY = "gb"` to the `Platform` enum for Game Boy / Game Boy Color systems.
- Added GameBoy platform configuration to `PLATFORM_CONFIGS` for backwards compatibility.

### 2. Pattern Matching Enhancements
Enhanced the rival pattern matching for Gen1/Gen2 to handle:
- Standard format: "Rival's Team"
- Numbered format: "Rival 2's Team", "Rival 3's Team", etc.
- Compact format: "Rival2's Team" (no space)
- Missing apostrophe: "Rivals Team", "Rival 2s Team"
- Both straight (') and curly (') apostrophes

Pattern implementation:
```python
rival_patterns = [
    r"\brival\s*\d+['\u2019]?s\s+team",  # "rival 2's team", "rival2's team"
    r"\brival['\u2019]?s\s+team",         # "rival's team"
    r"\brivalt['\u2019]?s\s+team",        # OCR error: "rivalt's team"
]
```

**Special Cases Handled:**
- **Lance**: Detected as both "Lance's Team" and "Champion's Team" (since Lance is the Champion in Crystal)
- **Rival OCR Error**: Added pattern to catch when OCR misreads "rival" as "rivalt"

### 3. OCR Testing Results

#### Comprehensive Crystal Testing
Tested on **27 Crystal trainer images** with **100% success rate (27/27)**:

**Johto Gym Leaders:**
- ✓ Falkner's Team
- ✓ Bugsy's Team
- ✓ Whitney's Team
- ✓ Morty's Team
- ✓ Chuck's Team
- ✓ Pryce's Team
- ✓ Jasmine's Team
- ✓ Clair's Team

**Kanto Gym Leaders:**
- ✓ Brock's Team
- ✓ Misty's Team
- ✓ Lt. Surge's Team
- ✓ Erika's Team
- ✓ Sabrina's Team
- ✓ Janine's Team
- ✓ Blaine's Team

**Elite Four:**
- ✓ Will's Team
- ✓ Koga's Team
- ✓ Bruno's Team
- ✓ Karen's Team

**Champions & Special:**
- ✓ Lance's Team (also detected as "Champion's Team")
- ✓ Red's Team
- ✓ Blue's Team

**Rival Battles (5 tested):**
- ✓ Rival 1's Team (handled OCR error: "rivalt's team")
- ✓ Rival 2's Team
- ✓ Rival 3's Team
- ✓ Rival 4's Team
- ✓ Rival 5's Team

All three OCR methods (raw PSM 6, raw PSM 7, preprocessed) successfully detected trainer names.

#### Black/White Frame Detection Testing
Tested black/white frame detection on Gen2 example frames with **100% success rate (2/2)**:

**With GameBoy Platform (x=400, y=36, w=1120, h=1008):**
- ✓ Black frame: mean=0.01 (threshold: ≤5) - PERFECT
- ✓ White frame: mean=254.99 (threshold: ≥250) - PERFECT

**Previous GBA Platform (x=360, y=19, w=1200, h=800) - INCORRECT:**
- ✗ Black frame: mean=6.01 - FAILED (above threshold)
- ✗ White frame: mean=238.95 - FAILED (below threshold)

The correct GameBoy gameplay region is essential for accurate black/white frame detection in Gen1/Gen2 games.

## Usage Examples

```bash
# Crystal version
python fury_cutter.py --version crystal your_video.mp4

# Yellow version
python fury_cutter.py --version yellow your_video.mp4

# Red version
python fury_cutter.py --version red your_video.mp4
```

## Notes

1. The OCR region settings are identical for all three versions (Crystal, Yellow, Red) as they share the same emulator layout.

2. All trainers from these games are already mapped in the Premiere Pro label system (`PREMIERE_LABELS`), so automation blocks will work correctly.

3. The pattern matching handles various OCR artifacts and misreadings, making detection robust across different video qualities.

4. The "team" OCR pattern is used (like Gen5), which looks for "[trainer]'s Team" in the header region, rather than the "leader" pattern used by Gen3/Gen4.

## Testing

Created test scripts to verify:
- `test_gen2_ocr.py` - OCR functionality on example images
- `test_new_versions.py` - Configuration correctness
- `test_rival_patterns.py` - Pattern matching logic

All tests pass successfully.

