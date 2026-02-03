"""
Fury Cutter - Video Analysis Tool for Pokemon Game Editing
Detects black frames, white frames, and trainer battles for automated video cuts.
"""

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import argparse
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Thread, Lock
import os
import json
import re
from PIL import Image

# OCR setup
try:
    import pytesseract
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: pytesseract not installed. Trainer detection disabled.")


# Premiere Pro label mapping for Automation Blocks
# Maps trainer types to Premiere Pro label names (matching your keyboard shortcuts)
# These match the custom label names from your Premiere Pro setup:
#   Rival (2), Gym (1), E4 (3), Champion (4), Postgame (5), Enemy Leader (6), Cerulean (7)
PREMIERE_LABELS = {
    # Rival battles -> "Rival" label (key 2)
    "rival": "Rival",
    
    # Gym Leaders -> "Gym" label (key 1)
    # Gen 4 Platinum
    "roark": "Gym", "gardenia": "Gym", "fantina": "Gym", "maylene": "Gym",
    "wake": "Gym", "byron": "Gym", "candice": "Gym", "volkner": "Gym",
    # Gen 4 HGSS
    "falkner": "Gym", "bugsy": "Gym", "whitney": "Gym", "morty": "Gym",
    "chuck": "Gym", "jasmine": "Gym", "pryce": "Gym", "clair": "Gym",
    "brock": "Gym", "misty": "Gym", "lt. surge": "Gym", "surge": "Gym",
    "erika": "Gym", "sabrina": "Gym", "blaine": "Gym", "janine": "Gym",
    # Gen 3 RSE
    "roxanne": "Gym", "brawly": "Gym", "wattson": "Gym", "flannery": "Gym",
    "norman": "Gym", "winona": "Gym", "tate & liza": "Gym", "tate and liza": "Gym", "juan": "Gym",
    # Gen 3 FRLG
    "giovanni": "Gym", "koga": "Gym",
    # Gen 5
    "cress": "Gym", "chili": "Gym", "cilan": "Gym", "lenora": "Gym",
    "burgh": "Gym", "elesa": "Gym", "clay": "Gym", "skyla": "Gym",
    "brycen": "Gym", "drayden": "Gym",
    
    # Elite Four -> "E4" label (key 3)
    "aaron": "E4", "bertha": "E4", "flint": "E4", "lucian": "E4",
    "will": "E4", "bruno": "E4", "karen": "E4",
    "sidney": "E4", "phoebe": "E4", "glacia": "E4", "drake": "E4",
    "lorelei": "E4", "agatha": "E4", "lance": "E4",
    "shauntal": "E4", "marshall": "E4", "grimsley": "E4", "caitlin": "E4",
    
    # Champion -> "Champion" label (key 4)
    "cynthia": "Champion", "red": "Champion", "steven": "Champion", "wallace": "Champion", "champion": "Champion",
    "blue": "Champion",  # Blue as Champion in HGSS
    
    # Evil Team Leaders -> "Enemy Leader" label (key 6)
    "mars": "Enemy Leader", "jupiter": "Enemy Leader", "saturn": "Enemy Leader", "cyrus": "Enemy Leader",
    "maxie": "Enemy Leader", "archie": "Enemy Leader",
    "ghetsis": "Enemy Leader",
    
    # Story trainers (Bianca, Cheren, N, Wally) -> "Cerulean" label (key 7)
    "bianca": "Cerulean", "cheren": "Cerulean", "n": "Enemy Boss", "wally": "Cerulean",
    
    # Special trainers
    "kimono girl": "Cerulean",  # Kimono Girls in HGSS
    "lance": "Champion",  # Lance as Champion in HGSS
}


class Platform(Enum):
    """Supported gaming platforms with different screen layouts."""
    NINTENDO_DS = "nds"
    NINTENDO_GBA = "gba"


class Generation(Enum):
    """Pokemon game generations."""
    GEN3 = 3
    GEN4 = 4
    GEN5 = 5


