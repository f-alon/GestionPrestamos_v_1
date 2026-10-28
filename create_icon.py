from PIL import Image, ImageDraw

def create_app_icon():
    # Create 256x256 image with rounded background and dollar/shield motif
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue modern gradient / rounded rect
    draw.rounded_rectangle([16, 16, 240, 240], radius=48, fill="#0078D4", outline="#005A9E", width=4)

    # Inner subtle glow/border
    draw.rounded_rectangle([24, 24, 232, 232], radius=40, outline="#60A5FA", width=2)

    # Draw a stylized '$' currency symbol in white
    # Top bar, S-curves, vertical stems
    draw.rectangle([120, 48, 136, 208], fill="#FFFFFF")  # vertical stem
    
    # White circles / arcs for '$'
    # Upper loop
    draw.arc([68, 70, 188, 140], start=90, end=270, fill="#FFFFFF", width=20)
    # Lower loop
    draw.arc([68, 116, 188, 186], start=270, end=90, fill="#FFFFFF", width=20)
    # Middle line
    draw.rectangle([80, 118, 176, 138], fill="#FFFFFF")
    # Top horizontal cap
    draw.rectangle([110, 70, 176, 90], fill="#FFFFFF")
    # Bottom horizontal cap
    draw.rectangle([80, 166, 146, 186], fill="#FFFFFF")

    os_dir = "resources"
    import os
    os.makedirs(os_dir, exist_ok=True)
    ico_path = os.path.join(os_dir, "app_icon.ico")
    png_path = os.path.join(os_dir, "app_icon.png")

    img.save(png_path, format="PNG")
    img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icons generated at: {ico_path} and {png_path}")

if __name__ == "__main__":
    create_app_icon()

