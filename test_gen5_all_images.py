"""
Test OCR on all Gen5 example images with the new optimized OCR region.
Tests all images in top_right_text_examples/gen5 to confirm trainer detection works.
"""

import cv2
import numpy as np
from PIL import Image
import os
from pathlib import Path
import re

# OCR setup
try:
    import pytesseract
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
except ImportError:
    print("Error: pytesseract not installed")
    exit(1)

# New optimized Gen5 OCR region
NEW_OCR_REGION = {
    'x': 1508,
    'y': 22,
    'width': 374,
    'height': 36
}

# Expected trainers in gen5 images
EXPECTED_TRAINERS = {
    "brycen.jpg": "brycen",
    "cheren's team.jpg": "cheren",
    "cress's team.jpg": "cress",
    "lenora's team.jpg": "lenora",
    "n_example_1.jpg": "n",
    "n_example_2.jpg": "n",
    "n's team.jpg": "n",
    "ocr_success_n_1.jpg": "n",
    "ocr_success_n_amusement park.jpg": "n",
    "ocr_failed_marshal.jpg": "marshal",
    "ocr_failed_n_chargestone cave.jpg": "n",
    "ocr_failed_n_final.jpg": "n",
    "skyla.jpg": "skyla",
    # These should NOT match
    "not_n_example_1.jpg": None,
    "not_n_example_2.jpg": None,
    "movepool.jpg": None,
    "splits.jpg": None,
}

def has_text_like_content(ocr_crop, min_contrast=30, min_text_ratio=0.03, max_text_ratio=0.6):
    """Fast pre-screen from fury_cutter.py."""
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
        return False, f"Text ratio {text_ratio:.2%} outside range"
    
    return True, f"OK (contrast={contrast}, ratio={text_ratio:.2%})"


def test_ocr_on_image(image_path, region, expected_trainer=None):
    """Test OCR on a single image and check if it matches expected trainer."""
    img = cv2.imread(str(image_path))
    if img is None:
        return None, f"ERROR: Could not load image"
    
    img_height, img_width = img.shape[:2]
    
    # Check if region fits
    if region['x'] + region['width'] > img_width or region['y'] + region['height'] > img_height:
        # Adjust region to fit
        region['width'] = min(region['width'], img_width - region['x'])
        region['height'] = min(region['height'], img_height - region['y'])
    
    # Crop region
    ocr_crop = img[
        region['y'] : region['y'] + region['height'],
        region['x'] : region['x'] + region['width']
    ]
    
    # Pre-screen check
    has_text, text_msg = has_text_like_content(ocr_crop)
    
    if not has_text:
        return None, f"Pre-screen failed: {text_msg}"
    
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
    
    # Check for trainer patterns (Gen5 pattern: "[trainer]'s team")
    detected_trainers = []
    all_trainers = ["n", "cheren", "bianca", "cress", "chili", "cilan",
                     "lenora", "burgh", "elesa", "clay", "skyla", "brycen",
                     "drayden", "shauntal", "marshal", "grimsley", "caitlin", "ghetsis"]
    
    for trainer in all_trainers:
        # Use word boundary to avoid matching "rolan's team" or "warren's team" as "n's team"
        # \b ensures the trainer name starts at a word boundary (not preceded by a letter)
        pattern = rf"\b{re.escape(trainer)}['']?s\s+team"
        
        if re.search(pattern, text_clean):
            detected_trainers.append(trainer)
    
    # Determine result
    if expected_trainer is None:
        # Should NOT match any trainer
        if detected_trainers:
            result = f"FALSE POSITIVE: Detected {detected_trainers}"
            status = "FAIL"
        else:
            result = "Correctly rejected (no trainer expected)"
            status = "PASS"
    else:
        # Should match expected trainer
        if expected_trainer in detected_trainers:
            result = f"Correctly detected: {expected_trainer}"
            status = "PASS"
        elif detected_trainers:
            result = f"WRONG TRAINER: Expected {expected_trainer}, got {detected_trainers}"
            status = "FAIL"
        else:
            result = f"MISSED: Expected {expected_trainer}, got nothing"
            status = "FAIL"
    
    return {
        'status': status,
        'result': result,
        'ocr_text': text_clean,
        'raw_ocr': text,
        'detected': detected_trainers,
        'expected': expected_trainer
    }


def main():
    base_dir = Path(__file__).parent
    gen5_dir = base_dir / "top_right_text_examples" / "gen5"
    
    print("="*70)
    print("GEN5 OCR TEST - New Region (1508, 22, 374, 36)")
    print("="*70)
    
    # Get all images
    all_images = []
    for ext in ['*.jpg', '*.png']:
        all_images.extend(gen5_dir.glob(ext))
        all_images.extend((gen5_dir / "ocr_failures").glob(ext))
        all_images.extend((gen5_dir / "ocr success").glob(ext))
    
    # Filter to only image files (not crop outputs)
    all_images = [img for img in all_images if 'crop' not in img.name.lower()]
    
    results = []
    for img_path in sorted(all_images):
        img_name = img_path.name
        expected = EXPECTED_TRAINERS.get(img_name)
        
        print(f"\n{'='*70}")
        print(f"Testing: {img_name}")
        if expected:
            print(f"Expected: {expected}")
        else:
            print(f"Expected: None (should not match)")
        print(f"{'='*70}")
        
        result = test_ocr_on_image(img_path, NEW_OCR_REGION, expected)
        if result:
            print(f"Status: {result['status']}")
            print(f"Result: {result['result']}")
            print(f"OCR text: '{result['ocr_text']}'")
            if result['raw_ocr'].strip() != result['ocr_text']:
                print(f"Raw OCR: '{result['raw_ocr']}'")
            results.append((img_name, result))
        else:
            print(f"Status: ERROR")
            results.append((img_name, {'status': 'ERROR', 'result': 'Could not process'}))
    
    # Summary
    print("\n\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, r in results if r.get('status') == 'PASS')
    failed = sum(1 for _, r in results if r.get('status') == 'FAIL')
    errors = sum(1 for _, r in results if r.get('status') == 'ERROR')
    
    print(f"Total images tested: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    
    if failed > 0 or errors > 0:
        print("\nFAILURES:")
        for img_name, result in results:
            if result.get('status') in ['FAIL', 'ERROR']:
                print(f"  {img_name}: {result.get('result', 'ERROR')}")
    
    return 0 if failed == 0 and errors == 0 else 1


if __name__ == "__main__":
    exit(main())

