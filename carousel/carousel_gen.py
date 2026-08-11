"""
carousel/carousel_gen.py
Generates carousel slides as 1080x1080px PNGs compiled into a single PDF.
Uses Pillow only — no external design tools.
Design: clean editorial style — left-aligned body, blue accent bars, minimal white palette.
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

# Layout constants
MARGIN = CAROUSEL_MARGIN          # 80px
SIZE   = CAROUSEL_CANVAS_SIZE     # 1080px
INNER  = CAROUSEL_CONTENT_SIZE    # 920px  (SIZE - 2*MARGIN)

# Left-aligned text starts here
TEXT_X = MARGIN
# Right edge for text wrap
TEXT_MAX_W = INNER

# Accent bar dimensions
ACCENT_BAR_W = 5
ACCENT_BAR_GAP = 18   # gap between bar and text


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
    total = len(slides)
    paths = []

    for i, slide_data in enumerate(slides):
        try:
            img = _render_slide(slide_data, slide_number=i, total=total)
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
        return _render_cover(slide_data, total)
    elif slide_type == "cta" or slide_number == total - 1:
        return _render_cta(slide_data, slide_number, total)
    else:
        return _render_content(slide_data, slide_number, total)


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

def _headline_content_font(size: int = None):
    return _load_font(F["headline_path"], size or F["headline_size_content"])

def _body_font(size: int = None):
    return _load_font(F["body_path"], size or F["body_size"])

def _semibold_font(size: int = None):
    return _load_font(F["semibold_path"], size or F["body_size"])


# ─────────────────────────────────────────────────────────────────
# SLIDE RENDERERS
# ─────────────────────────────────────────────────────────────────

def _render_cover(slide_data: dict, total: int) -> Image.Image:
    """
    Slide 1 — Clean white background.
    Layout: category chip (top-left), large headline (center-left),
    subheading below, accent strip at bottom.
    """
    img = Image.new("RGB", (SIZE, SIZE), C["cover_bg"])
    draw = ImageDraw.Draw(img)

    category = slide_data.get("category_label", "AI TOOLS").upper()
    heading   = slide_data.get("heading", "")
    subheading = slide_data.get("subheading", "")

    # ── Bottom accent strip ──────────────────────────────────────
    strip_h = 8
    draw.rectangle([0, SIZE - strip_h, SIZE, SIZE], fill=C["accent"])

    # ── Top slide counter ───────────────────────────────────────
    counter_font = _semibold_font(F["label_size"])
    counter_text = f"1 / {total}"
    draw.text((TEXT_X, MARGIN), counter_text, font=counter_font, fill=C["muted_text"])

    # ── Category chip (below counter) ───────────────────────────
    chip_font  = _semibold_font(F["label_size"])
    chip_y     = MARGIN + 40
    chip_pad_h = 14
    chip_pad_v = 7
    chip_r     = 6
    cat_bbox   = draw.textbbox((0, 0), category, font=chip_font)
    cat_w      = cat_bbox[2] - cat_bbox[0]
    chip_rect  = [TEXT_X, chip_y, TEXT_X + cat_w + chip_pad_h * 2, chip_y + F["label_size"] + chip_pad_v * 2]
    draw.rounded_rectangle(chip_rect, radius=chip_r, fill=C["accent_light"])
    draw.text((TEXT_X + chip_pad_h, chip_y + chip_pad_v), category, font=chip_font, fill=C["accent"])

    # ── Main heading ─────────────────────────────────────────────
    head_font  = _headline_font(F["headline_size"])
    head_y     = chip_y + F["label_size"] + chip_pad_v * 2 + 48
    head_h     = _text_height_left(draw, heading, head_font, TEXT_MAX_W)
    _draw_left_text(draw, heading, head_font, C["primary_text"], head_y, TEXT_MAX_W)

    # ── Subheading ───────────────────────────────────────────────
    if subheading:
        sub_font = _body_font(F["subheadline_size"])
        sub_y = head_y + head_h + 28
        _draw_left_text(draw, subheading, sub_font, C["body_text"], sub_y, TEXT_MAX_W)

    # ── Left accent bar (full height minus margins) ───────────────
    bar_x1 = MARGIN - 24
    bar_x2 = bar_x1 + ACCENT_BAR_W
    bar_y1 = chip_y - 4
    bar_y2 = SIZE - MARGIN - strip_h - 4
    draw.rectangle([bar_x1, bar_y1, bar_x2, bar_y2], fill=C["accent"])

    return img


def _render_content(slide_data: dict, slide_number: int, total: int) -> Image.Image:
    """
    Content slides 2-(n-1) — warm off-white.
    Layout: slide counter (top-right), blue accent bar + heading (left-aligned),
    body text below (left-aligned), optional highlight chip.
    """
    img = Image.new("RGB", (SIZE, SIZE), C["content_bg"])
    draw = ImageDraw.Draw(img)

    heading   = slide_data.get("heading", "")
    body      = slide_data.get("body", "")
    highlight = slide_data.get("highlight_phrase", "")

    # ── Slide counter top-right ──────────────────────────────────
    counter_font = _semibold_font(F["label_size"])
    counter_text = f"{slide_number + 1} / {total}"
    ct_bbox = draw.textbbox((0, 0), counter_text, font=counter_font)
    ct_w    = ct_bbox[2] - ct_bbox[0]
    draw.text((SIZE - MARGIN - ct_w, MARGIN), counter_text, font=counter_font, fill=C["muted_text"])

    # ── Thin divider line under counter ─────────────────────────
    div_y = MARGIN + F["label_size"] + 16
    draw.rectangle([TEXT_X, div_y, SIZE - MARGIN, div_y + 1], fill=C["divider"])

    # ── Left accent bar + heading ─────────────────────────────────
    head_font = _headline_content_font()
    head_y    = div_y + 40

    # Draw accent bar aligned to heading
    head_h = _text_height_left(draw, heading, head_font, TEXT_MAX_W - ACCENT_BAR_W - ACCENT_BAR_GAP)
    bar_x1 = TEXT_X
    bar_x2 = bar_x1 + ACCENT_BAR_W
    # Ensure bar is at least as tall as one line height
    bar_height = max(head_h, _get_line_height(head_font))
    draw.rectangle([bar_x1, head_y - 4, bar_x2, head_y + bar_height + 4], fill=C["accent"])

    # Heading text starts after the bar
    head_text_x = TEXT_X + ACCENT_BAR_W + ACCENT_BAR_GAP
    head_text_w = TEXT_MAX_W - ACCENT_BAR_W - ACCENT_BAR_GAP
    _draw_left_text(draw, heading, head_font, C["primary_text"], head_y, head_text_w, x_offset=head_text_x)

    # ── Body text ─────────────────────────────────────────────────
    if body:
        body_font = _body_font()
        body_y    = head_y + head_h + 52

        # Always render full body as clean text first
        body_y = _draw_body_paragraphs_left(draw, body, body_font, C["body_text"], body_y)

        # Highlight chip shown as a standalone callout below body
        if highlight:
            body_y += 36
            _draw_highlight_chip_left(draw, highlight, body_font, body_y)

    return img


def _render_cta(slide_data: dict, slide_number: int, total: int) -> Image.Image:
    """
    Final CTA slide — warm cream background.
    Layout: bold heading, body, yellow highlight chip, accent strip at bottom.
    """
    img = Image.new("RGB", (SIZE, SIZE), C["cta_bg"])
    draw = ImageDraw.Draw(img)

    heading   = slide_data.get("heading", "The bottom line")
    body      = slide_data.get("body", "")
    highlight = slide_data.get("highlight_phrase", "")

    # ── Bottom accent strip ──────────────────────────────────────
    strip_h = 8
    draw.rectangle([0, SIZE - strip_h, SIZE, SIZE], fill=C["accent"])

    # ── Slide counter top-right ──────────────────────────────────
    counter_font = _semibold_font(F["label_size"])
    counter_text = f"{slide_number + 1} / {total}"
    ct_bbox = draw.textbbox((0, 0), counter_text, font=counter_font)
    ct_w    = ct_bbox[2] - ct_bbox[0]
    draw.text((SIZE - MARGIN - ct_w, MARGIN), counter_text, font=counter_font, fill=C["muted_text"])

    # ── Vertically center the content block ───────────────────────
    head_font = _headline_content_font()
    body_font = _body_font()

    head_h    = _text_height_left(draw, heading, head_font, TEXT_MAX_W)
    body_h    = _text_height_left(draw, body, body_font, TEXT_MAX_W) if body else 0
    hl_h      = (_text_height_left(draw, highlight, body_font, TEXT_MAX_W - 40) + 48) if highlight else 0

    gap1, gap2 = 40, 36
    total_block = head_h + gap1 + body_h + (gap2 + hl_h if highlight else 0)
    start_y = (SIZE - total_block) // 2

    # ── Left accent bar spanning heading ─────────────────────────
    bar_x1 = TEXT_X
    bar_x2 = bar_x1 + ACCENT_BAR_W
    draw.rectangle([bar_x1, start_y - 4, bar_x2, start_y + head_h + 4], fill=C["accent"])

    head_text_x = TEXT_X + ACCENT_BAR_W + ACCENT_BAR_GAP
    head_text_w = TEXT_MAX_W - ACCENT_BAR_W - ACCENT_BAR_GAP
    _draw_left_text(draw, heading, head_font, C["primary_text"], start_y, head_text_w, x_offset=head_text_x)

    y = start_y + head_h + gap1

    if body:
        _draw_body_paragraphs_left(draw, body, body_font, C["body_text"], y)
        y += body_h + gap2

    if highlight:
        _draw_highlight_chip_left(draw, highlight, body_font, y)

    return img


# ─────────────────────────────────────────────────────────────────
# LEFT-ALIGNED DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────

def _get_line_height(font) -> int:
    """Return tighter line height for large fonts, standard for body."""
    if font.size >= 60:
        return int(font.size * 1.1)
    return int(font.size * 1.45)


def _wrap_text_left(draw, text: str, font, max_width: int) -> list[str]:
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


def _text_height_left(draw, text: str, font, max_width: int) -> int:
    """Calculate total height of wrapped text block."""
    lines = _wrap_text_left(draw, text, font, max_width)
    return len(lines) * _get_line_height(font)


def _draw_left_text(draw, text: str, font, color: str, y: int, max_width: int, x_offset: int = None):
    """Draw word-wrapped text left-aligned."""
    x = x_offset if x_offset is not None else TEXT_X
    lines = _wrap_text_left(draw, text, font, max_width)
    line_h = _get_line_height(font)

    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += line_h


def _draw_body_paragraphs_left(draw, body: str, font, color: str, y: int) -> int:
    """Draw body text left-aligned, respecting double newlines as paragraph breaks."""
    paragraphs = body.split("\n\n")
    for i, p in enumerate(paragraphs):
        p = p.strip()
        if not p:
            continue
        _draw_left_text(draw, p, font, color, y, TEXT_MAX_W)
        y += _text_height_left(draw, p, font, TEXT_MAX_W)
        if i < len(paragraphs) - 1:
            y += 32   # paragraph gap
    return y


def _draw_body_with_highlight_left(draw, body: str, font, highlight: str, y: int) -> int:
    """
    Draw body text left-aligned, rendering the highlight_phrase with
    a yellow background chip. Returns new y after all text.
    """
    if not highlight or highlight not in body:
        return _draw_body_paragraphs_left(draw, body, font, C["body_text"], y)

    parts = body.split(highlight, 1)
    before = parts[0].strip()
    after  = parts[1].strip() if len(parts) > 1 else ""

    if before:
        y = _draw_body_paragraphs_left(draw, before, font, C["body_text"], y)
        y += 32

    _draw_highlight_chip_left(draw, highlight, font, y)
    y += _text_height_left(draw, highlight, font, TEXT_MAX_W - 40) + 48 + 32

    if after:
        y = _draw_body_paragraphs_left(draw, after, font, C["body_text"], y)

    return y


def _draw_highlight_chip_left(draw, text: str, font, y: int):
    """Draw text with a yellow rounded-rect background, left-aligned."""
    lines = _wrap_text_left(draw, text, font, TEXT_MAX_W - 40)
    pad_h, pad_v = 18, 10
    radius = 8
    line_h = _get_line_height(font)

    for line in lines:
        bbox   = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        rect   = [
            TEXT_X,
            y - pad_v,
            TEXT_X + text_w + pad_h * 2,
            y + font.size + pad_v,
        ]
        draw.rounded_rectangle(rect, radius=radius, fill=C["highlight_yellow"])
        draw.text((TEXT_X + pad_h, y), line, font=font, fill=C["primary_text"])
        y += line_h + pad_v


# ─────────────────────────────────────────────────────────────────
# LEGACY CENTERED HELPERS (kept for backward compat, not used in new design)
# ─────────────────────────────────────────────────────────────────

def _draw_centered_text(draw, text: str, font, color: str, y: int, max_width: int):
    """Draw word-wrapped text centered horizontally."""
    lines = _wrap_text_left(draw, text, font, max_width)
    line_h = _get_line_height(font)

    for line in lines:
        bbox   = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = TEXT_X + (max_width - line_w) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += line_h
