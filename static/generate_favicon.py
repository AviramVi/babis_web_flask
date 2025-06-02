from PIL import Image, ImageDraw, ImageFont
import os

# Create a 32x32 image with a blue background
img = Image.new('RGB', (32, 32), color=(41, 128, 185))  # Blue color
draw = ImageDraw.Draw(img)

# Add a simple 'B' letter in the center
try:
    # Try to use a system font
    font = ImageFont.truetype("Arial", 24)
    draw.text((8, 2), "B", fill=(255, 255, 255), font=font)
except Exception:
    # If font loading fails, draw a simple shape instead
    draw.rectangle([8, 8, 24, 24], fill=(255, 255, 255))

# Save as ICO
img.save('static/favicon.ico')
print("Favicon created successfully")
