#!/usr/bin/env python3
"""
Premiere Pro Label Sender

Sends keyboard shortcuts to Premiere Pro to apply labels to timeline clips.
Works with JSON exported from fury_cutter.py or premiere_apply_labels_simple.jsx.

Usage:
    python premiere_label_sender.py <json_file> [--step]

Options:
    --step    Step through clips one at a time (press Enter for each)

Requirements:
    pip install pyautogui pygetwindow

The script will:
1. Find the Premiere Pro window
2. For each clip in the JSON:
   - Navigate to the clip's timestamp
   - Send Shift+3 to focus timeline
   - Send 'D' to select clip at playhead
   - Send the label keyboard shortcut
"""

import json
import sys
import time
import argparse
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("ERROR: pyautogui not installed.")
    print("Run: pip install pyautogui")
    sys.exit(1)

try:
    import pygetwindow as gw
except ImportError:
    gw = None
    print("WARNING: pygetwindow not installed. Window focus will be manual.")
    print("Install with: pip install pygetwindow")


# ============================================================================
# CONFIGURATION - Adjust these to match YOUR Premiere Pro keyboard shortcuts
# ============================================================================

# Shortcut to go to a specific timecode (varies by Premiere version/layout)
# Common options:
#   - Ctrl+G: "Go to Time" in some setups
#   - Ctrl+Shift+J: "Go to Sequence Marker" 
#   - Just click timeline and type timecode
GO_TO_TIME_SHORTCUT = None  # Set to None to skip navigation (JSX handles it)

# Shortcut to focus the timeline panel
FOCUS_TIMELINE_SHORTCUT = ('shift', '3')

# Shortcut to select clip at playhead
SELECT_AT_PLAYHEAD_SHORTCUT = 'd'  # Default Premiere shortcut

# Map label names to keyboard shortcuts
# Adjust these to match your Premiere Pro keyboard shortcut assignments
# Format: "Label Name": ('modifier1', 'modifier2', 'key')
LABEL_SHORTCUTS = {
    # Primary battle types - using Ctrl+Shift+Number
    "Rival":        ('ctrl', 'shift', '1'),
    "Gym":          ('ctrl', 'shift', '2'),
    "E4":           ('ctrl', 'shift', '3'),
    "Champion":     ('ctrl', 'shift', '4'),
    "Postgame":     ('ctrl', 'shift', '5'),
    "Enemy Leader": ('ctrl', 'shift', '6'),
    "Enemy Boss":   ('ctrl', 'shift', '7'),
    
    # Default/fallback colors
    "Cerulean":     ('ctrl', 'shift', '8'),
    "Caribbean":    ('ctrl', 'shift', '9'),
    "Lavender":     ('ctrl', 'shift', '0'),
    
    # Additional labels using F-keys
    "Magenta":      ('ctrl', 'shift', 'f1'),
    "Purple":       ('ctrl', 'shift', 'f2'),
    "Blue":         ('ctrl', 'shift', 'f3'),
    "Green":        ('ctrl', 'shift', 'f4'),
    "Yellow":       ('ctrl', 'shift', 'f5'),
    "Brown":        ('ctrl', 'shift', 'f6'),
}

# Timing delays (seconds)
KEY_DELAY = 0.05       # Between key presses in a hotkey
STEP_DELAY = 0.15      # Between steps in the workflow
CLIP_DELAY = 0.3       # Between processing clips


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_sendkeys(shortcut: str) -> tuple:
    """Convert SendKeys format (^+1) to pyautogui format ('ctrl', 'shift', '1')."""
    modifiers = []
    keys = []
    
    i = 0
    while i < len(shortcut):
        char = shortcut[i]
        
        if char == '^':
            modifiers.append('ctrl')
        elif char == '+':
            modifiers.append('shift')
        elif char == '%':
            modifiers.append('alt')
        elif char == '{':
            # Special key like {F1}
            end = shortcut.find('}', i)
            if end != -1:
                key_name = shortcut[i+1:end].lower()
                keys.append(key_name)
                i = end
        else:
            keys.append(char.lower() if char.isalpha() else char)
        
        i += 1
    
    return tuple(modifiers + keys)


