"""
carousel/carousel_gen.py
Generates carousel slides as 1080x1080px PNGs compiled into a single PDF.
Uses Pillow only — no external design tools.
All design decisions from PRD Section 11/12 are hard-coded here.
"""

import os
import io
import textwrap
from PIL import Image, ImageDraw, ImageFont
try:
    from pilmoji import Pilmoji
except ImportError:
    Pilmoji = None

from utils.logger import get_logger, log_error
from config.settings import (
    CAROUSEL_CANVAS_SIZE, CAROUSEL_MARGIN, CAROUSEL_CONTENT_SIZE,
    CAROUSEL_MAX_SLIDES, CAROUSEL_MAX_WORDS_PER_SLIDE,
    CAROUSEL_COLORS as C, CAROUSEL_FONTS as F,
    CAROUSEL_OUTPUT_DIR,
)

log = get_logger("carousel")

# Content zone
CONTENT_X = CAROUSEL_MARGIN
CONTENT_Y = CAROUSEL_MARGIN
CONTENT_W = CAROUSEL_CONTENT_SIZE
CONTENT_H = CAROUSEL_CONTENT_SIZE


# ─────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────

def generate_carousel_pdf(carousel_data: dict, output_filename: str = "carousel.pdf") -> str:
    """
    Generate carousel slides and save as PDF.
    Returns the path to the generated PDF.
    """
    os.makedirs(CAROUSEL_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(CAROUSEL_OUTPUT_DIR, output_filename)

    slides = carousel_data.get("slides", [])
    if len(slides) > CAROUSEL_MAX_SLIDES:
        slides = slides[:CAROUSEL_MAX_SLIDES]

    images = []
    for i, slide_data in enumerate(slides):
        try:
            img = _render_slide(slide_data, slide_number=i, total=len(slides))
            images.append(img)
        except Exception as e:
            log_error(f"Failed to render slide {i}", e)
            log.warning(f"Skipping slide {i} due to render error")

    if not images:
        raise ValueError("No slides could be rendered")

    # Save as multi-page PDF using Pillow
    images[0].save(
        output_path,
        format="PDF",
        save_all=True,
        append_images=images[1:],
        resolution=144,
    )

    log.info(f"Carousel PDF saved: {output_path} ({len(images)} slides)")
    return output_path


def generate_carousel_pngs(carousel_data: dict) -> list[str]:
    """Generate individual PNG files for each slide. Returns list of paths."""
    os.makedirs(CAROUSEL_OUTPUT_DIR, exist_ok=True)
    slides = carousel_data.get("slides", [])[:CAROUSEL_MAX_SLIDES]
    paths = []

    for i, slide_data in enumerate(slides):
        try:
            img = _render_slide(slide_data, slide_number=i, total=len(slides))
            path = os.path.join(CAROUSEL_OUTPUT_DIR, f"slide_{i+1:02d}.png")
            img.save(path, format="PNG", dpi=(144, 144))
            paths.append(path)
        except Exception as e:
            log_error(f"Failed to render slide PNG {i}", e)

    return paths


# ─────────────────────────────────────────────────────────────────
# SLIDE ROUTER
# ─────────────────────────────────────────────────────────────────

def _render_slide(slide_data: dict, slide_number: int, total: int) -> Image.Image:
    """Route to correct slide renderer based on type."""
    slide_type = slide_data.get("type", "content")

    if slide_type == "cover" or slide_number == 0:
        return _render_cover(slide_data)
    elif slide_type == "cta" or slide_number == total - 1:
        return _render_cta(slide_data, slide_number)
    else:
        return _render_content(slide_data, slide_number)


# ─────────────────────────────────────────────────────────────────
# FONT LOADING
# ─────────────────────────────────────────────────────────────────

_font_cache = {}

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except (OSError, IOError):
            log.warning(f"Font not found: {path} — using default")
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def _headline_font(size: int = None):
    return _load_font(F["headline_path"], size or F["headline_size"])

def _headline_content_font():
    return _load_font(F["headline_path"], F["headline_size_content"])

def _body_font(size: int = None):
    return _load_font(F["body_path"], size or F["body_size"])

def _semibold_font(size: int = None):
    return _load_font(F["semibold_path"], size or F["body_size"])


# ─────────────────────────────────────────────────────────────────
# SLIDE RENDERERS
# ─────────────────────────────────────────────────────────────────

def _render_cover(slide_data: dict) -> Image.Image:
    """Slide 1 — sage green background, big headline, no footer."""
    img = Image.new("RGB", (CAROUSEL_CANVAS_SIZE, CAROUSEL_CANVAS_SIZE), C["cover_bg"])
    draw = ImageDraw.Draw(img)

    category = slide_data.get("category_label", "AI TOOLS").upper()
    if "🌿" not in category:
        category = f"🌿 {category}"
    heading = slide_data.get("heading", "")
    subheading = slide_data.get("subheading", "")

    # Measure everything first, then center vertically
    cat_font = _semibold_font(F["label_size"])
    head_font = _headline_font(F["headline_size"])
    sub_font = _body_font(F["subheadline_size"])

    cat_h = _text_height(draw, category, cat_font, CONTENT_W)
    head_h = _text_height(draw, heading, head_font, CONTENT_W)
    sub_h = _text_height(draw, subheading, sub_font, CONTENT_W) if subheading else 0

    gap1, gap2 = 24, 20
    total_h = cat_h + gap1 + head_h + (gap2 + sub_h if subheading else 0)
    start_y = CONTENT_Y + (CONTENT_H - total_h) // 2

    # Draw category label
    y = start_y
    if Pilmoji is not None and "🌿" in category:
        # Measure using pilmoji context
        with Pilmoji(img) as pilmoji:
            # textbbox isn't easily supported for emojis without custom logic, 
            # so we use a slightly rough approximation of width, or standard bbox
            # Actually Pilmoji can just draw. For centering:
            bbox = draw.textbbox((0, 0), category, font=cat_font)
            line_w = bbox[2] - bbox[0]
            # Add a bit of width for the emoji offset
            line_w += 20
            x = CONTENT_X + (CONTENT_W - line_w) // 2
            pilmoji.text((x, y), category, font=cat_font, fill=C["muted_text"])
    else:
        _draw_centered_text(draw, category, cat_font, C["muted_text"], y, max_width=CONTENT_W)
        
    y += cat_h + gap1

    # Draw main headline (may wrap)
    _draw_centered_text(draw, heading, head_font, C["primary_text"], y, max_width=CONTENT_W)
    y += head_h + gap2

    # Draw subheadline
    if subheading:
        _draw_centered_text(draw, subheading, sub_font, C["muted_text"], y, max_width=CONTENT_W)

    return img


def _render_content(slide_data: dict, slide_number: int) -> Image.Image:
    """Content slides 2-4 — warm cream, slide number top-left, footer bottom."""
    img = Image.new("RGB", (CAROUSEL_CANVAS_SIZE, CAROUSEL_CANVAS_SIZE), C["content_bg"])
    draw = ImageDraw.Draw(img)

    heading = slide_data.get("heading", "")
    body = slide_data.get("body", "")
    highlight = slide_data.get("highlight_phrase", "")
    bullets = slide_data.get("bullets", [])

    # Slide number — top left
    num_font = _body_font(F["slide_num_size"])
    draw.text(
        (CONTENT_X, CONTENT_Y),
        f"{slide_number:02d}",
        font=num_font,
        fill=C["muted_text"],
    )

    head_font = _headline_content_font()
    body_font = _body_font()

    head_h = _text_height(draw, heading, head_font, CONTENT_W)
    body_h = _text_height(draw, body, body_font, CONTENT_W) if body else 0

    gap_head_body = 60
    total_h = head_h + gap_head_body + body_h
    start_y = CONTENT_Y + (CONTENT_H - total_h) // 2

    y = start_y
    _draw_centered_text(draw, heading, head_font, C["primary_text"], y, max_width=CONTENT_W)
    y += head_h + gap_head_body

    if bullets:
        y = _draw_bullets(draw, bullets, y)
    elif body:
        if highlight and highlight in body:
            y = _draw_body_with_highlight(draw, body, body_font, highlight, y)
        else:
            y = _draw_body_paragraphs(draw, body, body_font, C["body_text"], y)

    return img


def _render_cta(slide_data: dict, slide_number: int) -> Image.Image:
    """Final CTA slide — slightly warmer cream, yellow highlight for hero phrase."""
    img = Image.new("RGB", (CAROUSEL_CANVAS_SIZE, CAROUSEL_CANVAS_SIZE), C["cta_bg"])
    draw = ImageDraw.Draw(img)

    heading = slide_data.get("heading", "the bottom line")
    body = slide_data.get("body", "")
    highlight = slide_data.get("highlight_phrase", "")

    head_font = _headline_content_font()
    body_font = _body_font()

    head_h = _text_height(draw, heading, head_font, CONTENT_W)
    body_h = _text_height(draw, body, body_font, CONTENT_W) if body else 0

    total_h = head_h + 32 + body_h + (40 if highlight else 0)
    start_y = CONTENT_Y + (CONTENT_H - total_h) // 2

    y = start_y
    _draw_centered_text(draw, heading, head_font, C["primary_text"], y, max_width=CONTENT_W)
    y += head_h + 32

    if body:
        _draw_centered_text(draw, body, body_font, C["body_text"], y, max_width=CONTENT_W)
        y += body_h + 24

    if highlight:
        _draw_highlight_box(draw, highlight, body_font, C["highlight_yellow"],
                            C["primary_text"], y, CONTENT_X, CONTENT_W)

    return img


# ─────────────────────────────────────────────────────────────────
# DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────

def _get_line_height(font) -> int:
    """Return tighter line height for larger headline fonts, standard for body."""
    if font.size >= 60:
        return int(font.size * 1.1)
    return int(font.size * 1.4)

def _draw_centered_text(draw, text: str, font, color: str, y: int, max_width: int):
    """Draw word-wrapped text centered horizontally."""
    lines = _wrap_text(draw, text, font, max_width)
    line_h = _get_line_height(font)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = CONTENT_X + (max_width - line_w) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += line_h


def _text_height(draw, text: str, font, max_width: int) -> int:
    """Calculate total height of wrapped text block."""
    lines = _wrap_text(draw, text, font, max_width)
    line_h = _get_line_height(font)
    return len(lines) * line_h


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = []

    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)

    if current:
        lines.append(" ".join(current))

    return lines or [text]


