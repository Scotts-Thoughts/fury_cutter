"""
Premiere Pro Label Automation via Keyboard
==========================================

This script reads the fury_cutter JSON and uses keyboard automation to:
1. Go to each battle's timecode in Premiere Pro
2. Select the clip
3. Apply the label using your keyboard shortcuts

REQUIREMENTS:
- pip install pyautogui pyperclip
- Premiere Pro must be the active window
- Your sequence must be open

YOUR LABEL SHORTCUTS (from your screenshot):
- 1 = Gym
- 2 = Rival  
- 3 = E4
- 4 = Champion
- 5 = Postgame
- 6 = Enemy Leader
- 7 = Cerulean
"""

import json
import time
import sys
from pathlib import Path

try:
    import pyautogui
    import pyperclip
except ImportError:
    print("ERROR: Required packages not installed.")
    print("Run: pip install pyautogui pyperclip")
    sys.exit(1)

# Disable pyautogui fail-safe for smoother automation
# (Move mouse to corner to abort if needed)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # Small delay between actions

# Label to keyboard shortcut mapping (based on your Premiere Pro setup)
LABEL_SHORTCUTS = {
    "Gym": "1",
    "Rival": "2", 
    "E4": "3",
    "Champion": "4",
    "Postgame": "5",
    "Enemy Leader": "6",
    "Cerulean": "7",
    # Add more as needed
    "Enemy Boss": None,  # No shortcut
    "Lavender": None,
    "Brown": None,
}

def seconds_to_timecode(seconds: float, fps: float = 24.0) -> str:
    """Convert seconds to timecode format HH:MM:SS:FF"""
    total_frames = int(seconds * fps)
    frames = total_frames % int(fps)
    total_seconds = int(seconds)
    secs = total_seconds % 60
    mins = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"

def goto_timecode(timecode: str):
    """
    Navigate to a specific timecode in Premiere Pro.
    Uses Ctrl+Shift+G (Go to Time) shortcut.
    """
    # Ctrl+Shift+G opens "Go to Time" dialog
    pyautogui.hotkey('ctrl', 'shift', 'g')
    time.sleep(0.3)
    
    # Clear any existing text and type the timecode
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.05)
    
    # Type the timecode
    pyautogui.typewrite(timecode.replace(':', ''), interval=0.02)
    time.sleep(0.1)
    
    # Press Enter to go to that time
    pyautogui.press('enter')
    time.sleep(0.2)

def select_clip_at_playhead():
    """
    Select the clip at the current playhead position.
    Uses 'D' key (default Premiere shortcut for Select Clip at Playhead).
    """
    pyautogui.press('d')
    time.sleep(0.1)

def apply_label(label_name: str) -> bool:
    """
    Apply a label using the keyboard shortcut.
    Returns True if a shortcut was available and pressed.
    """
    shortcut = LABEL_SHORTCUTS.get(label_name)
    if shortcut:
        pyautogui.press(shortcut)
        time.sleep(0.1)
        return True
    return False

def process_battles(json_path: str, fps: float = 240.0, dry_run: bool = False):
    """
    Process all battles from the JSON file and apply labels.
    
    Args:
        json_path: Path to the _automation_blocks.json file
        fps: Video frame rate (for timecode conversion)
        dry_run: If True, just print what would happen without doing it
    """
    # Load JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    if 'labels' not in data:
        print("ERROR: No 'labels' array found in JSON")
        return
    
    battles = data['labels']
    fps = data.get('fps', fps)
    
    print(f"\n{'='*60}")
    print(f"PREMIERE PRO LABEL AUTOMATION")
    print(f"{'='*60}")
    print(f"JSON File: {json_path}")
    print(f"Battles: {len(battles)}")
    print(f"FPS: {fps}")
    print(f"Dry Run: {dry_run}")
    print(f"{'='*60}\n")
    
    if not dry_run:
        print("Starting in 5 seconds...")
        print("Make sure Premiere Pro is the active window!")
        print("Move mouse to corner to abort.\n")
        for i in range(5, 0, -1):
            print(f"  {i}...")
            time.sleep(1)
        print("Starting!\n")
    
    success_count = 0
    skip_count = 0
    
    for i, battle in enumerate(battles):
        trainer = battle.get('trainer', 'Unknown')
        label = battle.get('label', 'Cerulean')
        start_sec = battle.get('start_seconds', 0)
        
        # Add 0.5 second offset to be well into the clip
        target_sec = start_sec + 0.5
        timecode = seconds_to_timecode(target_sec, fps)
        
        shortcut = LABEL_SHORTCUTS.get(label)
        
        print(f"[{i+1}/{len(battles)}] {trainer}")
        print(f"    Timecode: {timecode} (offset +0.5s)")
        print(f"    Label: {label} -> Key: {shortcut or 'NO SHORTCUT'}")
        
        if dry_run:
            if shortcut:
                print(f"    [DRY RUN] Would apply label\n")
                success_count += 1
            else:
                print(f"    [DRY RUN] Would skip (no shortcut)\n")
                skip_count += 1
            continue
        
        if not shortcut:
            print(f"    SKIPPED: No shortcut for '{label}'\n")
            skip_count += 1
            continue
        
        # Execute the automation
        try:
            # Step 1: Go to timecode
            goto_timecode(timecode)
            
            # Step 2: Select clip at playhead
            select_clip_at_playhead()
            
            # Step 3: Apply label
            apply_label(label)
            
            print(f"    DONE\n")
            success_count += 1
            
            # Small delay between battles
            time.sleep(0.2)
            
        except Exception as e:
            print(f"    ERROR: {e}\n")
    
    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"{'='*60}")
    print(f"Labeled: {success_count}")
    print(f"Skipped: {skip_count}")
    print(f"{'='*60}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Automate Premiere Pro label application using keyboard shortcuts"
    )
    parser.add_argument("json_file", type=str, 
                        help="Path to the _automation_blocks.json file")
    parser.add_argument("--fps", type=float, default=240.0,
                        help="Video frame rate (default: 240)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without doing it")
    
    args = parser.parse_args()
    
    if not Path(args.json_file).exists():
        print(f"ERROR: File not found: {args.json_file}")
        return 1
    
    process_battles(args.json_file, args.fps, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

