
import os, io, time, textwrap
from typing import Dict, Any, List
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image

FONT_PATHS = [
    os.path.join("assets","DejaVuSans.ttf"),
    "/system/fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def _load_font_or_fallback():
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("DejaVu", p))
                return "DejaVu"
            except Exception:
                pass
    # Try to use built-in fonts that support Cyrillic
    try:
        # Try Times-Roman which has better Unicode support
        return "Times-Roman"
    except Exception:
        # Last resort - Helvetica (may not display Cyrillic correctly)
        return "Helvetica"

def _fmt_ts(ts):
    if not ts:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

def _wrap(c, text, x, y, max_width_pt, font_name, font_size):
    # crude wrapper: split by words, draw multiple lines
    words = text.split()
    line = ""
    lh = font_size + 2
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, font_name, font_size) <= max_width_pt:
            line = test
        else:
            c.drawString(x, y, line)
            y -= lh
            line = w
    if line:
        c.drawString(x, y, line)
        y -= lh
    return y

def compress_image_to_jpeg(src_path: str, max_dim: int = 1600, quality: int = 80) -> bytes:
    im = Image.open(src_path)
    im = im.convert("RGB")
    w, h = im.size
    scale = min(1.0, float(max_dim)/max(w, h))
    if scale < 1.0:
        im = im.resize((int(w*scale), int(h*scale)))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()

def generate_pdf(db, session, steps, photos_by_step: Dict[int, List[str]], save_dir: str, seq: int, checklist_version: str):
    # File name
    started = _fmt_ts(session["started_at"])
    stamp = time.strftime("%Y-%m-%d_%H%M%S", time.localtime(time.time()))
    fname = f"{stamp}_{session['order_no']}_nesting_{seq:04d}.pdf"
    out_path = os.path.join(save_dir, fname)

    font_name = _load_font_or_fallback()
    page_size = landscape(A4)
    c = canvas.Canvas(out_path, pagesize=page_size)
    c.setTitle(f"CNC Checklist Report #{seq}")
    c.setAuthor("CNC Checklist App")
    margin = 15*mm
    width, height = page_size
    x = margin
    y = height - margin

    # Header
    c.setFont(font_name, 16)
    c.drawString(x, y, "Отчёт по чек-листу – Нестинг (Компакт)")
    y -= 10*mm
    c.setFont(font_name, 10)
    header = [
        f"Заказ: {session['order_no']}",
        f"Оператор: {session['operator_name']}",
        f"Начато: {started}",
        f"Окончено: {_fmt_ts(session['completed_at']) or '-'}",
        f"Версия чек-листа: {checklist_version}",
        f"Авто-номер отчёта (SEQ): {seq:04d}"
    ]
    for line in header:
        c.drawString(x, y, line)
        y -= 5*mm

    # Table header
    y -= 5*mm
    c.setFont(font_name, 11)
    c.drawString(x, y, "Таблица пунктов:")
    y -= 6*mm
    c.setFont(font_name, 9)

    # Columns: Block# Item# Text | ✓/✗ | Start | End | Dur | Critical | Override | Note
    col_x = [x, x+12*mm, x+22*mm, x+150*mm, x+165*mm, x+190*mm, x+205*mm, x+220*mm, x+235*mm]
    headers = ["Блок", "Пункт", "Статус", "Текст", "Начато", "Окончено", "Длит.,с", "Крит.", "Обход"]
    for i, h in enumerate(headers):
        c.drawString(col_x[i], y, h)
    y -= 5*mm
    c.line(x, y+2*mm, width - margin, y+2*mm)
    y -= 2*mm

    # Rows
    block_item_counters = {}
    for st in steps:
        bi = st["block_index"]
        ii = st["item_index"]
        status = st["status"]
        status_char = "✓" if status=="done" else ("✗" if status=="failed" else ("…"))
        started_at = _fmt_ts(st["started_at"])
        completed_at = _fmt_ts(st["completed_at"])
        duration = str(st["duration_sec"] or "-")
        crit = "Да" if st["critical"] else "-"
        override = "Да" if st["override_by_master"] else "-"

        # block and item numbers humanized
        c.drawString(col_x[0], y, str(bi+1))
        c.drawString(col_x[1], y, str(ii+1))
        c.drawString(col_x[2], y, status_char)

        # wrap text
        y = _wrap(c, st["text"], col_x[3], y, (width - margin) - col_x[3], font_name, 9)
        # smaller columns for times on the last printed line
        c.drawString(col_x[4], y+9, started_at)
        c.drawString(col_x[5], y+9, completed_at)
        c.drawString(col_x[6], y+9, duration)
        c.drawString(col_x[7], y+9, crit)
        c.drawString(col_x[8], y+9, override)
        y -= 2*mm
        if y < 40*mm:
            c.showPage()
            y = height - margin
            c.setFont(font_name, 9)

    # Photos per block
    c.showPage()
    y = height - margin
    c.setFont(font_name, 12)
    c.drawString(x, y, "Фото по блокам")
    y -= 8*mm
    c.setFont(font_name, 9)

    for st in steps:
        pid = st["id"]
        phs = photos_by_step.get(pid, [])
        if not phs:
            continue
        title = f"Блок {st['block_index']+1}, пункт {st['item_index']+1}: {st['text']}"
        y = _wrap(c, title, x, y, width - 2*margin, font_name, 9)
        # place up to 3 images per row
        cell_w = (width - 2*margin) / 3 - 5*mm
        cell_h = 45*mm
        col = 0
        for p in phs:
            try:
                jpeg_bytes = compress_image_to_jpeg(p, max_dim=1600, quality=80)
                img = ImageReader(io.BytesIO(jpeg_bytes))
                ix = x + col * (cell_w + 5*mm)
                iy = y - cell_h
                c.drawImage(img, ix, iy, width=cell_w, height=cell_h, preserveAspectRatio=True, anchor='sw')
                col += 1
                if col >= 3:
                    col = 0
                    y -= (cell_h + 5*mm)
                    if y < 30*mm:
                        c.showPage()
                        y = height - margin
                        c.setFont(font_name, 9)
            except Exception:
                continue
        if col != 0:
            y -= (cell_h + 8*mm)
        if y < 40*mm:
            c.showPage()
            y = height - margin
            c.setFont(font_name, 9)

    c.showPage()
    c.save()
    return out_path
