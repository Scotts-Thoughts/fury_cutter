# Transition Search Logic Explanation

## Overview

The transition search logic finds black/white frames (cut points) before and after trainer battles. It uses a two-phase approach: OCR-based boundary detection followed by black/white frame search.

## How It Works

### Cut-In (Before Battle) Search

**Function:** `_find_transition_before_fast()`

**Algorithm:**
1. Start at the frame where trainer was detected (`start_frame`)
2. Jump **BACKWARDS** by `TRANSITION_JUMP` frames (default: 720 = 3 seconds at 240fps)
3. At each jump, check if trainer text is still present using OCR
4. When text disappears, we know the boundary is between the last frame with text and current frame
5. Use binary search to narrow down the exact text boundary (reduces OCR calls)
6. Search for black/white frame around the boundary, searching **backwards** from boundary

**Why backwards?** To find the closest transition to the battle. Some games have sequences like: white frame → graphic → black frame → battle. We want the black frame (closest), not the white frame (earlier).

### Cut-Out (After Battle) Search

**Function:** `_find_transition_after_fast()`

**Algorithm:**
1. Start at the frame where trainer was detected (`start_frame`)
2. Jump **FORWARDS** by `TRANSITION_JUMP` frames (default: 720 = 3 seconds at 240fps)
3. At each jump, check if trainer text is still present using OCR
4. When text disappears, we know the boundary is between the last frame with text and current frame
5. Use binary search to narrow down the exact text boundary
6. Search for black/white frame around the boundary, searching **forwards** from boundary
7. If not found in immediate area, extend search up to `JUMP * 2` frames forward

## Potential Issues with Short Battles

### Problem
If `TRANSITION_JUMP` is too large (e.g., 720 frames = 3 seconds) and a battle is very short (e.g., 1-2 seconds), the search might:

1. **Cut-In:** Usually fine because we search backwards from a known detection point
2. **Cut-Out:** Might jump past the battle end in one step, but binary search should still find the boundary

### Current Mitigations

1. **Fallback Search:** If fast search fails, we do a thorough linear search:
   - First: 30 seconds forward with fine steps (5 frames)
   - Then: 2 minutes forward with coarser steps (10 frames)
   - Finally: Use end of video if near the end

2. **Extended Search Window:** The cut-out search extends up to `JUMP * 2` frames (6 seconds) forward if not found immediately

3. **Binary Search Refinement:** Even if we jump past the battle, binary search narrows down the exact boundary where text disappears

## Configuration

- `TRANSITION_JUMP`: Default 720 frames (3 seconds at 240fps)
  - Larger = fewer OCR calls, but might miss very short battles
  - Smaller = more OCR calls, but better for short battles
  - Can be adjusted via `--transition-jump` command line argument

- `EARLY_GAME_INTERVAL`: Default 480 frames (2 seconds at 240fps)
  - More frequent sampling early in video to catch short battles

- `TRAINER_SAMPLE_INTERVAL`: Default 1440 frames (6 seconds at 240fps)
  - Normal sampling interval after early game period

## Recommendations

If you're missing short battles:

1. **Reduce TRANSITION_JUMP:** Try `--transition-jump 480` (2 seconds) or `--transition-jump 240` (1 second)
2. **Reduce sampling intervals:** Use `--early-interval 240` and `--normal-interval 720` for more frequent checks
3. **Check fallback logic:** The fallback should catch most cases, but very short battles (< 1 second) might still be missed

## Example Flow

**Battle detected at frame 10000:**
1. Cut-in search: Jump backwards to 9280, 8560, 7840... until text disappears (say at 8560)
2. Binary search between 8560-9280 to find exact boundary (say 8700)
3. Search for black/white frame between 7980-8700, find at 8500
4. Cut-out search: Jump forwards to 10720, 11440... until text disappears (say at 11440)
5. Binary search between 10000-11440 to find exact boundary (say 11000)
6. Search for black/white frame around 11000, find at 11200

**Result:** Cut-in at 8500, Cut-out at 11200

