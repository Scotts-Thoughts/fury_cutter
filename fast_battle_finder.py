"""
Fast Battle Finder - Optimized battle detection using multiple strategies.

Strategies:
1. Black frame detection first - find all transitions
2. Color-based header detection - check if battle header colors present
3. Template matching - fast pattern matching for text
4. OCR fallback - only when needed for confirmation

Expected speedup: 10-50x faster than OCR-only approach
"""

import cv2
import numpy as np
from pathlib import Path
import time
from dataclasses import dataclass
from typing import Optional, List, Tuple
import os

# Try to import OCR for fallback
try:
    import pytesseract
    from PIL import Image
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


@dataclass
class BattleCandidate:
    """A potential battle location found by fast detection."""
    frame_start: int
    frame_end: int
    confidence: float
    detection_method: str
    trainer_hint: Optional[str] = None


class FastBattleFinder:
    """
    Fast battle detection using multiple strategies.
    """
    
    # Gen4 specific colors (HSV ranges for battle header backgrounds)
    # Blue header background for Gen4
    HEADER_COLOR_RANGES = {
        "gen4_blue": {
            "lower": np.array([100, 50, 50]),   # Blue hue, some saturation
            "upper": np.array([130, 255, 255]),
        },
        "gen4_tan": {
            "lower": np.array([15, 30, 100]),   # Tan/brown hue
            "upper": np.array([30, 150, 200]),
        },
    }
    
    def __init__(self, video_path: Path, 
                 header_region: Tuple[int, int, int, int],  # x, y, w, h
                 gameplay_region: Tuple[int, int, int, int],
                 fps: float = 240.0):
        self.video_path = video_path
        self.header_region = header_region
        self.gameplay_region = gameplay_region
        self.fps = fps
        
        # Get video info
        cap = cv2.VideoCapture(str(video_path))
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        print(f"FastBattleFinder initialized:")
        print(f"  Video: {video_path.name}")
        print(f"  Frames: {self.total_frames} ({self.total_frames/self.video_fps:.1f}s)")
    
    def _get_frame(self, cap, frame_num: int) -> Optional[np.ndarray]:
        """Get a specific frame from video."""
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        return frame if ret else None
    
    def _is_black_frame(self, frame: np.ndarray, threshold: float = 5.0) -> bool:
        """Check if gameplay region is black."""
        x, y, w, h = self.gameplay_region
        crop = frame[y:y+h, x:x+w]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        # Downscale for speed
        small = cv2.resize(gray, (0, 0), fx=0.25, fy=0.25)
        return small.mean() < threshold
    
    def _is_white_frame(self, frame: np.ndarray, threshold: float = 250.0) -> bool:
        """Check if gameplay region is white."""
        x, y, w, h = self.gameplay_region
        crop = frame[y:y+h, x:x+w]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (0, 0), fx=0.25, fy=0.25)
        return small.mean() > threshold
    
    def _has_battle_header_color(self, frame: np.ndarray) -> Tuple[bool, str]:
        """
        Check if the header region has battle-like colors.
        Returns (has_color, color_type).
        """
        x, y, w, h = self.header_region
        crop = frame[y:y+h, x:x+w]
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        
        for color_name, ranges in self.HEADER_COLOR_RANGES.items():
            mask = cv2.inRange(hsv, ranges["lower"], ranges["upper"])
            ratio = np.sum(mask > 0) / mask.size
            if ratio > 0.3:  # At least 30% of header has this color
                return True, color_name
        
        return False, ""
    
    def _has_text_contrast(self, frame: np.ndarray) -> bool:
        """Quick check if header has text-like contrast."""
        x, y, w, h = self.header_region
        crop = frame[y:y+h, x:x+w]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        
        # Check for bimodal distribution (text on background)
        contrast = gray.max() - gray.min()
        return contrast > 40
    
    def find_black_transitions(self, sample_interval: int = 240) -> List[int]:
        """
        Fast scan to find all black frame transitions.
        These mark potential battle boundaries.
        
        Returns list of frame numbers where black frames start.
        """
        print(f"\n[1/4] Scanning for black transitions (interval={sample_interval})...")
        
        cap = cv2.VideoCapture(str(self.video_path))
        transitions = []
        was_black = False
        
        start_time = time.perf_counter()
        samples = 0
        
        for frame_num in range(0, self.total_frames, sample_interval):
            frame = self._get_frame(cap, frame_num)
            if frame is None:
                continue
            
            is_black = self._is_black_frame(frame) or self._is_white_frame(frame)
            samples += 1
            
            if is_black and not was_black:
                transitions.append(frame_num)
            
            was_black = is_black
            
            if samples % 100 == 0:
                pct = frame_num / self.total_frames * 100
                print(f"  {pct:.0f}% scanned...", end='\r')
        
        cap.release()
        elapsed = time.perf_counter() - start_time
        
        print(f"  Found {len(transitions)} transitions in {elapsed:.1f}s ({samples} samples)")
        return transitions
    
    def check_battle_between_transitions(self, 
                                         transitions: List[int],
                                         check_interval: int = 480) -> List[BattleCandidate]:
        """
        For each pair of transitions, check if there's a battle between them.
        Uses color detection first (fast), then OCR fallback if needed.
        """
        print(f"\n[2/4] Checking for battles between transitions...")
        
        candidates = []
        cap = cv2.VideoCapture(str(self.video_path))
        
        start_time = time.perf_counter()
        
        for i in range(len(transitions) - 1):
            start = transitions[i]
            end = transitions[i + 1]
            
            # Skip if too short (< 5 seconds) or too long (> 10 minutes)
            duration_frames = end - start
            duration_sec = duration_frames / self.video_fps
            
            if duration_sec < 5 or duration_sec > 600:
                continue
            
            # Check middle of the segment for battle header
            mid_frame = start + duration_frames // 2
            frame = self._get_frame(cap, mid_frame)
            if frame is None:
                continue
            
            # Fast color check
            has_color, color_type = self._has_battle_header_color(frame)
            has_contrast = self._has_text_contrast(frame)
            
            if has_color and has_contrast:
                candidates.append(BattleCandidate(
                    frame_start=start,
                    frame_end=end,
                    confidence=0.7,
                    detection_method=f"color:{color_type}",
                ))
        
        cap.release()
        elapsed = time.perf_counter() - start_time
        
        print(f"  Found {len(candidates)} potential battles in {elapsed:.1f}s")
        return candidates
    
    def confirm_with_ocr(self, candidates: List[BattleCandidate], 
                         trainers: List[str]) -> List[BattleCandidate]:
        """
        Confirm battle candidates using OCR (only run on candidates, not full video).
        """
        if not OCR_AVAILABLE:
            print("  OCR not available, skipping confirmation")
            return candidates
        
        print(f"\n[3/4] Confirming {len(candidates)} candidates with OCR...")
        
        confirmed = []
        cap = cv2.VideoCapture(str(self.video_path))
        
        start_time = time.perf_counter()
        
        for candidate in candidates:
            # Check a frame in the middle of the battle
            mid = candidate.frame_start + (candidate.frame_end - candidate.frame_start) // 2
            frame = self._get_frame(cap, mid)
            if frame is None:
                continue
            
            x, y, w, h = self.header_region
            crop = frame[y:y+h, x:x+w]
            
            # Quick OCR
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            threshold_value = np.percentile(gray, 20)
            _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
            processed = 255 - binary
            pil_img = Image.fromarray(processed)
            
            text = pytesseract.image_to_string(pil_img, config='--psm 6').lower()
            
            # Check if any trainer name is in the text
            for trainer in trainers:
                if trainer.lower() in text or (trainer == "rival" and "rival" in text):
                    candidate.trainer_hint = trainer
                    candidate.confidence = 0.95
                    candidate.detection_method += "+ocr"
                    confirmed.append(candidate)
                    print(f"  Confirmed: {trainer} @ frame {mid} ({mid/self.video_fps:.1f}s)")
                    break
        
        cap.release()
        elapsed = time.perf_counter() - start_time
        
        print(f"  Confirmed {len(confirmed)} battles in {elapsed:.1f}s")
        return confirmed
    
    def find_battles_fast(self, trainers: List[str], 
                          sample_interval: int = 240) -> List[BattleCandidate]:
        """
        Main entry point - find all battles using fast multi-stage approach.
        
        1. Find black/white transitions (very fast)
        2. Check for battle colors between transitions (fast)
        3. Confirm with OCR only on candidates (slow but limited)
        """
        total_start = time.perf_counter()
        
        # Stage 1: Find transitions
        transitions = self.find_black_transitions(sample_interval)
        
        # Stage 2: Color-based filtering
        candidates = self.check_battle_between_transitions(transitions)
        
        # Stage 3: OCR confirmation
        confirmed = self.confirm_with_ocr(candidates, trainers)
        
        total_elapsed = time.perf_counter() - total_start
        
        print(f"\n[4/4] Complete!")
        print(f"  Total time: {total_elapsed:.1f}s")
        print(f"  Battles found: {len(confirmed)}")
        
        return confirmed


def benchmark_comparison(video_path: str):
    """Compare fast finder vs current approach."""
    from fury_cutter import VideoProcessor, GAME_CONFIGS
    
    video = Path(video_path)
    config = GAME_CONFIGS["platinum"]
    
    print("=" * 70)
    print("BENCHMARK: Fast Battle Finder vs Current Approach")
    print("=" * 70)
    
    # Fast approach
    print("\n--- FAST APPROACH ---")
    finder = FastBattleFinder(
        video,
        header_region=(config.ocr_region.x, config.ocr_region.y, 
                      config.ocr_region.width, config.ocr_region.height),
        gameplay_region=(config.gameplay_region.x, config.gameplay_region.y,
                        config.gameplay_region.width, config.gameplay_region.height),
    )
    
    fast_start = time.perf_counter()
    battles = finder.find_battles_fast(config.trainers)
    fast_time = time.perf_counter() - fast_start
    
    print(f"\nFast approach: {fast_time:.1f}s, found {len(battles)} battles")
    
    return battles


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        benchmark_comparison(sys.argv[1])
    else:
        print("Usage: python fast_battle_finder.py <video_path>")
        print("\nThis will benchmark the fast battle detection approach.")

