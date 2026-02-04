"""
Test OCR on Gen5 example images to debug trainer detection issues.
Tests the failure images and compares with successful ones.
"""

import cv2
import numpy as np
from PIL import Image
import os
from pathlib import Path

# OCR setup
try:
    import pytesseract
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
except ImportError:
    print("Error: pytesseract not installed")
    exit(1)

# Gen5 OCR region from fury_cutter.py
# Default: Region(x=1100, y=20, width=820, height=90)
OCR_REGION = {
    'x': 1100,
    'y': 20,
    'width': 820,
    'height': 90
}

# Test different crop sizes to see if smaller is better
TIGHT_OCR_REGION = {
    'x': 1100,
    'y': 20,
    'width': 400,  # Much smaller width
    'height': 50   # Smaller height
}

# Try a region that focuses on just the header text (top portion)
HEADER_ONLY_REGION = {
    'x': 1100,
    'y': 20,
    'width': 500,  # Medium width
    'height': 40   # Just the header line
}

# Test the new proposed region (500x50)
PROPOSED_REGION = {
    'x': 1100,
    'y': 20,
    'width': 500,
    'height': 50
}

# Try wider but shorter region (to capture full header text but avoid Pokemon info)
WIDE_SHORT_REGION = {
    'x': 1100,
    'y': 20,
    'width': 700,  # Wider to capture full header
    'height': 45   # Shorter to avoid Pokemon info
}

def has_text_like_content(ocr_crop, min_contrast=30, min_text_ratio=0.03, max_text_ratio=0.6):
    """
    Fast pre-screen from fury_cutter.py - check if region looks like it contains text.
    """
    gray = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2GRAY) if len(ocr_crop.shape) == 3 else ocr_crop
    
    min_val, max_val = gray.min(), gray.max()
    contrast = max_val - min_val
    if contrast < min_contrast:
        return False, f"Low contrast ({contrast})"
    
    threshold_value = np.percentile(gray, 20)
    _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
    
    text_pixels = np.sum(binary > 0)
    total_pixels = binary.size
    text_ratio = text_pixels / total_pixels
    
    if not (min_text_ratio <= text_ratio <= max_text_ratio):
        return False, f"Text ratio {text_ratio:.2%} outside {min_text_ratio:.0%}-{max_text_ratio:.0%}"
    
    return True, f"Passed (contrast={contrast}, ratio={text_ratio:.2%})"


def test_ocr_on_image(image_path, region, region_name="default"):
    """Test OCR on a single image with a specific region."""
    print(f"\n{'='*70}")
    print(f"Testing: {image_path.name} with {region_name} region")
    print(f"Region: x={region['x']}, y={region['y']}, w={region['width']}, h={region['height']}")
    print(f"{'='*70}")
    
    # Load image
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"ERROR: Could not load image {image_path}")
        return None
    
    img_height, img_width = img.shape[:2]
    print(f"Image size: {img_width}x{img_height}")
    
    # Check if region fits
    if region['x'] + region['width'] > img_width or region['y'] + region['height'] > img_height:
        print(f"WARNING: Region extends beyond image bounds!")
        print(f"  Region end: x={region['x'] + region['width']}, y={region['y'] + region['height']}")
        print(f"  Image size: {img_width}x{img_height}")
        # Adjust region to fit
        region['width'] = min(region['width'], img_width - region['x'])
        region['height'] = min(region['height'], img_height - region['y'])
        print(f"  Adjusted region: w={region['width']}, h={region['height']}")
    
    # Crop region
    ocr_crop = img[
        region['y'] : region['y'] + region['height'],
        region['x'] : region['x'] + region['width']
    ]
    
    # Save crop for inspection
    crop_path = image_path.parent / f"{image_path.stem}_crop_{region_name}.png"
    cv2.imwrite(str(crop_path), ocr_crop)
    print(f"Saved crop to: {crop_path.name}")
    
    # Pre-screen check
    has_text, text_msg = has_text_like_content(ocr_crop)
    print(f"Pre-screen: {text_msg}")
    
    if not has_text:
        print("  -> Skipping OCR (pre-screen failed)")
        return None
    
    # Convert BGR to RGB for PIL
    rgb_crop = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_crop)
    
    # Run OCR (Gen5 uses --psm 6)
    text = pytesseract.image_to_string(pil_image, config='--psm 6')
    
    # Clean text (same as fury_cutter.py)
    text_clean = ' '.join(text.split()).lower()
    text_clean = text_clean.replace('\ufffd', '').replace('\u200b', '').replace('\u00a0', ' ')
    text_clean = text_clean.strip('"\'`.,;:!?')
    text_clean = text_clean.strip('"\'')
    
    print(f"Raw OCR: '{text}'")
    print(f"Cleaned: '{text_clean}'")
    
    # Check for trainer patterns
    trainers_to_check = ["n", "marshal", "marshall"]
    print("\nTrainer pattern matching:")
    for trainer in trainers_to_check:
        # Gen5 pattern: "[trainer]'s team"
        pattern1 = f"{trainer}'s team"
        pattern2 = f"{trainer}s team"  # OCR sometimes misses apostrophe
        
        match1 = pattern1 in text_clean
        match2 = pattern2 in text_clean
        
        if match1 or match2:
            print(f"  [MATCH] {trainer}: MATCHED (pattern1={match1}, pattern2={match2})")
        else:
            print(f"  [NO MATCH] {trainer}: NOT MATCHED")
    
    return text_clean


