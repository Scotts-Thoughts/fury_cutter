from PIL import Image
import os

# Open the lenora example
examples = os.listdir('top_right_text_examples')
lenora_file = [f for f in examples if 'lenora' in f.lower()][0]
img = Image.open(os.path.join('top_right_text_examples', lenora_file))
print(f'Full image size: {img.size}')

# Save different crops to find the right region
crops = [
    ('header_full_right', (1100, 0, 1920, 100)),
    ('header_top_right', (1100, 0, 1450, 60)),
    ('header_narrow', (1200, 15, 1400, 50)),
    ('header_wide', (1100, 5, 1500, 80)),
]

for name, box in crops:
    crop = img.crop(box)
    crop.save(f'debug_{name}.png')
    print(f'Saved debug_{name}.png - size {crop.size}')

# Also save the same crops from cress example
cress_file = [f for f in examples if 'cress' in f.lower()][0]
img2 = Image.open(os.path.join('top_right_text_examples', cress_file))
crop2 = img2.crop((1100, 0, 1450, 60))
crop2.save('debug_cress_header.png')
print('Saved debug_cress_header.png')