@dataclass
class Region:
    """Defines a rectangular region within the video frame."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class GameConfig:
    """Configuration for a specific Pokemon game."""
    name: str
    generation: Generation
    platform: Platform
    trainers: list[str]
    # OCR pattern type: "team" for "[name]'s team", "leader" for "Leader [name]", "name_only" for just the name
    ocr_pattern: str = "team"
    # OCR region for trainer overlay text
    ocr_region: Region = None
    # Gameplay region for black/white detection
    gameplay_region: Region = None
    
    def __post_init__(self):
        # Default regions for Nintendo DS
        if self.gameplay_region is None:
            self.gameplay_region = Region(x=448, y=19, width=1024, height=768)
        if self.ocr_region is None:
            self.ocr_region = Region(x=1100, y=20, width=820, height=90)


# Game configurations
GAME_CONFIGS = {
    # Generation 5
    "black": GameConfig(
        name="Pokemon Black",
        generation=Generation.GEN5,
        platform=Platform.NINTENDO_DS,
        ocr_pattern="team",  # "[trainer]'s Team"
        trainers=[
            "n", "cheren", "bianca", "cress", "chili", "cilan",
            "lenora", "burgh", "elesa", "clay", "skyla", "brycen",
            "drayden", "shauntal", "marshall", "grimsley", "caitlin", "ghetsis"
        ]
    ),
    
    # Generation 4
    # Gen4 header shows "Leader [Name]" or "Rival #" in header bar
    # TIGHT crop (1490, 20, 400, 35) avoids decorative borders that confuse OCR
    "platinum": GameConfig(
        name="Pokemon Platinum",
        generation=Generation.GEN4,
        platform=Platform.NINTENDO_DS,
        ocr_pattern="leader",  # "Leader [name]" or "Rival #"
        ocr_region=Region(x=1490, y=20, width=400, height=35),
        trainers=[
            "rival", "roark", "gardenia", "fantina", "maylene", "wake",
            "byron", "candice", "volkner", "aaron", "bertha", "flint",
            "lucian", "cynthia", "mars", "jupiter", "saturn", "cyrus"
        ]
    ),
    
    "heartgold": GameConfig(
        name="Pokemon HeartGold",
        generation=Generation.GEN4,
        platform=Platform.NINTENDO_DS,
        ocr_pattern="leader",  # "Leader [name]" or "Rival #" or "Elite Four [name]"
        ocr_region=Region(x=1490, y=20, width=400, height=35),
        trainers=[
            "rival", "falkner", "bugsy", "whitney", "morty", "chuck",
            "jasmine", "pryce", "clair", "will", "koga", "bruno",
            "karen", "lance", "brock", "misty", "lt. surge", "erika",
            "sabrina", "blaine", "janine", "blue", "red", "silver",
            "kimono girl"
        ]
    ),
    
    # Generation 3 - Ruby/Sapphire/Emerald
    # GBA games with different screen layout
    # Gameplay: center (960, 419), size 1200x800 -> top-left (360, 19)
    # OCR region: x=1584, y=25, w=322, h=31 (tight crop of header text)
    "emerald": GameConfig(
        name="Pokemon Emerald",
        generation=Generation.GEN3,
        platform=Platform.NINTENDO_GBA,
        ocr_pattern="leader",  # "Leader [name]", "Rival #", "Elite Four [name]"
        ocr_region=Region(x=1584, y=25, width=322, height=31),
        gameplay_region=Region(x=360, y=19, width=1200, height=800),
        trainers=[
            "rival", "roxanne", "brawly", "wattson", "flannery", "norman",
            "winona", "tate & liza", "tate and liza", "juan", "wally",
            "maxie", "archie", "sidney", "phoebe", "glacia", "drake",
            "wallace", "steven"
        ]
    ),
    
    "ruby": GameConfig(
        name="Pokemon Ruby",
        generation=Generation.GEN3,
        platform=Platform.NINTENDO_GBA,
        ocr_pattern="leader",
        ocr_region=Region(x=1584, y=25, width=322, height=31),
        gameplay_region=Region(x=360, y=19, width=1200, height=800),
        trainers=[
            "rival", "roxanne", "brawly", "wattson", "flannery", "norman",
            "winona", "tate & liza", "tate and liza", "juan", "wally",
            "maxie", "archie", "sidney", "phoebe", "glacia", "drake",
            "wallace", "steven"
        ]
    ),
    
    "sapphire": GameConfig(
        name="Pokemon Sapphire",
        generation=Generation.GEN3,
        platform=Platform.NINTENDO_GBA,
        ocr_pattern="leader",
        ocr_region=Region(x=1584, y=25, width=322, height=31),
        gameplay_region=Region(x=360, y=19, width=1200, height=800),
        trainers=[
            "rival", "roxanne", "brawly", "wattson", "flannery", "norman",
            "winona", "tate & liza", "tate and liza", "juan", "wally",
            "maxie", "archie", "sidney", "phoebe", "glacia", "drake",
            "wallace", "steven"
        ]
    ),
    
    # Generation 3 - FireRed/LeafGreen
    "firered": GameConfig(
        name="Pokemon FireRed",
        generation=Generation.GEN3,
        platform=Platform.NINTENDO_GBA,
        ocr_pattern="leader",  # "Leader [name]", "Rival #", "Elite Four [name]", "Champion"
        ocr_region=Region(x=1584, y=25, width=322, height=31),
        gameplay_region=Region(x=360, y=19, width=1200, height=800),
        trainers=[
            "brock", "misty", "lt. surge", "surge", "erika", "koga",
            "sabrina", "blaine", "giovanni", "rival", "lorelei", "bruno",
            "agatha", "lance", "champion"
        ]
    ),
    
    "leafgreen": GameConfig(
        name="Pokemon LeafGreen",
        generation=Generation.GEN3,
        platform=Platform.NINTENDO_GBA,
        ocr_pattern="leader",
        ocr_region=Region(x=1584, y=25, width=322, height=31),
        gameplay_region=Region(x=360, y=19, width=1200, height=800),
        trainers=[
            "brock", "misty", "lt. surge", "surge", "erika", "koga",
            "sabrina", "blaine", "giovanni", "rival", "lorelei", "bruno",
            "agatha", "lance", "champion"
        ]
    ),
}

# Legacy platform configs (for backwards compatibility)
PLATFORM_CONFIGS = {
    Platform.NINTENDO_DS: {
        "gameplay": Region(x=448, y=19, width=1024, height=768),
        "ocr_region": Region(x=1100, y=20, width=820, height=90),
    }
}


@dataclass
class Detection:
    """Represents a detected event in the video."""
    frame_number: int
    timestamp: float
    detection_type: str
    details: Optional[str] = None
    
    def __str__(self) -> str:
        return f"[Frame {self.frame_number:>8}] ({self.timestamp:>10.4f}s) {self.detection_type}: {self.details or ''}"


@dataclass 
class BattleSequence:
    """Represents a complete trainer battle with in/out cut points."""
    trainer_name: str
    battle_start_frame: int  # First frame where trainer is detected
    battle_end_frame: int    # Last frame where trainer is detected
    cut_in_frame: int        # Black/white frame BEFORE battle (edit point)
    cut_out_frame: int       # Black/white frame AFTER battle (edit point)
    cut_in_timestamp: float
    cut_out_timestamp: float
    
    def __str__(self) -> str:
        return (f"BATTLE: {self.trainer_name}\n"
                f"  Cut IN:  Frame {self.cut_in_frame:>8} ({self.cut_in_timestamp:>10.4f}s)\n"
                f"  Cut OUT: Frame {self.cut_out_frame:>8} ({self.cut_out_timestamp:>10.4f}s)\n"
                f"  Duration: {self.cut_out_timestamp - self.cut_in_timestamp:.2f}s")


class VideoProcessor:
    """Processes video files to detect edit points with multithreaded analysis."""
    
    BLACK_MEAN_THRESHOLD = 5   # Stricter - true black frames have mean ~0
    WHITE_MEAN_THRESHOLD = 250  # Stricter - true white frames have mean ~255
    TRAINER_SAMPLE_INTERVAL = 960  # Check for trainer every N frames (6 sec at 240fps)
    
    # Performance tuning for transition search
    # Larger jumps = fewer OCR calls, but wider search window for black/white detection
    TRANSITION_JUMP = 240  # 3 seconds at 240fps (was 240 = 1 sec)
    
    # Adaptive sampling for early-game short battles
    EARLY_GAME_INTERVAL = 240   # Check every 2 seconds for first 10 minutes
    EARLY_GAME_THRESHOLD = 43200  # First 10 min at 240fps
    
    def __init__(self, video_path: Path, game_config: GameConfig,
                 downscale_factor: float = 0.25,
                 num_workers: int = None,
                 debug_ocr: bool = False,
                 transition_jump: int = None,
                 early_interval: int = None,
                 normal_interval: int = None):
        self.video_path = video_path
        self.game_config = game_config
        self.platform = game_config.platform
        self.downscale_factor = downscale_factor
        self.num_workers = num_workers or max(1, os.cpu_count() - 1)
        self.debug_ocr = debug_ocr
        
        # Override class defaults if custom values provided
        if transition_jump is not None:
            self.TRANSITION_JUMP = transition_jump
        if early_interval is not None:
            self.EARLY_GAME_INTERVAL = early_interval
        if normal_interval is not None:
            self.TRAINER_SAMPLE_INTERVAL = normal_interval
        
        # OCR cache to avoid duplicate calls on the same frame
        # Key: frame_num, Value: OCR text result
        self._ocr_cache: dict[int, str] = {}
        self._ocr_cache_lock = Lock()
        
        # Build config dict for backwards compatibility
        self.config = {
            "gameplay": game_config.gameplay_region,
            "ocr_region": game_config.ocr_region,
        }
        
        # Get video properties
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
            
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        print(f"Video: {video_path.name}")
        print(f"  Resolution: {self.width}x{self.height}")
        print(f"  FPS: {self.fps}")
        print(f"  Total Frames: {self.total_frames}")
        print(f"  Duration: {self.total_frames / self.fps:.2f}s")
        print(f"  Worker threads: {self.num_workers}")
        print(f"  OCR available: {OCR_AVAILABLE}")
    
    def _analyze_frame_range(self, start_frame: int, end_frame: int, 
                             detect_trainers: list[str] = None) -> list[dict]:
        """Analyze a range of frames. Returns list of frame analysis results."""
        cap = cv2.VideoCapture(str(self.video_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        gameplay = self.config["gameplay"]
        trainer_header = self.config["trainer_header"]
        results = []
        
        for frame_num in range(start_frame, end_frame):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Analyze gameplay region for black/white
            gp_crop = frame[
                gameplay.y : gameplay.y + gameplay.height,
                gameplay.x : gameplay.x + gameplay.width
            ]
            
            # Downscale for faster mean calculation
            if self.downscale_factor < 1.0:
                gp_small = cv2.resize(gp_crop, None, 
                                      fx=self.downscale_factor, 
                                      fy=self.downscale_factor,
                                      interpolation=cv2.INTER_AREA)
            else:
                gp_small = gp_crop
            
            gray = cv2.cvtColor(gp_small, cv2.COLOR_BGR2GRAY)
            mean_value = gray.mean()
            
            is_black = mean_value <= self.BLACK_MEAN_THRESHOLD
            is_white = mean_value >= self.WHITE_MEAN_THRESHOLD
            
            # Check for trainer presence
            trainer_detected = None
            if detect_trainers:
                header_crop = frame[
                    trainer_header.y : trainer_header.y + trainer_header.height,
                    trainer_header.x : trainer_header.x + trainer_header.width
                ]
                
                for trainer_name in detect_trainers:
                    if trainer_name in self.trainer_templates:
                        template = self.trainer_templates[trainer_name]
                        # Resize template if needed to fit header region
                        if template.shape[0] > header_crop.shape[0] or template.shape[1] > header_crop.shape[1]:
                            continue
                        
                        result = cv2.matchTemplate(header_crop, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(result)
                        
                        if max_val >= self.TRAINER_MATCH_THRESHOLD:
                            trainer_detected = trainer_name
                            break
            
            results.append({
                "frame": frame_num,
                "mean": mean_value,
                "is_black": is_black,
                "is_white": is_white,
                "trainer": trainer_detected
            })
        
        cap.release()
        return results
    
    def _text_contains_trainer_pattern(self, text: str, trainer_name: str) -> bool:
        """Quick check if text contains trainer-like patterns."""
        trainer_lower = trainer_name.lower()
        ocr_pattern = self.game_config.ocr_pattern
        
        if ocr_pattern == "team":
            # Use word boundary to avoid matching "rolan's team" or "warren's team" as "n's team"
            # \b ensures the trainer name starts at a word boundary (not preceded by a letter)
            pattern = rf"\b{re.escape(trainer_lower)}['']?s\s+team"
            return bool(re.search(pattern, text))
        elif ocr_pattern == "leader":
            if trainer_lower == "rival":
                # Match various OCR misreadings of "Rival #"
                # OCR commonly mangles "Rival" into: rvari, kvai, rvar, ival, eva, etc.
                # Also handle tan/brown theme which produces different artifacts
                rival_patterns = [
                    r'rival\s*\d+',       # correct: "rival 1", "rival2"
                    r'rival[1-9]',        # compact: "rival1", "rival2"
                    r'rivals\b',          # OCR sometimes reads "rivals" (no digit)
                    r'riva[il1]\s*\d+',   # misread: "rivai 1", "rival1"
                    r'rivar',             # misread: "rivar" (without digit)
                    r'rvari',             # misread: "rvari" (OCR garble)
                    r'kvai\s*\d*',        # misread: "kvai2" 
                    r'rvar',              # partial: "rvar"
                    r'[rk]va[il1r]\s*\d*', # flexible: rval, kval, rvai, kvai + optional digit
                    r'iva[il1]?\s*\d+',   # misread: "ival 1", "iva 2"
                    r'rva[il1]\s*\d*',    # misread: "rvai", "rval" (tan theme artifacts)
                ]
                for pattern in rival_patterns:
                    if re.search(pattern, text):
                        return True
                return False
            elif trainer_lower in ["tate & liza", "tate and liza"]:
                # Special case: double battle gym leaders
                return "tate" in text and "liza" in text
            elif trainer_lower == "lt. surge" or trainer_lower == "surge":
                # Handle Lt. Surge variations
                return "surge" in text
            elif trainer_lower == "silver":
                # Clean text first
                cleaned_text = text.strip('"\'`.,;:!?').strip('"\'')
                # Rival Silver - match "rival silver" or just "silver" in context
                if "rival" in cleaned_text and "silver" in cleaned_text:
                    return True
                # Also match just "silver" as standalone word (but not "silver" in other contexts)
                if re.search(r'\bsilver\b', cleaned_text):
                    return True
                return False
            elif trainer_lower == "kimono girl":
                # Clean text first
                cleaned_text = text.strip('"\'`.,;:!?').strip('"\'')
                # Kimono Girl - match any text containing "kimono girl" regardless of name that follows
                # Pattern: "kimono girl" followed by optional name (e.g., "kimono girl sayo")
                if re.search(r'\bkimono\s+girl\b', cleaned_text, re.IGNORECASE):
                    return True
                return False
            elif trainer_lower == "misty":
                # Clean text first
                cleaned_text = text.strip('"\'`.,;:!?').strip('"\'')
                # Handle OCR errors: "misty" sometimes reads as "mistu", "misty", etc.
                misty_patterns = [r'leader\s*misty', r'leader\s*mistu', r'leader\s*mist[yui]', r'\bmisty\b', r'\bmistu\b']
                for pattern in misty_patterns:
                    if re.search(pattern, cleaned_text, re.IGNORECASE):
                        return True
                return False
            elif trainer_lower == "janine":
                # Clean text first
                cleaned_text = text.strip('"\'`.,;:!?').strip('"\'')
                # Handle OCR errors: "leader" sometimes reads as "deader", "1eader", etc.
                janine_patterns = [
                    r'leader\s*janine',
                    r'[ld]eader\s*janine',  # "deader" OCR error
                    r'[il1]eader\s*janine',  # "1eader" OCR error
                    r'\bjanine\b'
                ]
                for pattern in janine_patterns:
                    if re.search(pattern, cleaned_text, re.IGNORECASE):
                        return True
                return False
            elif trainer_lower == "bruno":
                # Clean text first
                cleaned_text = text.strip('"\'`.,;:!?').strip('"\'')
                # Handle OCR errors for Elite Four Bruno:
                # "elite" -> "lite", "slite", "elite"
                # "four" -> "four"
                # "bruno" -> "bruno", "brunco", "brunc0", "bruanco", "brun0"
                bruno_patterns = [
                    r'(?:elite|[s\']?lite)\s*four\s*bru[an]?[cn][co0]?o?',  # "elite four bruno", "lite four brunco", "lite four bruanco"
                    r'elite\s+bru[an]?[cn][co0]?o?',  # "elite bruno"
                    r'\bbru[an]?[cn][co0]?o?\b',  # just "bruno", "brunco", "bruanco"
                ]
                for pattern in bruno_patterns:
                    if re.search(pattern, cleaned_text, re.IGNORECASE):
                        return True
                return False
            elif trainer_lower == "champion":
                # Champion battle (Gen3 FRLG)
                return "champion" in text
            elif trainer_lower == "cynthia":
                # OCR commonly misreads "cynthia" as "cunthia", "cyntha", etc.
                cynthia_patterns = [r'cynthia', r'cunthia', r'cyntha', r'cynth[il1]a']
                for pattern in cynthia_patterns:
                    if re.search(pattern, text):
                        return True
                return False
            elif trainer_lower == "cyrus":
                # OCR commonly misreads "cyrus" as "curus", "cvrus", etc.
                cyrus_patterns = [r'cyrus', r'curus', r'cvrus', r'cyru[s5]', r'curu[s5]']
                for pattern in cyrus_patterns:
                    if re.search(pattern, text):
                        return True
                return False
            else:
                # Clean text to handle OCR artifacts (quotes, missing letters)
                # Remove replacement characters and other Unicode artifacts
                # \ufffd is the replacement character, \u200b is zero-width space
                # Also remove other common OCR artifacts like \u00a0 (non-breaking space)
                cleaned_text = text.replace('\ufffd', '').replace('\u200b', '').replace('\u00a0', ' ')
                # Remove leading/trailing quotes and punctuation
                cleaned_text = cleaned_text.strip('"\'`.,;:!?').strip('"\'')
                
                # Check for "Leader [name]", "Champion [name]", "Elite Four [name]", or just the name
                # Handle "Leader [name]" - OCR sometimes runs words together (e.g., "leadermisty")
                leader_pattern = rf'leader\s*{re.escape(trainer_lower)}'
                if re.search(leader_pattern, cleaned_text, re.IGNORECASE):
                    return True
                if f"leader {trainer_lower}" in cleaned_text:
                    return True
                # Handle "Champion [name]" - OCR sometimes runs words together (e.g., "championlance")
                champion_pattern = rf'champion\s*{re.escape(trainer_lower)}'
                if re.search(champion_pattern, cleaned_text, re.IGNORECASE):
                    return True
                if f"champion {trainer_lower}" in cleaned_text:
                    return True
                # Handle "Elite Four [name]" with OCR error tolerance
                # OCR sometimes reads "Elite Four" as "lite four" (missing E) or adds quotes
                # Also handle cases where OCR runs "Four" and name together (e.g., "fourbruno")
                elite_four_pattern = rf"(?:elite|['\"]?lite)\s+four\s*{re.escape(trainer_lower)}"
                if re.search(elite_four_pattern, cleaned_text, re.IGNORECASE):
                    return True
                # Also check for "elite [name]" (OCR might miss "four")
                if f"elite {trainer_lower}" in cleaned_text:
                    return True
                # Filter out false positives: exclude "gentleman alfred" and similar
                # If text contains "gentleman", only match if trainer is explicitly "gentleman"
                if "gentleman" in cleaned_text and trainer_lower != "gentleman":
                    return False
                # Also filter out common false positives like "alfred" in "gentleman alfred"
                # Check if trainer name appears but is preceded by "gentleman"
                if re.search(rf'gentleman\s+{re.escape(trainer_lower)}\b', cleaned_text):
                    return False
                # Just the trainer name in the text (but not as part of another word)
                # Use word boundary to avoid partial matches (e.g., "fred" in "alfred")
                if re.search(rf'\b{re.escape(trainer_lower)}\b', cleaned_text):
                    return True
                return False
        else:
            return trainer_lower in text
    
    def _has_text_like_content(self, ocr_crop, min_contrast=30, min_text_ratio=0.03, max_text_ratio=0.6) -> bool:
        """
        Fast pre-screen to check if the region looks like it contains text.
        This is ~300x faster than OCR and filters out non-battle frames.
        
        Returns True if:
        - There's enough contrast (dark text on light background or vice versa)
        - The ratio of "text pixels" is reasonable (not too few, not too many)
        """
        gray = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2GRAY) if len(ocr_crop.shape) == 3 else ocr_crop
        
        # Check contrast - need enough difference for text to be visible
        min_val, max_val = gray.min(), gray.max()
        contrast = max_val - min_val
        if contrast < min_contrast:
            return False  # Not enough contrast for text
        
        # Check text ratio using percentile-based thresholding
        threshold_value = np.percentile(gray, 20)
        _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
        
        # Count dark pixels (potential text)
        text_pixels = np.sum(binary > 0)
        total_pixels = binary.size
        text_ratio = text_pixels / total_pixels
        
        # Text should be between 3% and 60% of the image
        return min_text_ratio <= text_ratio <= max_text_ratio
    
    def _get_ocr_text_at_frame(self, cap, frame_num: int) -> str:
        """
        Get OCR text at a specific frame. Returns empty string if no text found.
        This is separated from trainer checking so we only run OCR ONCE per frame.
        
        OPTIMIZED: Results are cached to avoid duplicate OCR calls on the same frame.
        """
        if not OCR_AVAILABLE:
            return ""
        
        # Check cache first (thread-safe)
        with self._ocr_cache_lock:
            if frame_num in self._ocr_cache:
                return self._ocr_cache[frame_num]
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            return ""
        
        # Get OCR region
        ocr_region = self.config["ocr_region"]
        ocr_crop = frame[
            ocr_region.y : ocr_region.y + ocr_region.height,
            ocr_region.x : ocr_region.x + ocr_region.width
        ]
        
        # OPTIMIZATION: Fast pre-screen to skip OCR on non-battle frames (~0.2ms vs ~70ms)
        if not self._has_text_like_content(ocr_crop):
            # Cache the empty result too
            with self._ocr_cache_lock:
                self._ocr_cache[frame_num] = ""
            return ""
        
        # Convert BGR to RGB for PIL
        rgb_crop = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_crop)
        
        # Run OCR with preprocessing appropriate for the generation
        try:
            ocr_pattern = self.game_config.ocr_pattern
            
            if ocr_pattern == "leader":
                # Gen3/Gen4: Use percentile-based preprocessing for colored backgrounds
                gray = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2GRAY)
                threshold_value = np.percentile(gray, 20)  # Darkest 20% = text
                _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
                processed = 255 - binary
                pil_processed = Image.fromarray(processed)
                # Use --psm 7 (single text line) - works better for single-line headers
                # PSM 6 fails on some images (e.g., rival, brock) where PSM 7 succeeds
                text = pytesseract.image_to_string(pil_processed, config='--psm 7')
            else:
                # Gen5: Raw OCR works well on the cleaner layout
                text = pytesseract.image_to_string(pil_image, config='--psm 6')
            
            # Clean text: remove quotes, normalize whitespace, handle OCR errors
            result = ' '.join(text.split()).lower()
            # Remove replacement characters and other Unicode artifacts that OCR sometimes produces
            # \ufffd is the replacement character, \u200b is zero-width space
            # Also remove other common OCR artifacts like \u00a0 (non-breaking space)
            result = result.replace('\ufffd', '').replace('\u200b', '').replace('\u00a0', ' ')
            # Remove common OCR artifacts: quotes, extra punctuation at start/end
            result = result.strip('"\'`.,;:!?')
            # Remove leading/trailing quotes that OCR sometimes adds
            result = result.strip('"\'')
            
            # Cache the result
            with self._ocr_cache_lock:
                self._ocr_cache[frame_num] = result
            
            return result
        except Exception:
            return ""
    
    def _check_trainer_at_frame(self, cap, frame_num: int, trainer_name: str) -> tuple[bool, str]:
        """Check if a trainer is present at a specific frame using OCR. Returns (detected, ocr_text)."""
        if not OCR_AVAILABLE:
            return False, ""
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            return False, ""
        
        # Get OCR region
        ocr_region = self.config["ocr_region"]
        ocr_crop = frame[
            ocr_region.y : ocr_region.y + ocr_region.height,
            ocr_region.x : ocr_region.x + ocr_region.width
        ]
        
        # OPTIMIZATION: Fast pre-screen to skip OCR on non-battle frames (~0.2ms vs ~70ms)
        if not self._has_text_like_content(ocr_crop):
            return False, ""
        
        # Convert BGR to RGB for PIL
        rgb_crop = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_crop)
        
        # Run OCR with preprocessing appropriate for the generation
        try:
            ocr_pattern = self.game_config.ocr_pattern
            
            if ocr_pattern == "leader":
                # Gen3/Gen4: Use percentile-based preprocessing for colored backgrounds
                gray = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2GRAY)
                threshold_value = np.percentile(gray, 20)  # Darkest 20% = text
                _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
                processed = 255 - binary
                pil_processed = Image.fromarray(processed)
                # Use --psm 7 (single text line) - works better for single-line headers
                # PSM 6 fails on some images (e.g., rival, brock) where PSM 7 succeeds
                text = pytesseract.image_to_string(pil_processed, config='--psm 7')
            else:
                # Gen5: Raw OCR works well on the cleaner layout
                text = pytesseract.image_to_string(pil_image, config='--psm 6')
            
            # Clean text: remove quotes, normalize whitespace, handle OCR errors
            text_clean = ' '.join(text.split()).lower()
            # Remove replacement characters and other Unicode artifacts that OCR sometimes produces
            # \ufffd is the replacement character, \u200b is zero-width space
            # Also remove other common OCR artifacts like \u00a0 (non-breaking space)
            text_clean = text_clean.replace('\ufffd', '').replace('\u200b', '').replace('\u00a0', ' ')
            # Remove common OCR artifacts: quotes, extra punctuation at start/end
            text_clean = text_clean.strip('"\'`.,;:!?')
            # Remove leading/trailing quotes that OCR sometimes adds
            text_clean = text_clean.strip('"\'')
            
            # Debug output
            if self.debug_ocr and text_clean.strip():
                print(f"    [OCR @{frame_num}] '{text_clean}'", flush=True)
            
            # Match based on OCR pattern type
            ocr_pattern = self.game_config.ocr_pattern
            trainer_lower = trainer_name.lower()
            
            if ocr_pattern == "team":
                # Gen5 pattern: "[trainer]'s Team"
                search_pattern = f"{trainer_lower}'s team"
                search_pattern_alt = f"{trainer_lower}s team"  # OCR sometimes misses apostrophe
                
                if search_pattern in text_clean or search_pattern_alt in text_clean:
                    return True, text_clean
                    
            elif ocr_pattern == "leader":
                # Gen3/Gen4 pattern: "Leader [name]", "Rival #", "Elite Four [name]", "Champion"
                if trainer_lower == "rival":
                    # Special case: "Rival" followed by any number (Rival 1, Rival 2, etc.)
                    # OCR commonly mangles "Rival" into: rvari, kvai, rvar, ival, eva, etc.
                    # Also handle tan/brown theme which produces different artifacts
                    rival_patterns = [
                        r'rival\s*\d+',       # correct: "rival 1", "rival2"
                        r'rival[1-9]',        # compact: "rival1", "rival2"
                        r'rivals\b',          # OCR sometimes reads "rivals" (no digit)
                        r'riva[il1]\s*\d+',   # misread: "rivai 1", "rival1"
                        r'rivar',             # misread: "rivar"
                        r'rvari',             # misread: "rvari" (OCR garble)
                        r'kvai\s*\d*',        # misread: "kvai2"
                        r'rvar',              # partial: "rvar"
                        r'[rk]va[il1r]\s*\d*', # flexible: rval, kval, rvai, kvai
                        r'iva[il1]?\s*\d+',   # misread: "ival 1", "iva 2"
                        r'rva[il1]\s*\d*',    # misread: "rvai", "rval" (tan theme)
                    ]
                    for pattern in rival_patterns:
                        if re.search(pattern, text_clean):
                            return True, text_clean
                elif trainer_lower in ["tate & liza", "tate and liza"]:
                    # Special case: double battle gym leaders
                    if "tate" in text_clean and "liza" in text_clean:
                        return True, text_clean
                elif trainer_lower == "lt. surge" or trainer_lower == "surge":
                    # Handle Lt. Surge variations
                    if "surge" in text_clean:
                        return True, text_clean
                elif trainer_lower == "silver":
                    # Rival Silver - match "rival silver" or just "silver" in context
                    if "rival" in text_clean and "silver" in text_clean:
                        return True, text_clean
                    # Also match just "silver" as standalone word
                    if re.search(r'\bsilver\b', text_clean):
                        return True, text_clean
                    return False, text_clean
                elif trainer_lower == "kimono girl":
                    # Kimono Girl - match any text containing "kimono girl" regardless of name that follows
                    # Pattern: "kimono girl" followed by optional name (e.g., "kimono girl sayo")
                    if re.search(r'\bkimono\s+girl\b', text_clean, re.IGNORECASE):
                        return True, text_clean
                    return False, text_clean
                elif trainer_lower == "misty":
                    # Handle OCR errors: "misty" sometimes reads as "mistu", etc.
                    misty_patterns = [r'leader\s*misty', r'leader\s*mistu', r'leader\s*mist[yui]', r'\bmisty\b', r'\bmistu\b']
                    for pattern in misty_patterns:
                        if re.search(pattern, text_clean, re.IGNORECASE):
                            return True, text_clean
                    return False, text_clean
                elif trainer_lower == "janine":
                    # Handle OCR errors: "leader" sometimes reads as "deader", "1eader", etc.
                    janine_patterns = [
                        r'leader\s*janine',
                        r'[ld]eader\s*janine',  # "deader" OCR error
                        r'[il1]eader\s*janine',  # "1eader" OCR error
                        r'\bjanine\b'
                    ]
                    for pattern in janine_patterns:
                        if re.search(pattern, text_clean, re.IGNORECASE):
                            return True, text_clean
                    return False, text_clean
                elif trainer_lower == "bruno":
                    # Handle OCR errors for Elite Four Bruno:
                    # "elite" -> "lite", "slite", "elite"
                    # "bruno" -> "bruno", "brunco", "brunc0", "bruanco", "brun0"
                    bruno_patterns = [
                        r'(?:elite|[s\']?lite)\s*four\s*bru[an]?[cn][co0]?o?',  # "elite four bruno", "lite four brunco", "lite four bruanco"
                        r'elite\s+bru[an]?[cn][co0]?o?',  # "elite bruno"
                        r'\bbru[an]?[cn][co0]?o?\b',  # just "bruno", "brunco", "bruanco"
                    ]
                    for pattern in bruno_patterns:
                        if re.search(pattern, text_clean, re.IGNORECASE):
                            return True, text_clean
                    return False, text_clean
                elif trainer_lower == "champion":
                    # Champion battle (Gen3 FRLG)
                    if "champion" in text_clean:
                        return True, text_clean
                elif trainer_lower == "cynthia":
                    # OCR commonly misreads "cynthia" as "cunthia", "cyntha", etc.
                    cynthia_patterns = [r'cynthia', r'cunthia', r'cyntha', r'cynth[il1]a']
                    for pattern in cynthia_patterns:
                        if re.search(pattern, text_clean):
                            return True, text_clean
                elif trainer_lower == "cyrus":
                    # OCR commonly misreads "cyrus" as "curus", "cvrus", etc.
                    cyrus_patterns = [r'cyrus', r'curus', r'cvrus', r'cyru[s5]', r'curu[s5]']
                    for pattern in cyrus_patterns:
                        if re.search(pattern, text_clean):
                            return True, text_clean
                else:
                    # Check for "Leader [name]" pattern (gym leaders)
                    # Handle cases where OCR runs words together (e.g., "leadermisty")
                    leader_pattern = rf'leader\s*{re.escape(trainer_lower)}'
                    if re.search(leader_pattern, text_clean, re.IGNORECASE):
                        return True, text_clean
                    if f"leader {trainer_lower}" in text_clean:
                        return True, text_clean
                    
                    # Check for "Champion [name]" pattern (Cynthia, Steven, Lance, etc.)
                    # Handle cases where OCR runs words together (e.g., "championlance")
                    champion_pattern = rf'champion\s*{re.escape(trainer_lower)}'
                    if re.search(champion_pattern, text_clean, re.IGNORECASE):
                        return True, text_clean
                    if f"champion {trainer_lower}" in text_clean:
                        return True, text_clean
                    
                    # Check for "Elite Four [name]" pattern with OCR error tolerance
                    # OCR sometimes reads "Elite Four" as "lite four" (missing E) or adds quotes
                    # Also handle cases where OCR runs "Four" and name together (e.g., "fourbruno")
                    elite_four_pattern = rf"(?:elite|['\"]?lite)\s+four\s*{re.escape(trainer_lower)}"
                    if re.search(elite_four_pattern, text_clean, re.IGNORECASE):
                        return True, text_clean
                    if f"elite {trainer_lower}" in text_clean:  # OCR might miss "four"
                        return True, text_clean
                    
                    # Filter out false positives: exclude "gentleman alfred" and similar
                    # If text contains "gentleman", only match if trainer is explicitly "gentleman"
                    if "gentleman" in text_clean and trainer_lower != "gentleman":
                        return False, text_clean
                    # Also filter out common false positives like "alfred" in "gentleman alfred"
                    if re.search(rf'gentleman\s+{re.escape(trainer_lower)}\b', text_clean):
                        return False, text_clean
                    
                    # Check for just the trainer name at start of text (header position)
                    # This handles Elite Four, Champion, Team Galactic, etc.
                    # Match if name appears at the start or as standalone word
                    if text_clean.startswith(trainer_lower) or re.search(rf'\b{re.escape(trainer_lower)}\b', text_clean):
                        return True, text_clean
            
            else:
                # Default: just check if trainer name is in text
                if trainer_lower in text_clean:
                    return True, text_clean
            
            return False, text_clean
        except Exception as e:
            return False, f"OCR error: {e}"
    
    def _check_black_white_at_frame(self, cap, frame_num: int) -> tuple[bool, bool, float]:
        """Check if frame is black or white. Returns (is_black, is_white, mean)."""
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            return False, False, 128.0
        
        gameplay = self.config["gameplay"]
        gp_crop = frame[
            gameplay.y : gameplay.y + gameplay.height,
            gameplay.x : gameplay.x + gameplay.width
        ]
        
        if self.downscale_factor < 1.0:
            gp_crop = cv2.resize(gp_crop, None, 
                                 fx=self.downscale_factor, 
                                 fy=self.downscale_factor,
                                 interpolation=cv2.INTER_AREA)
        
        gray = cv2.cvtColor(gp_crop, cv2.COLOR_BGR2GRAY)
        mean_val = gray.mean()
        
        return mean_val <= self.BLACK_MEAN_THRESHOLD, mean_val >= self.WHITE_MEAN_THRESHOLD, mean_val
    
    def _find_black_white_in_range(self, cap, start_frame: int, end_frame: int, step: int = 10) -> Optional[int]:
        """
        Search for a black/white frame in a range, jumping by 'step' frames.
        Works in either direction depending on start_frame < end_frame or start_frame > end_frame.
        """
        if start_frame <= end_frame:
            for frame in range(start_frame, end_frame + 1, step):
                is_black, is_white, _ = self._check_black_white_at_frame(cap, frame)
                if is_black or is_white:
                    return frame
        else:
            for frame in range(start_frame, end_frame - 1, -step):
                is_black, is_white, _ = self._check_black_white_at_frame(cap, frame)
                if is_black or is_white:
                    return frame
        return None
    
    def _binary_search_transition(self, cap, start_frame: int, end_frame: int, find_start: bool = True) -> Optional[int]:
        """
        Use binary search to find the exact transition point between normal and black/white frames.
        Much faster than linear search for large ranges.
        
        If find_start=True, finds the START of a black/white sequence (first black frame).
        If find_start=False, finds the END of a black/white sequence (last black frame).
        """
        # First, verify there's a transition in this range
        start_bw = self._check_black_white_at_frame(cap, start_frame)
        end_bw = self._check_black_white_at_frame(cap, end_frame)
        
        start_is_bw = start_bw[0] or start_bw[1]
        end_is_bw = end_bw[0] or end_bw[1]
        
        # If both same, no transition
        if start_is_bw == end_is_bw:
            return start_frame if start_is_bw else None
        
        # Binary search for the transition point
        left, right = start_frame, end_frame
        while right - left > 1:
            mid = (left + right) // 2
            mid_bw = self._check_black_white_at_frame(cap, mid)
            mid_is_bw = mid_bw[0] or mid_bw[1]
            
            if find_start:
                # Looking for first black frame
                if mid_is_bw:
                    right = mid
                else:
                    left = mid
            else:
                # Looking for last black frame
                if mid_is_bw:
                    left = mid
                else:
                    right = mid
        
        return right if find_start else left
    
    def _refine_to_sequence_start(self, cap, approx_frame: int) -> int:
        """
        Given a frame that's black/white, find the exact START of the sequence.
        Uses binary search for speed.
        """
        # Search backwards up to 2 seconds (480 frames at 240fps) to find where black starts
        search_start = max(0, approx_frame - 480)
        result = self._binary_search_transition(cap, search_start, approx_frame, find_start=True)
        return result if result else approx_frame
    
    def _refine_to_sequence_end(self, cap, approx_frame: int) -> int:
        """
        Given a frame that's black/white, find the exact END of the sequence.
        Uses binary search for speed.
        """
        # Search forwards up to 2 seconds (480 frames at 240fps) to find where black ends
        search_end = min(self.total_frames - 1, approx_frame + 480)
        result = self._binary_search_transition(cap, approx_frame, search_end, find_start=False)
        return result if result else approx_frame
    
    def _find_sequence_center(self, cap, approx_frame: int) -> int:
        """
        Given a frame that's black/white, find the CENTER of the sequence.
        First finds the start and end, then returns the midpoint.
        """
        start = self._refine_to_sequence_start(cap, approx_frame)
        end = self._refine_to_sequence_end(cap, approx_frame)
        return (start + end) // 2
    
    def _binary_search_text_boundary(self, cap, start_frame: int, end_frame: int, 
                                      trainer_name: str, find_first: bool = True) -> int:
        """
        Use binary search to find the boundary where trainer text appears/disappears.
        Much faster than linear search - reduces O(n) OCR calls to O(log n).
        
        Args:
            start_frame: Frame where text is NOT detected (or IS detected if find_first=False)
            end_frame: Frame where text IS detected (or NOT detected if find_first=False)
            trainer_name: The trainer to search for
            find_first: If True, find first frame with text. If False, find last frame with text.
            
        Returns:
            The approximate frame number of the boundary
        """
        left, right = start_frame, end_frame
        
        # Ensure left < right
        if left > right:
            left, right = right, left
        
        # Binary search - stop when window is small enough
        # We don't need exact precision since we'll search for black/white in a window anyway
        MIN_WINDOW = int(self.fps * 0.5)  # Stop at 0.5 second precision
        
        while right - left > MIN_WINDOW:
            mid = (left + right) // 2
            detected = self._text_contains_trainer_pattern(
                self._get_ocr_text_at_frame(cap, mid), trainer_name
            )
            
            if find_first:
                # Looking for first frame WITH text
                if detected:
                    right = mid  # Text found, boundary is earlier
                else:
                    left = mid  # Text not found, boundary is later
            else:
                # Looking for last frame WITH text
                if detected:
                    left = mid  # Text found, boundary is later
                else:
                    right = mid  # Text not found, boundary is earlier
        
        return (left + right) // 2
    
    def _find_transition_before_fast(self, cap, start_frame: int, trainer_name: str) -> Optional[int]:
        """
        Fast search for transition BEFORE battle (cut-in point).
        Uses OCR to narrow down where to search, then finds black/white frames.
        The black/white frame should be between where text disappears and where it appears.
        
        ALGORITHM:
        1. Start at the frame where trainer was detected (start_frame)
        2. Jump BACKWARDS by TRANSITION_JUMP frames (default 720 = 3 sec at 240fps)
        3. Check if trainer text is still present at each jump
        4. When text disappears, use binary search to find exact boundary
        5. Search for black/white frame around the boundary (backwards from boundary)
        
        OPTIMIZED: Uses larger jumps (3 sec instead of 1 sec) to reduce OCR calls by 3x.
        Then uses binary search to narrow down the exact window.
        
        IMPORTANT: Searches BACKWARDS from the battle to find the closest transition.
        This ensures we find the black frame right before the battle, not an earlier
        white frame (e.g., Gen 5 has white->graphic->black->battle sequence).
        
        POTENTIAL ISSUE: If TRANSITION_JUMP is too large (e.g., 720 frames = 3 sec),
        we might jump over short battles entirely. However, this function searches backwards
        from a known detection point, so it should still find the transition before the battle.
        """
        JUMP = self.TRANSITION_JUMP  # 3 seconds at 240fps (configurable)
        
        # Jump backwards until trainer text disappears
        frame = start_frame
        last_with_text = start_frame
        
        while frame > 0:
            frame -= JUMP
            if frame < 0:
                frame = 0
            detected = self._text_contains_trainer_pattern(
                self._get_ocr_text_at_frame(cap, frame), trainer_name
            )
            if detected:
                last_with_text = frame  # Still in battle
            else:
                # Text disappeared - transition is between 'frame' and 'last_with_text'
                # Use binary search to narrow down the exact boundary (reduces OCR calls)
                boundary = self._binary_search_text_boundary(
                    cap, frame, last_with_text, trainer_name, find_first=True
                )
                
                # Search around the boundary for black/white frame
                # Search BACKWARDS from boundary to find the closest transition to the battle
                # This is important for Gen 5 where white->graphic->black->battle sequence
                # means we want the black frame (closest), not the white frame (earliest)
                search_start = max(0, boundary - JUMP)
                
                # Coarse search BACKWARDS (from boundary toward earlier frames)
                approx = self._find_black_white_in_range(cap, boundary, search_start, step=10)
                if approx:
                    return self._find_sequence_center(cap, approx)
                
                # If not found, try smaller steps
                approx = self._find_black_white_in_range(cap, boundary, search_start, step=1)
                if approx:
                    return self._find_sequence_center(cap, approx)
                
                break
        
        return None
    
    def _find_transition_after_fast(self, cap, start_frame: int, trainer_name: str) -> Optional[int]:
        """
        Fast search for transition AFTER battle (cut-out point).
        Uses OCR to narrow down where to search - the black/white frame should be
        shortly after the trainer text disappears.
        
        ALGORITHM:
        1. Start at the frame where trainer was detected (start_frame)
        2. Jump FORWARDS by TRANSITION_JUMP frames (default 720 = 3 sec at 240fps)
        3. Check if trainer text is still present at each jump
        4. When text disappears, use binary search to find exact boundary
        5. Search for black/white frame around the boundary (forwards from boundary)
        
        OPTIMIZED: Uses larger jumps (3 sec instead of 1 sec) to reduce OCR calls by 3x.
        Then uses binary search to narrow down the exact window.
        
        POTENTIAL ISSUE: If TRANSITION_JUMP is too large and the battle is very short
        (shorter than TRANSITION_JUMP), we might jump past the battle end in one step.
        However, the binary search should still find the boundary between last_with_text
        and the frame where text disappeared. The real issue is if the black/white frame
        search window is too narrow - we extend the search up to JUMP * 2 frames forward
        to handle this case.
        """
        JUMP = self.TRANSITION_JUMP  # 3 seconds at 240fps (configurable)
        
        # Jump forwards until trainer text disappears
        frame = start_frame
        last_with_text = start_frame
        
        while frame < self.total_frames:
            frame += JUMP
            if frame >= self.total_frames:
                frame = self.total_frames - 1
            
            detected = self._text_contains_trainer_pattern(
                self._get_ocr_text_at_frame(cap, frame), trainer_name
            )
            if detected:
                last_with_text = frame
            else:
                # Text disappeared - transition is between 'last_with_text' and 'frame'
                # Use binary search to narrow down the exact boundary (reduces OCR calls)
                boundary = self._binary_search_text_boundary(
                    cap, last_with_text, frame, trainer_name, find_first=False
                )
                
                # Search around the boundary for black/white frame
                search_start = max(0, boundary - int(self.fps * 5))
                search_end = min(self.total_frames - 1, boundary + JUMP)
                
                # Coarse search (every 10 frames)
                approx = self._find_black_white_in_range(cap, search_start, search_end, step=10)
                if approx:
                    return self._find_sequence_center(cap, approx)
                
                # If not found in immediate area, extend search further
                extended_end = min(self.total_frames - 1, frame + JUMP * 2)
                approx = self._find_black_white_in_range(cap, search_end, extended_end, step=10)
                if approx:
                    return self._find_sequence_center(cap, approx)
                
                break
        
        return None

    def _process_trainer_detection(self, trainer_name: str, first_frame: int, results_queue: Queue):
        """
        Worker function to process a single trainer detection.
        Finds the cut-in and cut-out frames using fast coarse-to-fine search.
        """
        # Each worker gets its own video capture
        cap = cv2.VideoCapture(str(self.video_path))
        
        try:
            # Fast search for cut-in (backwards)
            cut_in = self._find_transition_before_fast(cap, first_frame, trainer_name)
            if cut_in is None:
                # Fallback: do a more thorough search
                cut_in = self._find_black_white_in_range(cap, first_frame, max(0, first_frame - int(self.fps * 60)), step=5)
                if cut_in:
                    cut_in = self._find_sequence_center(cap, cut_in)
                else:
                    cut_in = first_frame  # Last resort fallback
            
            # Fast search for cut-out (forwards)
            cut_out = self._find_transition_after_fast(cap, first_frame, trainer_name)
            if cut_out is None:
                # Fallback: do a more thorough search for short battles
                # Search with smaller steps to catch transitions close to battle end
                # First try a tight search (30 seconds) with fine steps
                search_end = min(self.total_frames - 1, first_frame + int(self.fps * 30))
                cut_out = self._find_black_white_in_range(cap, first_frame, search_end, step=5)
                if cut_out:
                    cut_out = self._find_sequence_center(cap, cut_out)
                else:
                    # If not found, try wider search (2 minutes) with coarser steps
                    search_end = min(self.total_frames - 1, first_frame + int(self.fps * 120))
                    cut_out = self._find_black_white_in_range(cap, first_frame, search_end, step=10)
                    if cut_out:
                        cut_out = self._find_sequence_center(cap, cut_out)
                    else:
                        # If still not found and near end of video, use end of video
                        if first_frame > self.total_frames - int(self.fps * 60):
                            cut_out = self.total_frames - 1
                        else:
                            cut_out = first_frame  # Last resort fallback
            
            # Sanity check: cut_out should be after cut_in
            if cut_out <= cut_in:
                # Try extended forward search (3 minutes out)
                extended_search = self._find_black_white_in_range(
                    cap, cut_in + 1, min(self.total_frames - 1, cut_in + int(self.fps * 180)), step=10
                )
                if extended_search:
                    cut_out = self._find_sequence_center(cap, extended_search)
            
            # Final sanity check: if still invalid, try even wider search (5 minutes)
            if cut_out <= cut_in:
                wider_search = self._find_black_white_in_range(
                    cap, cut_in + 1, min(self.total_frames - 1, cut_in + int(self.fps * 300)), step=20
                )
                if wider_search:
                    cut_out = self._find_sequence_center(cap, wider_search)
            
            # Skip this battle if we still can't find a valid cut-out
            if cut_out <= cut_in:
                print(f"    WARNING: Could not find cut-out for {trainer_name} at frame {first_frame}. Skipping.", flush=True)
                return  # Don't add to results queue
            
            # Get transition types
            is_black_in, is_white_in, mean_in = self._check_black_white_at_frame(cap, cut_in)
            is_black_out, is_white_out, mean_out = self._check_black_white_at_frame(cap, cut_out)
            
            result = {
                "trainer": trainer_name,
                "first_frame": first_frame,
                "cut_in": cut_in,
                "cut_out": cut_out,
                "cut_in_type": "BLACK" if is_black_in else ("WHITE" if is_white_in else "UNKNOWN"),
                "cut_out_type": "BLACK" if is_black_out else ("WHITE" if is_white_out else "UNKNOWN"),
                "mean_in": mean_in,
                "mean_out": mean_out,
            }
            results_queue.put(result)
            
        finally:
            cap.release()
    
    def analyze(self, detect_trainers: list[str] = None) -> tuple[list[Detection], list[BattleSequence]]:
        """
        Analyze video for trainer battles using parallel processing.
        
        Fast approach:
        1. Main thread scans for trainer text at large intervals
        2. Worker threads process each detection to find cut points
        3. Coarse-to-fine search for transitions
        
        Returns:
            Tuple of (detections list, battle sequences list)
        """
        start_time = time.time()
        battles: list[BattleSequence] = []
        detections: list[Detection] = []
        
        if not detect_trainers:
            print("No trainers specified to detect.")
            return detections, battles
        
        if not OCR_AVAILABLE:
            print("OCR not available, cannot detect trainers")
            return detections, battles
        
        print(f"\nScanning {self.total_frames} frames for trainers: {detect_trainers}")
        print(f"Sample interval: {self.EARLY_GAME_INTERVAL} frames (early) / {self.TRAINER_SAMPLE_INTERVAL} frames (normal)")
        print(f"Transition search: {self.TRANSITION_JUMP} frame jumps with binary search refinement")
        print(f"Using {self.num_workers} worker threads for cut point detection")
        print("-" * 70, flush=True)
        
        # Queue for detection results
        results_queue: Queue = Queue()
        pending_tasks = []
        
        # Use thread pool for processing detections
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Main thread: scan for trainers
            cap = cv2.VideoCapture(str(self.video_path))
            
            frame_num = 0
            # Track detections PER TRAINER to avoid filtering different trainers as duplicates
            detections_per_trainer: dict[str, list[int]] = {t: [] for t in detect_trainers}
            ocr_calls = 0  # Track OCR calls for performance monitoring
            frames_checked = 0
            
            while frame_num < self.total_frames:
                # OPTIMIZATION: Run OCR ONCE per frame, then check all trainers
                ocr_text = self._get_ocr_text_at_frame(cap, frame_num)
                frames_checked += 1
                
                if ocr_text:  # Only count and check if OCR returned text
                    ocr_calls += 1
                    
                    # Debug output
                    if self.debug_ocr:
                        print(f"    [OCR @{frame_num}] '{ocr_text}'", flush=True)
                    
                    # Check all trainers against this single OCR result
                    for trainer_name in detect_trainers:
                        if self._text_contains_trainer_pattern(ocr_text, trainer_name):
                            # Check if we're too close to an existing detection OF THE SAME TRAINER
                            # Use current interval for proximity check, but be more lenient for rapid battles
                            current_interval = self.EARLY_GAME_INTERVAL if frame_num < self.EARLY_GAME_THRESHOLD else self.TRAINER_SAMPLE_INTERVAL
                            
                            # Special handling for trainers that appear multiple times in quick succession
                            # Kimono Girls: 5 battles in a row, each ~10 seconds apart
                            # Use smaller proximity threshold (just 1x interval instead of 2x)
                            if trainer_name.lower() == "kimono girl":
                                proximity_multiplier = 1  # More lenient for Kimono Girls
                            else:
                                proximity_multiplier = 2  # Standard threshold
                            
                            too_close = any(abs(frame_num - d) < current_interval * proximity_multiplier 
                                           for d in detections_per_trainer[trainer_name])
                            
                            if not too_close:
                                print(f"  Found {trainer_name} at frame {frame_num} ({frame_num/self.fps:.1f}s) - processing...", flush=True)
                                detections_per_trainer[trainer_name].append(frame_num)
                                
                                # Submit to worker thread
                                future = executor.submit(
                                    self._process_trainer_detection,
                                    trainer_name, frame_num, results_queue
                                )
                                pending_tasks.append(future)
                                # Don't break - allow multiple trainers to be detected in the same frame
                                # (e.g., if OCR text contains multiple trainer names, though unlikely)
                
                # ADAPTIVE SAMPLING: More frequent checks early in video to catch short battles
                if frame_num < self.EARLY_GAME_THRESHOLD:
                    frame_num += self.EARLY_GAME_INTERVAL  # Every 2 sec for first 10 min
                else:
                    frame_num += self.TRAINER_SAMPLE_INTERVAL  # Every 6 sec after that
                
                # Progress
                if frames_checked % 50 == 0:
                    pct = (frame_num / self.total_frames) * 100
                    elapsed = time.time() - start_time
                    print(f"  ... {pct:.0f}% scanned ({ocr_calls} OCR calls in {elapsed:.1f}s)", flush=True)
            
            cap.release()
            print(f"\nScan complete: {ocr_calls} OCR calls total")
            
            # Wait for all tasks to complete
            print(f"\nWaiting for {len(pending_tasks)} cut point searches to complete...", flush=True)
            for future in as_completed(pending_tasks):
                try:
                    future.result()  # This will raise any exceptions
                except Exception as e:
                    print(f"  Warning: Worker error: {e}")
        
        # Collect results
        while not results_queue.empty():
            result = results_queue.get()
            
            print(f"  {result['trainer']}: IN={result['cut_in']} ({result['cut_in']/self.fps:.1f}s) "
                  f"OUT={result['cut_out']} ({result['cut_out']/self.fps:.1f}s)")
            
            # Add detections
            detections.append(Detection(
                result['cut_in'], 
                result['cut_in'] / self.fps, 
                f"{result['cut_in_type']}_FRAME",
                f"mean={result['mean_in']:.1f}"
            ))
            detections.append(Detection(
                result['cut_out'], 
                result['cut_out'] / self.fps, 
                f"{result['cut_out_type']}_FRAME",
                f"mean={result['mean_out']:.1f}"
            ))
            
            # Add battle
            battles.append(BattleSequence(
                trainer_name=result['trainer'],
                battle_start_frame=result['first_frame'],
                battle_end_frame=result['cut_out'],
                cut_in_frame=result['cut_in'],
                cut_out_frame=result['cut_out'],
                cut_in_timestamp=result['cut_in'] / self.fps,
                cut_out_timestamp=result['cut_out'] / self.fps
            ))
        
        # Sort battles by cut-in time
        battles.sort(key=lambda b: b.cut_in_frame)
        
        # De-duplicate overlapping battles (same trainer with overlapping time ranges)
        battles = self._deduplicate_battles(battles)
        
        # Also de-duplicate detections
        seen_frames = set()
        unique_detections = []
        for d in detections:
            if d.frame_number not in seen_frames:
                seen_frames.add(d.frame_number)
                unique_detections.append(d)
        detections = unique_detections
        
        elapsed = time.time() - start_time
        print("-" * 70)
        print(f"Analysis complete in {elapsed:.1f}s")
        print(f"Found {len(battles)} battles")
        
        return detections, battles
    
    def _deduplicate_battles(self, battles: list[BattleSequence]) -> list[BattleSequence]:
        """
        Merge overlapping battles of the same trainer.
        Two battles are considered overlapping if their time ranges intersect.
        """
        if not battles:
            return battles
        
        # Group by trainer
        by_trainer = {}
        for battle in battles:
            key = battle.trainer_name.lower()
            if key not in by_trainer:
                by_trainer[key] = []
            by_trainer[key].append(battle)
        
        merged = []
        for trainer, trainer_battles in by_trainer.items():
            # Sort by cut_in
            trainer_battles.sort(key=lambda b: b.cut_in_frame)
            
            # Merge overlapping
            current = trainer_battles[0]
            for next_battle in trainer_battles[1:]:
                # Check if overlapping (next starts before current ends)
                if next_battle.cut_in_frame <= current.cut_out_frame:
                    # Merge: keep earliest cut_in, latest cut_out
                    current = BattleSequence(
                        trainer_name=current.trainer_name,
                        battle_start_frame=min(current.battle_start_frame, next_battle.battle_start_frame),
                        battle_end_frame=max(current.battle_end_frame, next_battle.battle_end_frame),
                        cut_in_frame=min(current.cut_in_frame, next_battle.cut_in_frame),
                        cut_out_frame=max(current.cut_out_frame, next_battle.cut_out_frame),
                        cut_in_timestamp=min(current.cut_in_timestamp, next_battle.cut_in_timestamp),
                        cut_out_timestamp=max(current.cut_out_timestamp, next_battle.cut_out_timestamp),
                    )
                else:
                    # No overlap, add current and move to next
                    merged.append(current)
                    current = next_battle
            
            merged.append(current)
        
        # Sort final result
        merged.sort(key=lambda b: b.cut_in_frame)
        return merged


def export_timebolt_json(battles: list[BattleSequence], video_duration: float, fps: float, output_path: Path):
    """
    Export battle cut points in Timebolt JSON format.
    Creates segments marking battle boundaries with labels, keeping all footage.
    """
    segments = []
    
    # Sort battles by cut_in time
    sorted_battles = sorted(battles, key=lambda b: b.cut_in_timestamp)
    
    current_time = 0.0
    
    for battle in sorted_battles:
        # Segment before the battle (if any gap)
        if battle.cut_in_timestamp > current_time:
            segments.append({
                "start": current_time,
                "duration": battle.cut_in_timestamp - current_time,
                "type": "original",
                "punched": 1,
                "punchedPosition": "center",
                "operation": "keep"
            })
        
        # The battle segment with label
        battle_duration = battle.cut_out_timestamp - battle.cut_in_timestamp
        segments.append({
            "start": battle.cut_in_timestamp,
            "duration": battle_duration,
            "type": "original",
            "punched": 1,
            "punchedPosition": "center",
            "operation": "keep",
            "label": "Green",
            "name": f"{battle.trainer_name.title()} Battle"
        })
        
        current_time = battle.cut_out_timestamp
    
    # Segment after the last battle (if any)
    if current_time < video_duration:
        segments.append({
            "start": current_time,
            "duration": video_duration - current_time,
            "type": "original",
            "punched": 1,
            "punchedPosition": "center",
            "operation": "keep"
        })
    
    # Write JSON file
    with open(output_path, 'w') as f:
        json.dump(segments, f, indent=2)
    
    print(f"\nExported {len(segments)} segments to: {output_path}")


def seconds_to_timecode(seconds: float, fps: float) -> str:
    """Convert seconds to SMPTE timecode (HH:MM:SS:FF)."""
    total_frames = int(seconds * fps)
    frames = total_frames % int(fps)
    total_seconds = total_frames // int(fps)
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"


def get_premiere_label(trainer_name: str) -> str:
    """Get the Premiere Pro label for a trainer. Returns 'Magenta' for Rival, defaults to 'Cerulean'."""
    trainer_lower = trainer_name.lower()
    return PREMIERE_LABELS.get(trainer_lower, "Cerulean")


def export_automation_blocks_json(battles: list[BattleSequence], fps: float, output_path: Path):
    """
    Export battle data for Premiere Pro Automation Blocks.
    
    Creates a JSON file with label information that can be used by an Automation Blocks
    script to apply labels to clips in the timeline.
    
    Format:
    {
        "fps": 240,
        "labels": [
            {
                "trainer": "Rival",
                "label": "Magenta",
                "start_seconds": 53.05,
                "end_seconds": 62.64,
                "start_timecode": "00:00:53:12",
                "end_timecode": "00:01:02:15",
                "start_frame": 12733,
                "end_frame": 15034
            },
            ...
        ]
    }
    """
    labels_data = []
    
    # Sort battles by cut_in time
    sorted_battles = sorted(battles, key=lambda b: b.cut_in_timestamp)
    
    for battle in sorted_battles:
        label_name = get_premiere_label(battle.trainer_name)
        
        labels_data.append({
            "trainer": battle.trainer_name.title(),
            "label": label_name,
            "start_seconds": round(battle.cut_in_timestamp, 4),
            "end_seconds": round(battle.cut_out_timestamp, 4),
            "start_timecode": seconds_to_timecode(battle.cut_in_timestamp, fps),
            "end_timecode": seconds_to_timecode(battle.cut_out_timestamp, fps),
            "start_frame": battle.cut_in_frame,
            "end_frame": battle.cut_out_frame
        })
    
    output_data = {
        "fps": fps,
        "total_battles": len(labels_data),
        "labels": labels_data
    }
    
    # Write JSON file
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Exported {len(labels_data)} labels for Automation Blocks to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Fury Cutter - Video Analysis Tool for Pokemon Game Editing"
    )
    
    parser.add_argument("video", type=Path, help="Path to video file")
    parser.add_argument("--version", "-v", type=str, required=True,
                       choices=list(GAME_CONFIGS.keys()),
                       help=f"Game version: {', '.join(GAME_CONFIGS.keys())}")
    parser.add_argument("--downscale", "-d", type=float, default=0.25,
                       help="Downscale factor for faster processing")
    parser.add_argument("--workers", "-w", type=int, default=None,
                       help="Number of worker threads")
    parser.add_argument("--trainers", "-t", nargs="+", default=None,
                       help="Override trainer list (default: use game's trainer list)")
    parser.add_argument("--output", "-o", type=Path, default=None,
                       help="Output JSON file path (default: [video_name].json)")
    parser.add_argument("--debug-ocr", action="store_true",
                       help="Print OCR text for debugging")
    # Performance tuning
    parser.add_argument("--transition-jump", type=int, default=720,
                       help="Frame jump for transition search (default: 720 = 3sec at 240fps)")
    parser.add_argument("--early-interval", type=int, default=480,
                       help="Sample interval for early game in frames (default: 480 = 2sec at 240fps)")
    parser.add_argument("--normal-interval", type=int, default=1440,
                       help="Sample interval for normal scanning in frames (default: 1440 = 6sec at 240fps)")
    
    args = parser.parse_args()
    
    if not args.video.exists():
        print(f"Error: Video file not found: {args.video}")
        return 1
    
    # Get game configuration
    game_config = GAME_CONFIGS[args.version]
    
    # Use game's trainer list unless overridden
    trainers = args.trainers if args.trainers else game_config.trainers
    
    print(f"Game: {game_config.name} (Generation {game_config.generation.value})")
    
    try:
        processor = VideoProcessor(
            video_path=args.video,
            game_config=game_config,
            downscale_factor=args.downscale,
            num_workers=args.workers,
            debug_ocr=args.debug_ocr,
            transition_jump=args.transition_jump,
            early_interval=args.early_interval,
            normal_interval=args.normal_interval
        )
        
        detections, battles = processor.analyze(detect_trainers=trainers)
        
        # Print results
        print("\n" + "=" * 70)
        print("BLACK/WHITE FRAME DETECTIONS")
        print("=" * 70)
        for d in detections[:50]:  # Limit output
            print(f"  {d}")
        if len(detections) > 50:
            print(f"  ... and {len(detections) - 50} more")
        print(f"\nTotal transitions: {len(detections)}")
        
        if battles:
            print("\n" + "=" * 70)
            print("BATTLE CUT POINTS")
            print("=" * 70)
            for battle in battles:
                print(battle)
                print()
            
            # Export to Timebolt JSON
            output_path = args.output or args.video.with_suffix('.json')
            video_duration = processor.total_frames / processor.fps
            export_timebolt_json(battles, video_duration, processor.fps, output_path)
            
            # Export to Automation Blocks JSON
            ab_output_path = output_path.with_name(output_path.stem + '_automation_blocks.json')
            export_automation_blocks_json(battles, processor.fps, ab_output_path)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

