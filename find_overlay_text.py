import pytesseract
from PIL import Image
import os

# Set Tesseract path
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Load an example with known trainer name
examples = os.listdir('top_right_text_examples')
lenora_file = [f for f in examples if 'lenora' in f.lower()][0]
img = Image.open(os.path.join('top_right_text_examples', lenora_file))
print(f'Image: {lenora_file}')
print(f'Size: {img.size}')

# Save the full right side for visual inspection
right_side = img.crop((1100, 0, 1920, 400))
right_side.save('debug_right_side_full.png')
print('Saved debug_right_side_full.png - CHECK THIS IMAGE to see where the text is')

# Try OCR on different horizontal strips of the right side
print('\nScanning different Y positions for text...')
for y_start in range(0, 200, 20):
    y_end = y_start + 50
    strip = img.crop((1100, y_start, 1920, y_end))
    text = pytesseract.image_to_string(strip, config='--psm 6')
    text_clean = ' '.join(text.split()).strip()
    if text_clean and len(text_clean) > 3:
        print(f'  Y {y_start}-{y_end}: "{text_clean}"')
        if 'lenora' in text_clean.lower():
            print(f'    >>> FOUND LENORA at Y={y_start}-{y_end}')
            # Save this strip
            strip.save(f'debug_found_strip_y{y_start}.png')

