"""
Template Extractor for Fury Cutter

Extracts header text templates from battle screenshots for template matching.
This is ~100-350x faster than OCR for trainer detection.

Usage:
    python extract_templates.py

Reads screenshots from template_matching/{game}/ folders,
crops the header/title region, converts to grayscale, and saves
processed templates to templates/{game}/{template_name}.png.

Each game folder also gets a metadata.json mapping template filenames
to canonical trainer names used by fury_cutter.
"""

import cv2
import numpy as np
from pathlib import Path
import re
import json
import sys


# Template crop regions per game - matches the title bar position in the overlay
# (x, y, width, height) - defines the header text region to crop from each screenshot
TEMPLATE_CROP_REGIONS = {
    "black": (1508, 22, 374, 36),        # Gen5: "Cheren's Team" style
    "platinum": (1490, 20, 400, 35),     # Gen4 Platinum: "Leader Roark" style
    "heartgold": (1460, 28, 460, 46),    # Gen4 HGSS: "Leader Falkner" (right panel header)
    "emerald": (1584, 25, 322, 31),      # Gen3 RSE: "Leader Roxanne" style
    "firered": (1584, 25, 322, 31),      # Gen3 FRLG: "Leader Brock" style
    "crystal": (1548, 40, 355, 34),      # Gen2: "Falkner's Team" style
    "yellow": (1548, 40, 355, 34),       # Gen1: "[Name]'s Team" style
    "red": (1548, 40, 355, 34),          # Gen1: "[Name]'s Team" style
}


def filename_to_trainer(filename: str, game_key: str) -> str:
    """
    Map a screenshot filename to a canonical trainer name.
    
    These canonical names must match the trainer names in GAME_CONFIGS
    in fury_cutter.py so that template matches map correctly.
    """
    name = filename.lower().strip()
    
    # Rival variants (rival1, rival2, rival3, etc.)
    if re.match(r'^rival\s*\d+$', name):
        return "rival"
    
    # Rival Silver (heartgold)
    if name == "rival silver":
        return "silver"
    
    # Brendan is the rival in Gen3 RSE
    if name == "brendan" and game_key in ["emerald", "ruby", "sapphire"]:
        return "rival"
    
    # Kimono girl variants (kimono girl sayo, kimono girl kuni, etc.)
    if name.startswith("kimono girl"):
        return "kimono girl"
    
    # Team Galactic members with encounter numbers (mars_1, cyrus1, cyrus2, etc.)
    for galactic in ["mars", "jupiter", "saturn", "cyrus"]:
        if re.match(rf'^{galactic}[_\s]*\d*$', name):
            return galactic
    
    # Champion variants (champion, champion terry 4, champion terry 5, etc.)
    if name.startswith("champion"):
        return "champion"
    
    # Elite Four rematches (agatha2, bruno2, lorelei2, lance2)
    match = re.match(r'^(agatha|bruno|lorelei|lance)(\d+)$', name)
    if match:
        return match.group(1)
    
    # Alternate spellings
    if name == "brawley":
        return "brawly"
    
    # Default: filename is the trainer name
    return name


def extract_templates():
    """Extract and save templates from screenshot files."""
    base_dir = Path(__file__).parent
    template_matching_dir = base_dir / "template_matching"
    output_dir = base_dir / "templates"
    
    if not template_matching_dir.exists():
        print(f"Error: template_matching/ directory not found at {template_matching_dir}")
        return 1
    
    total_templates = 0
    
    for game_dir in sorted(template_matching_dir.iterdir()):
        if not game_dir.is_dir():
            continue
        
        game_key = game_dir.name.lower()
        if game_key not in TEMPLATE_CROP_REGIONS:
            print(f"Skipping {game_key}/ (no crop region defined)")
            continue
        
        # Check if folder has any images
        jpg_files = sorted(game_dir.glob("*.jpg"))
        if not jpg_files:
            print(f"Skipping {game_key}/ (no .jpg files)")
            continue
        
        x, y, w, h = TEMPLATE_CROP_REGIONS[game_key]
        
        # Create output directory
        game_output = output_dir / game_key
        game_output.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{game_key}/ (crop: x={x}, y={y}, w={w}, h={h})")
        
        game_metadata = {}
        game_count = 0
        
        for img_file in jpg_files:
            # Read the full screenshot
            img = cv2.imread(str(img_file))
            if img is None:
                print(f"  WARNING: Could not read {img_file.name}")
                continue
            
            img_h, img_w = img.shape[:2]
            
            # Verify image dimensions
            if img_w < x + w or img_h < y + h:
                print(f"  WARNING: {img_file.name} too small ({img_w}x{img_h}), "
                      f"need at least {x+w}x{y+h}")
                continue
            
            # Crop the title region
            crop = img[y:y+h, x:x+w]
            
            # Convert to grayscale
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            
            # Save template (use underscores for spaces in filename)
            template_name = img_file.stem.lower().replace(" ", "_")
            output_path = game_output / f"{template_name}.png"
            cv2.imwrite(str(output_path), gray)
            
            # Map to canonical trainer name
            trainer_name = filename_to_trainer(img_file.stem, game_key)
            game_metadata[template_name] = trainer_name
            
            print(f"  {img_file.name:40s} -> {template_name}.png  (trainer: {trainer_name})")
            game_count += 1
        
        # Save metadata mapping template names to trainer names
        metadata_path = game_output / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(game_metadata, f, indent=2)
        
        total_templates += game_count
        print(f"  => {game_count} templates saved")
    
    print(f"\n{'='*60}")
    print(f"Total: {total_templates} templates extracted")
    print(f"Templates saved to: {output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(extract_templates())

