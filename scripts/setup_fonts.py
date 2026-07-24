"""
scripts/setup_fonts.py
Downloads the required fonts for carousel generation.
Run once after cloning the repo.

Usage:
    python scripts/setup_fonts.py
"""

import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FONTS_DIR = "carousel/assets/fonts"

# Google Fonts direct download URLs (static/non-variable versions)
FONTS = {
    "Inter-Regular.ttf": (
        "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf",
        "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZthiI-Ek-_EeA.woff2"
    ),
    "PlayfairDisplay-Bold.ttf": (
        "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
        None,
    ),
    "Inter-SemiBold.ttf": None,  # Will copy from Inter variable and rename
}

# Actual reliable download URLs
FONT_URLS = {
    "Inter-Regular.ttf": "https://github.com/google/fonts/raw/refs/heads/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf",
    "PlayfairDisplay-Bold.ttf": "https://github.com/google/fonts/raw/refs/heads/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
}


def main():
    os.makedirs(FONTS_DIR, exist_ok=True)
    print(f"Downloading fonts to {FONTS_DIR}/\n")

    for filename, url in FONT_URLS.items():
        dest = os.path.join(FONTS_DIR, filename)
        if os.path.exists(dest):
            print(f"  + {filename} already exists")
            continue

        print(f"  -> {filename}...")
        try:
            urllib.request.urlretrieve(url, dest)
            size = os.path.getsize(dest)
            print(f"  + {filename} ({size // 1024}KB)")
        except Exception as e:
            print(f"  x {filename} failed: {e}")
            print(f"    Download manually from: {url}")
            print(f"    Save to: {dest}")

    # Inter-SemiBold: copy from Inter variable (it's a variable font — same file works)
    inter_src = os.path.join(FONTS_DIR, "Inter-Regular.ttf")
    inter_semi = os.path.join(FONTS_DIR, "Inter-SemiBold.ttf")
    if os.path.exists(inter_src) and not os.path.exists(inter_semi):
        import shutil
        shutil.copy(inter_src, inter_semi)
        print(f"  + Inter-SemiBold.ttf (copied from Inter variable font)")

    print("\nFont setup complete.")
    print("Note: Inter is a variable font — Regular/SemiBold use the same file.")


if __name__ == "__main__":
    main()