def _draw_highlight_box(draw, text: str, font, bg_color: str, text_color: str,
                         y: int, x_offset: int, max_width: int):
    """Draw text with a rounded-rect highlight background, centered."""
    lines = _wrap_text(draw, text, font, max_width - 40)
    padding_h, padding_v = 16, 10
    radius = 8
    line_h = _get_line_height(font)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        rect_w = text_w + padding_h * 2
        rect_x = x_offset + (max_width - rect_w) // 2
        rect = [rect_x, y - padding_v, rect_x + rect_w, y + font.size + padding_v]

        draw.rounded_rectangle(rect, radius=radius, fill=bg_color)
        draw.text((rect_x + padding_h, y), line, font=font, fill=text_color)
        y += line_h + padding_v


def _draw_body_paragraphs(draw, body: str, font, color: str, y: int) -> int:
    """Draw body text with spacing between double newlines."""
    paragraphs = body.split("\n\n")
    for i, p in enumerate(paragraphs):
        p = p.strip()
        if not p:
            continue
        _draw_centered_text(draw, p, font, color, y, max_width=CONTENT_W)
        y += _text_height(draw, p, font, CONTENT_W) + (40 if i < len(paragraphs) - 1 else 0)
    return y

def _draw_body_with_highlight(draw, body: str, font, highlight: str, y: int) -> int:
    """
    Draw body text, rendering the highlight_phrase with a green background box
    and the rest as plain text. Returns new y after all text is drawn.
    """
    if not highlight or highlight not in body:
        return _draw_body_paragraphs(draw, body, font, C["body_text"], y)

    parts = body.split(highlight, 1)
    before = parts[0].strip()
    after = parts[1].strip() if len(parts) > 1 else ""

    if before:
        y = _draw_body_paragraphs(draw, before, font, C["body_text"], y)
        y += 40  # paragraph gap

    # Highlighted phrase
    _draw_highlight_box(draw, highlight, font, C["highlight_yellow"],
                        C["primary_text"], y, CONTENT_X, CONTENT_W)
    y += _text_height(draw, highlight, font, CONTENT_W) + 40

    if after:
        y = _draw_body_paragraphs(draw, after, font, C["body_text"], y)

    return y


def _draw_bullets(draw, bullets: list[str], start_y: int) -> int:
    """Draw bullet list with coral dots and green highlight boxes."""
    body_font = _body_font()
    dot_r = 10
    gap = 28
    padding_h, padding_v = 12, 8
    radius = 6
    x_start = CONTENT_X + 40
    dot_x = CONTENT_X + 20
    max_text_w = CONTENT_W - 60

    y = start_y
    for bullet in bullets[:3]:
        line_h = _get_line_height(body_font)
        cy = y + body_font.size // 2

        # Coral dot
        draw.ellipse(
            [dot_x - dot_r, cy - dot_r, dot_x + dot_r, cy + dot_r],
            fill=C["coral"],
        )

        # Green highlight box behind text
        bbox = draw.textbbox((0, 0), bullet, font=body_font)
        text_w = min(bbox[2] - bbox[0], max_text_w)
        rect = [
            x_start - padding_h,
            y - padding_v,
            x_start + text_w + padding_h,
            y + body_font.size + padding_v,
        ]
        draw.rounded_rectangle(rect, radius=radius, fill=C["highlight_green"])
        draw.text((x_start, y), bullet, font=body_font, fill=C["primary_text"])

        y += line_h + gap

    return y
