"""
carousel/carousel_gen.py
Generates carousel slides as 1080x1080px PNGs compiled into a single PDF.
Uses Pillow only — no external design tools.

Visual style: original sage-green/cream palette.
Text rendering: fixed — proper word-wrap, left-aligned body, correct sizing.
"""

import os
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

# Layout constants (unchanged from original)
SIZE      = CAROUSEL_CANVAS_SIZE    # 1080
MARGIN    = CAROUSEL_MARGIN         # 80
INNER     = CAROUSEL_CONTENT_SIZE   # 920  (SIZE - 2*MARGIN)

# Content start positions
CX = MARGIN     # left edge of content zone
CY = MARGIN     # top edge of content zone
CW = INNER      # usable width
CH = INNER      # usable height

# ─────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────

def generate_carousel_pdf(carousel_data: dict, output_filename: str = "carousel.pdf") -> str:
    """Generate carousel slides and save as PDF. Returns path to PDF."""
    os.makedirs(CAROUSEL_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(CAROUSEL_OUTPUT_DIR, output_filename)

    slides = carousel_data.get("slides", [])
    if len(slides) > CAROUSEL_MAX_SLIDES:
        slides = slides[:CAROUSEL_MAX_SLIDES]

    images = []
    total = len(slides)
    for i, slide_data in enumerate(slides):
        try:
            img = _render_slide(slide_data, slide_number=i, total=total)
            images.append(img)
        except Exception as e:
            log_error(f"Failed to render slide {i}", e)
            log.warning(f"Skipping slide {i} due to render error")

    if not images:
        raise ValueError("No slides could be rendered")

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
    total  = len(slides)
    paths  = []

    for i, slide_data in enumerate(slides):
        try:
            img  = _render_slide(slide_data, slide_number=i, total=total)
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
    slide_type = slide_data.get("type", "content")
    if slide_type == "cover" or slide_number == 0:
        return _render_cover(slide_data, total)
    elif slide_type == "cta" or slide_number == total - 1:
        return _render_cta(slide_data, slide_number, total)
    else:
        return _render_content(slide_data, slide_number, total)


# ─────────────────────────────────────────────────────────────────
# FONT CACHE
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

def _headline_content_font(size: int = None):
    return _load_font(F["headline_path"], size or F["headline_size_content"])

def _body_font(size: int = None):
    return _load_font(F["body_path"], size or F["body_size"])

def _semibold_font(size: int = None):
    return _load_font(F["semibold_path"], size or F["body_size"])


# ─────────────────────────────────────────────────────────────────
# SLIDE RENDERERS — original aesthetic, fixed text rendering
# ─────────────────────────────────────────────────────────────────

def _render_cover(slide_data: dict, total: int) -> Image.Image:
    """
    Slide 1 — sage green background, centered layout.
    Original design preserved. Category label gets the leaf emoji.
    Slide counter shown bottom-right.
    """
    img  = Image.new("RGB", (SIZE, SIZE), C["cover_bg"])
    draw = ImageDraw.Draw(img)

    # ── Slide counter — bottom right ────────────────────────────
    num_font    = _semibold_font(F["slide_num_size"])
    counter     = f"01 / {total:02d}"
    ct_bbox     = draw.textbbox((0, 0), counter, font=num_font)
    ct_w        = ct_bbox[2] - ct_bbox[0]
    draw.text((SIZE - MARGIN - ct_w, SIZE - MARGIN - F["slide_num_size"]),
              counter, font=num_font, fill=C["muted_text"])

    # ── Category label ───────────────────────────────────────────
    category = slide_data.get("category_label", "AI TOOLS").upper()
    if "🌿" not in category:
        category = f"🌿 {category}"
    heading    = slide_data.get("heading", "")
    subheading = slide_data.get("subheading", "")

    cat_font  = _semibold_font(F["label_size"])
    head_font = _headline_font(F["headline_size"])
    sub_font  = _body_font(F["subheadline_size"])

    cat_h  = _text_height(draw, category.replace("🌿 ", ""), cat_font, CW)
    head_h = _text_height(draw, heading, head_font, CW)
    sub_h  = _text_height(draw, subheading, sub_font, CW) if subheading else 0

    gap1, gap2 = 28, 24
    total_h = cat_h + gap1 + head_h + (gap2 + sub_h if subheading else 0)
    start_y = CY + (CH - total_h) // 2

    # Draw category (centered)
    y = start_y
    if Pilmoji is not None and "🌿" in category:
        with Pilmoji(img) as pilmoji:
            bbox   = draw.textbbox((0, 0), category, font=cat_font)
            line_w = bbox[2] - bbox[0] + 24   # slight extra for emoji
            x      = CX + (CW - line_w) // 2
            pilmoji.text((x, y), category, font=cat_font, fill=C["muted_text"])
    else:
        _draw_centered_text(draw, category, cat_font, C["muted_text"], y, CW)
    y += cat_h + gap1

    # Draw heading (centered)
    _draw_centered_text(draw, heading, head_font, C["primary_text"], y, CW)
    y += head_h + gap2

    # Draw subheading (centered)
    if subheading:
        _draw_centered_text(draw, subheading, sub_font, C["muted_text"], y, CW)

    return img


def _render_content(slide_data: dict, slide_number: int, total: int) -> Image.Image:
    """
    Content slides — warm cream background.
    Heading: centered (bold serif). Body: LEFT-ALIGNED for readability.
    Highlight phrase shown as a callout chip below body.
    """
    img  = Image.new("RGB", (SIZE, SIZE), C["content_bg"])
    draw = ImageDraw.Draw(img)

    heading   = slide_data.get("heading", "")
    body      = slide_data.get("body", "")
    highlight = slide_data.get("highlight_phrase", "")

    # ── Slide number — top left ──────────────────────────────────
    num_font = _body_font(F["slide_num_size"])
    draw.text((CX, CY), f"{slide_number:02d}", font=num_font, fill=C["muted_text"])

    # ── Slide counter — top right ────────────────────────────────
    counter  = f"{slide_number + 1:02d} / {total:02d}"
    ct_bbox  = draw.textbbox((0, 0), counter, font=num_font)
    ct_w     = ct_bbox[2] - ct_bbox[0]
    draw.text((SIZE - MARGIN - ct_w, CY), counter, font=num_font, fill=C["muted_text"])

    # ── Thin rule below number row ───────────────────────────────
    rule_y = CY + F["slide_num_size"] + 20
    draw.rectangle([CX, rule_y, CX + CW, rule_y + 1], fill=C["muted_text"])

    # ── Heading — centered ───────────────────────────────────────
    head_font = _headline_content_font()
    head_y    = rule_y + 36
    head_h    = _text_height(draw, heading, head_font, CW)
    _draw_centered_text(draw, heading, head_font, C["primary_text"], head_y, CW)

    # ── Body — LEFT-ALIGNED for readability ─────────────────────
    if body:
        body_font = _body_font()
        body_y    = head_y + head_h + 52

        # Always render full body as clean left-aligned text
        body_y = _draw_body_paragraphs_left(draw, body, body_font, C["body_text"], body_y)

        # Highlight chip shown as a standalone callout below body
        if highlight:
            body_y += 36
            _draw_highlight_chip(draw, highlight, body_font, body_y, CX, CW)

    return img


def _render_cta(slide_data: dict, slide_number: int, total: int) -> Image.Image:
    """
    CTA slide — warmer cream background.
    Heading centered, body LEFT-ALIGNED, yellow highlight chip below.
    """
    img  = Image.new("RGB", (SIZE, SIZE), C["cta_bg"])
    draw = ImageDraw.Draw(img)

    heading   = slide_data.get("heading", "The bottom line")
    body      = slide_data.get("body", "")
    highlight = slide_data.get("highlight_phrase", "")

    # ── Slide counter — bottom right ────────────────────────────
    num_font = _body_font(F["slide_num_size"])
    counter  = f"{slide_number + 1:02d} / {total:02d}"
    ct_bbox  = draw.textbbox((0, 0), counter, font=num_font)
    ct_w     = ct_bbox[2] - ct_bbox[0]
    draw.text((SIZE - MARGIN - ct_w, SIZE - MARGIN - F["slide_num_size"]),
              counter, font=num_font, fill=C["muted_text"])

    # ── Vertically center the content block ──────────────────────
    head_font = _headline_content_font()
    body_font = _body_font()

    head_h = _text_height(draw, heading, head_font, CW)
    body_h = _text_height_left(draw, body, body_font, CW) if body else 0
    hl_h   = (_text_height_left(draw, highlight, body_font, CW - 40) + 48) if highlight else 0

    gap1, gap2 = 44, 36
    total_block = head_h + gap1 + body_h + (gap2 + hl_h if highlight else 0)
    start_y = (SIZE - total_block) // 2

    # Heading centered
    _draw_centered_text(draw, heading, head_font, C["primary_text"], start_y, CW)
    y = start_y + head_h + gap1

    # Body left-aligned
    if body:
        y = _draw_body_paragraphs_left(draw, body, body_font, C["body_text"], y)
        y += gap2

    # Highlight chip
    if highlight:
        _draw_highlight_chip(draw, highlight, body_font, y, CX, CW)

    return img


# ─────────────────────────────────────────────────────────────────
# DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────

def _get_line_height(font) -> int:
    """Tighter spacing for large display fonts, standard for body."""
    if font.size >= 60:
        return int(font.size * 1.1)
    return int(font.size * 1.45)


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words   = text.split()
    lines   = []
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


def _text_height(draw, text: str, font, max_width: int) -> int:
    """Height of centered/wrapped text block."""
    lines  = _wrap_text(draw, text, font, max_width)
    return len(lines) * _get_line_height(font)


def _text_height_left(draw, text: str, font, max_width: int) -> int:
    """Height of left-aligned text block (respects \\n\\n paragraph breaks)."""
    paragraphs = text.split("\n\n")
    total = 0
    for i, p in enumerate(paragraphs):
        p = p.strip()
        if not p:
            continue
        total += len(_wrap_text(draw, p, font, max_width)) * _get_line_height(font)
        if i < len(paragraphs) - 1:
            total += 32   # inter-paragraph gap
    return total


def _draw_centered_text(draw, text: str, font, color: str, y: int, max_width: int):
    """Draw word-wrapped text centered horizontally."""
    lines  = _wrap_text(draw, text, font, max_width)
    line_h = _get_line_height(font)

    for line in lines:
        bbox   = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x      = CX + (max_width - line_w) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += line_h


def _draw_body_paragraphs_left(draw, body: str, font, color: str, y: int) -> int:
    """
    Draw body text left-aligned, splitting on double-newlines as paragraph breaks.
    Returns the new y position after all text.
    """
    paragraphs = body.split("\n\n")
    line_h     = _get_line_height(font)

    for i, p in enumerate(paragraphs):
        p = p.strip()
        if not p:
            continue
        lines = _wrap_text(draw, p, font, CW)
        for line in lines:
            draw.text((CX, y), line, font=font, fill=color)
            y += line_h
        if i < len(paragraphs) - 1:
            y += 32   # paragraph breathing room
    return y


def _draw_highlight_chip(draw, text: str, font, y: int, x_offset: int, max_width: int):
    """Draw text with a rounded yellow background chip, left-aligned."""
    lines    = _wrap_text(draw, text, font, max_width - 40)
    pad_h    = 18
    pad_v    = 10
    radius   = 8
    line_h   = _get_line_height(font)

    for line in lines:
        bbox   = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        rect   = [
            x_offset,
            y - pad_v,
            x_offset + text_w + pad_h * 2,
            y + font.size + pad_v,
        ]
        draw.rounded_rectangle(rect, radius=radius, fill=C["highlight_yellow"])
        draw.text((x_offset + pad_h, y), line, font=font, fill=C["primary_text"])
        y += line_h + pad_v