def main():
    base_dir = Path(__file__).parent
    
    # Test failure images
    failures_dir = base_dir / "top_right_text_examples" / "gen5" / "ocr_failures"
    failures = [
        "ocr_failed_marshal.jpg",
        "ocr_failed_n_chargestone cave.jpg",
        "ocr_failed_n_final.jpg"
    ]
    
    # Test success images
    success_dir = base_dir / "top_right_text_examples" / "gen5" / "ocr success"
    successes = [
        "ocr_success_n_1.jpg",
        "ocr_success_n_amusement park.jpg"
    ]
    
    print("="*70)
    print("GEN5 OCR DEBUG TEST")
    print("="*70)
    
    # Test failures with default region
    print("\n\n" + "="*70)
    print("TESTING FAILURE IMAGES (default region)")
    print("="*70)
    for img_name in failures:
        img_path = failures_dir / img_name
        if img_path.exists():
            test_ocr_on_image(img_path, OCR_REGION, "default")
        else:
            print(f"WARNING: {img_path} not found")
    
    # Test failures with tight region
    print("\n\n" + "="*70)
    print("TESTING FAILURE IMAGES (tight region)")
    print("="*70)
    for img_name in failures:
        img_path = failures_dir / img_name
        if img_path.exists():
            test_ocr_on_image(img_path, TIGHT_OCR_REGION, "tight")
        else:
            print(f"WARNING: {img_path} not found")
    
    # Test successes with default region
    print("\n\n" + "="*70)
    print("TESTING SUCCESS IMAGES (default region)")
    print("="*70)
    for img_name in successes:
        img_path = success_dir / img_name
        if img_path.exists():
            test_ocr_on_image(img_path, OCR_REGION, "default")
        else:
            print(f"WARNING: {img_path} not found")
    
    # Test successes with tight region
    print("\n\n" + "="*70)
    print("TESTING SUCCESS IMAGES (tight region)")
    print("="*70)
    for img_name in successes:
        img_path = success_dir / img_name
        if img_path.exists():
            test_ocr_on_image(img_path, TIGHT_OCR_REGION, "tight")
        else:
            print(f"WARNING: {img_path} not found")
    
    # Test failures with header-only region
    print("\n\n" + "="*70)
    print("TESTING FAILURE IMAGES (header-only region)")
    print("="*70)
    for img_name in failures:
        img_path = failures_dir / img_name
        if img_path.exists():
            test_ocr_on_image(img_path, HEADER_ONLY_REGION, "header-only")
        else:
            print(f"WARNING: {img_path} not found")
    
    # Test successes with header-only region
    print("\n\n" + "="*70)
    print("TESTING SUCCESS IMAGES (header-only region)")
    print("="*70)
    for img_name in successes:
        img_path = success_dir / img_name
        if img_path.exists():
            test_ocr_on_image(img_path, HEADER_ONLY_REGION, "header-only")
        else:
            print(f"WARNING: {img_path} not found")
    
    # Test with proposed region (500x50)
    print("\n\n" + "="*70)
    print("TESTING FAILURE IMAGES (proposed 500x50 region)")
    print("="*70)
    for img_name in failures:
        img_path = failures_dir / img_name
        if img_path.exists():
            test_ocr_on_image(img_path, PROPOSED_REGION, "proposed")
        else:
            print(f"WARNING: {img_path} not found")
    
    print("\n\n" + "="*70)
    print("TESTING SUCCESS IMAGES (proposed 500x50 region)")
    print("="*70)
    for img_name in successes:
        img_path = success_dir / img_name
        if img_path.exists():
            test_ocr_on_image(img_path, PROPOSED_REGION, "proposed")
        else:
            print(f"WARNING: {img_path} not found")


if __name__ == "__main__":
    main()