def focus_premiere() -> bool:
    """Try to focus the Premiere Pro window."""
    if gw is None:
        return False
    
    try:
        windows = gw.getWindowsWithTitle('Adobe Premiere Pro')
        if windows:
            win = windows[0]
            win.activate()
            time.sleep(0.3)
            return True
    except Exception as e:
        print(f"  Could not focus Premiere Pro: {e}")
    
    return False


def focus_timeline():
    """Send Shift+3 to focus the timeline panel."""
    pyautogui.hotkey(*FOCUS_TIMELINE_SHORTCUT, interval=KEY_DELAY)
    time.sleep(STEP_DELAY)


def select_clip_at_playhead():
    """Press D to select clip at playhead."""
    pyautogui.press(SELECT_AT_PLAYHEAD_SHORTCUT)
    time.sleep(STEP_DELAY)


def send_label_shortcut(label: str) -> bool:
    """Send the keyboard shortcut for a label."""
    # First check our predefined shortcuts
    shortcut = LABEL_SHORTCUTS.get(label)
    
    # Case-insensitive fallback
    if not shortcut:
        for key, value in LABEL_SHORTCUTS.items():
            if key.lower() == label.lower():
                shortcut = value
                break
    
    if not shortcut:
        return False
    
    pyautogui.hotkey(*shortcut, interval=KEY_DELAY)
    time.sleep(STEP_DELAY)
    return True


