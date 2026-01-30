"""Find the Gen3 header region by analyzing the image."""
import cv2
import numpy as np

# Load a sample image
img = cv2.imread('top_right_text_examples/gen3/brock.jpg')
h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# The header "Leader Brock" appears in the TOP RIGHT area
# Let's crop progressively from the right side to find it

# Try different regions
test_regions = [
    # Looking at the visible text "Leader Brock" which should be around top-right
    (1160, 0, w-1160, 60),   # Far right, top
    (1180, 5, w-1180, 55),   # Adjusted
    (1200, 10, w-1200, 50),  # More adjusted
]

for i, (x, y, rw, rh) in enumerate(test_regions):
    crop = img[y:y+rh, x:x+rw]
    cv2.imwrite(f"debug_gen3_region_{i}.jpg", crop)
    print(f"Region {i}: x={x}, y={y}, w={rw}, h={rh} -> saved debug_gen3_region_{i}.jpg")

# Let's also just crop the top-right 500x100 pixels to see what's there
top_right = img[0:100, w-500:w]
cv2.imwrite("debug_gen3_top_right.jpg", top_right)
print(f"\nTop-right 500x100 saved to debug_gen3_top_right.jpg")

# And the full right side
right_panel = img[0:200, 1160:w]
cv2.imwrite("debug_gen3_right_panel.jpg", right_panel)
print(f"Right panel (x=1160 to end, h=200) saved to debug_gen3_right_panel.jpg")

