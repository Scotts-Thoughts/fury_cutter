"""
Test OCR on Gen3 example images to debug trainer detection issues.
"""

import cv2
import numpy as np
from PIL import Image
import os

# OCR setup
try:
    import pytesseract
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
except ImportError:
    print("Error: pytesseract not installed")
    exit(1)

# Gen3 OCR region from fury_cutter.py - adjusted for full frame images
# Original: Region(x=1584, y=25, width=322, height=31)
OCR_REGION = {
    'x': 1584,
    'y': 25,
    'width': 322,
    'height': 31
}

# Alternative: try a wider region to capture more of the header
WIDE_OCR_REGION = {
    'x': 1170,  # Start earlier to catch full text
    'y': 20,
    'width': 300,
    'height': 45
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


def test_ocr_on_image(image_path, region):
    """Test OCR on a single image."""
    print(f"\n{'='*60}")
    print(f"Testing: {os.path.basename(image_path)}")
    print(f"Region: x={region['x']}, y={region['y']}, w={region['width']}, h={region['height']}")
    
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        print(f"  ERROR: Could not read image")
        return None
    
    print(f"  Image size: {img.shape[1]}x{img.shape[0]}")
    
    # Crop to OCR region
    x, y, w, h = region['x'], region['y'], region['width'], region['height']
    
    # Check bounds
    if x + w > img.shape[1] or y + h > img.shape[0]:
        print(f"  ERROR: Region exceeds image bounds!")
        print(f"  Image: {img.shape[1]}x{img.shape[0]}, Region end: {x+w}x{y+h}")
        return None
    
    ocr_crop = img[y:y+h, x:x+w]
    
    # Save crop for debugging
    debug_name = f"debug_crop_{os.path.basename(image_path)}"
    cv2.imwrite(debug_name, ocr_crop)
    print(f"  Saved crop: {debug_name}")
    
    # Test the pre-screen filter (from fury_cutter.py)
    prescreen_pass, prescreen_reason = has_text_like_content(ocr_crop)
    print(f"  Pre-screen: {'PASS' if prescreen_pass else 'FAIL'} - {prescreen_reason}")
    
    # Check for text-like content (pre-screen)
    gray = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2GRAY)
    min_val, max_val = gray.min(), gray.max()
    contrast = max_val - min_val
    print(f"  Contrast: {contrast} (min={min_val}, max={max_val})")
    
    if contrast < 30:
        print(f"  WARNING: Low contrast - may not contain text")
    
    # Preprocessing for Gen3/Gen4 (leader pattern)
    threshold_value = np.percentile(gray, 20)
    print(f"  Threshold (20th percentile): {threshold_value}")
    
    _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
    processed = 255 - binary
    
    # Save processed image
    debug_proc = f"debug_proc_{os.path.basename(image_path)}"
    cv2.imwrite(debug_proc, processed)
    print(f"  Saved processed: {debug_proc}")
    
    # Run OCR
    pil_processed = Image.fromarray(processed)
    
    # Try different PSM modes
    for psm in [6, 7, 8, 13]:
        try:
            text = pytesseract.image_to_string(pil_processed, config=f'--psm {psm}')
            text_clean = ' '.join(text.split()).lower()
            if text_clean.strip():
                print(f"  OCR (psm {psm}): '{text_clean}'")
        except Exception as e:
            print(f"  OCR (psm {psm}): Error - {e}")
    
    # Also try raw (no preprocessing)
    rgb_crop = cv2.cvtColor(ocr_crop, cv2.COLOR_BGR2RGB)
    pil_raw = Image.fromarray(rgb_crop)
    try:
        text_raw = pytesseract.image_to_string(pil_raw, config='--psm 6')
        text_clean = ' '.join(text_raw.split()).lower()
        print(f"  OCR (raw): '{text_clean}'")
    except Exception as e:
        print(f"  OCR (raw): Error - {e}")
    
    return text_clean


def main():
    # Get all gen3 example images
    gen3_dir = "top_right_text_examples/gen3"
    
    if not os.path.exists(gen3_dir):
        print(f"Error: Directory not found: {gen3_dir}")
        return
    
    image_files = [f for f in os.listdir(gen3_dir) if f.endswith('.jpg')]
    
    print(f"Found {len(image_files)} Gen3 example images")
    print("Testing with standard region first...")
    
    for image_file in sorted(image_files):
        image_path = os.path.join(gen3_dir, image_file)
        test_ocr_on_image(image_path, OCR_REGION)
    
    print(f"\n{'='*60}")
    print("Testing with WIDER region...")
    print(f"{'='*60}")
    
    for image_file in sorted(image_files):
        image_path = os.path.join(gen3_dir, image_file)
        test_ocr_on_image(image_path, WIDE_OCR_REGION)


if __name__ == "__main__":
    main()