def load_json(json_path: Path) -> list[dict]:
    """Load clips from JSON file, supporting multiple formats."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    clips = []
    
    # Format 1: Automation Blocks format { "labels": [...] }
    if isinstance(data, dict) and 'labels' in data:
        for entry in data['labels']:
            clips.append({
                'start_seconds': entry.get('start_seconds', 0),
                'label': entry.get('label', 'Cerulean'),
                'trainer': entry.get('trainer', 'Unknown'),
            })
        return clips
    
    # Format 2: Premiere label sender export { "clips": [...] }
    if isinstance(data, dict) and 'clips' in data:
        for entry in data['clips']:
            # Handle SendKeys format shortcuts
            shortcut_str = entry.get('shortcut', '')
            if shortcut_str and isinstance(shortcut_str, str):
                # Store parsed shortcut for later
                entry['_parsed_shortcut'] = parse_sendkeys(shortcut_str)
            clips.append({
                'start_seconds': entry.get('start_seconds', 0),
                'label': entry.get('label', 'Cerulean'),
                'trainer': entry.get('trainer', 'Unknown'),
                '_parsed_shortcut': entry.get('_parsed_shortcut'),
            })
        return clips
    
    # Format 3: Timebolt format (flat array)
    if isinstance(data, list):
        for entry in data:
            if entry.get('label'):  # Only include segments with labels
                clips.append({
                    'start_seconds': entry.get('start', 0),
                    'label': entry.get('label', 'Cerulean'),
                    'trainer': entry.get('name', 'Unknown'),
                })
        return clips
    
    return clips


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Send label keyboard shortcuts to Premiere Pro',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python premiere_label_sender.py video_automation_blocks.json
    python premiere_label_sender.py video_premiere_labels.json --step

Setup:
    1. In Premiere Pro, go to Edit > Keyboard Shortcuts
    2. Search for "label" and assign shortcuts:
       Ctrl+Shift+1 = Edit > Label > [Rival color]
       Ctrl+Shift+2 = Edit > Label > [Gym color]
       etc.
    3. Run fury_cutter.py to generate the JSON file
    4. Open your sequence in Premiere Pro
    5. Run this script
        """)
    
    parser.add_argument('json_file', type=Path, help='JSON file with label data')
    parser.add_argument('--step', action='store_true', 
                        help='Step through clips one at a time')
    parser.add_argument('--delay', type=float, default=CLIP_DELAY,
                        help=f'Delay between clips in seconds (default: {CLIP_DELAY})')
    parser.add_argument('--skip-navigation', action='store_true',
                        help='Skip navigation, only send label shortcuts (use with JSX script)')
    
    args = parser.parse_args()
    
    if not args.json_file.exists():
        print(f"ERROR: File not found: {args.json_file}")
        return 1
    
    # Load clips
    clips = load_json(args.json_file)
    
    if not clips:
        print("No clips with labels found in JSON file.")
        return 1
    
    print()
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║          PREMIERE PRO LABEL SENDER                             ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    print(f"  Loaded: {len(clips)} clips from {args.json_file.name}")
    print()
    
    # Show summary by label type
    label_counts = {}
    for clip in clips:
        label = clip.get('label', 'Unknown')
        label_counts[label] = label_counts.get(label, 0) + 1
    
    print("  Labels to apply:")
    for label, count in sorted(label_counts.items()):
        shortcut = LABEL_SHORTCUTS.get(label, ('?',))
        shortcut_str = '+'.join(str(k).upper() for k in shortcut)
        print(f"    {label:15} : {count:3} clips  ({shortcut_str})")
    
    print()
    print("─" * 68)
    print()
    print("  REQUIRED SETUP:")
    print("  ───────────────")
    print("  1. Open your sequence in Premiere Pro")
    print("  2. Ensure keyboard shortcuts are assigned in Edit > Keyboard Shortcuts")
    print("  3. The JSX script should have positioned clips (or use --skip-navigation)")
    print()
    print("  HOW IT WORKS:")
    print("  ─────────────")
    print("  For each clip, this script will:")
    print("    • Press Shift+3 to focus the timeline")
    print("    • Press D to select clip at playhead")
    print("    • Press the label shortcut (e.g., Ctrl+Shift+1)")
    print()
    print("  ABORT: Move mouse to the top-left corner of screen")
    print()
    print("─" * 68)
    print()
    
    # Try to focus Premiere
    print("  Looking for Premiere Pro window...")
    if focus_premiere():
        print("  ✓ Found and focused Premiere Pro")
    else:
        print("  ! Could not auto-focus Premiere Pro")
        print("    Please click on the Premiere Pro window now")
    
    print()
    
    if args.step:
        input("  Press ENTER to start (step-by-step mode)...")
    else:
        input("  Press ENTER to start...")
    
    print()
    print("  Starting in 3...")
    time.sleep(1)
    print("  Starting in 2...")
    time.sleep(1)
    print("  Starting in 1...")
    time.sleep(1)
    print()
    
    # Safety settings
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.02
    
    success_count = 0
    fail_count = 0
    
    for i, clip in enumerate(clips):
        trainer = clip.get('trainer', 'Unknown')
        label = clip.get('label', 'Unknown')
        start = clip.get('start_seconds', 0)
        
        progress = f"[{i+1:3}/{len(clips)}]"
        print(f"  {progress} {trainer:20} → {label:15}", end=" ")
        
        try:
            # Step 1: Focus timeline
            focus_timeline()
            
            # Step 2: Select clip at playhead (if JSX already positioned us)
            if not args.skip_navigation:
                select_clip_at_playhead()
            
            # Step 3: Send label shortcut
            # Check if we have a pre-parsed shortcut from the JSON
            parsed = clip.get('_parsed_shortcut')
            if parsed:
                pyautogui.hotkey(*parsed, interval=KEY_DELAY)
                time.sleep(STEP_DELAY)
                sent = True
            else:
                sent = send_label_shortcut(label)
            
            if sent:
                print("✓")
                success_count += 1
            else:
                print("✗ (no shortcut for this label)")
                fail_count += 1
            
        except pyautogui.FailSafeException:
            print()
            print()
            print("  ⚠ ABORTED: Mouse moved to corner (failsafe triggered)")
            break
        except Exception as e:
            print(f"✗ ({e})")
            fail_count += 1
        
        if args.step:
            try:
                input("  Press ENTER for next clip...")
            except KeyboardInterrupt:
                print("\n  Cancelled.")
                break
        else:
            time.sleep(args.delay)
    
    print()
    print("─" * 68)
    print()
    print("  COMPLETE")
    print(f"    Success: {success_count}")
    print(f"    Failed:  {fail_count}")
    print()
    print("─" * 68)
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
