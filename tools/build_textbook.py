#!/usr/bin/env python3
"""Reusable Calpus textbook builder.
CLI:  python3 build_textbook.py "<src_dir>" "<Course Title>" "<out.pdf>" ["<footer subtitle>"]
Or import:  from build_textbook import build; build(src, title, out, subtitle)
"""
import os, re, glob, html, sys
import pdfplumber
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, PageBreak, HRFlowable)

def _collect(SRC):
    study, syl = [], []
    for p in sorted(glob.glob(os.path.join(SRC, "*.pdf"))):
        b = os.path.basename(p).lower()
        if b.startswith("calpus - "): continue
        (syl if "syllabus" in b else study).append(p)
    def key(p):
        m = re.search(r'module[-\s]*(\d+)', os.path.basename(p), re.I)
        return (0, int(m.group(1))) if m else (1, os.path.basename(p).lower())
    study.sort(key=key)
    return study, syl

def _extract_clean(path):
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            keep = lambda o: (o.get('size', 0) or 0) < 35 if o['object_type'] == 'char' else True
            out.append(page.filter(keep).extract_text() or "")
    txt = "\n".join(out).replace("(cid:127)", "•"); txt = re.sub(r"\(cid:\d+\)", "", txt)
    lines = []
    for ln in txt.split("\n"):
        s = ln.rstrip()
        if re.search(r'degreelive', s, re.I): continue
        if re.fullmatch(r'\s*\d{1,3}\s*', s): continue
        lines.append(s)
    return lines

def _is_heading(s):
    s = s.strip()
    if not s or len(s) > 70: return False
    if re.match(r'^(MODULE|Unit|Section)\b', s, re.I): return True
    letters = re.sub(r'[^A-Za-z]', '', s)
    return bool(letters and s.upper() == s and 3 < len(s) <= 62 and len(s.split()) <= 10)

def _reflow(lines):
    blocks, cur = [], ""
    def flush():
        nonlocal cur
        if cur.strip(): blocks.append(('P', cur.strip()))
        cur = ""
    for ln in lines:
        s = ln.strip()
        if not s: flush(); continue
        if _is_heading(s): flush(); blocks.append(('H', s)); continue
        if s[:1] in "•-*▪": flush(); blocks.append(('B', s.lstrip("•-*▪ ").strip())); continue
        if not cur: cur = s
        elif cur.endswith(('.', ':', '?', '!')): flush(); cur = s
        else: cur += " " + s
    flush(); return blocks

def _sanitize(s):
    for k, v in {'•': '–', '✦': '*', '‘': "'", '’': "'", '“': '"', '”': '"', '…': '...'}.items():
        s = s.replace(k, v)
    return s.encode('cp1252', 'ignore').decode('cp1252')
def _esc(s): return html.escape(_sanitize(s), quote=False)

def build(SRC, COURSE, OUT, SUBTITLE="Calicut University"):
    styles = getSampleStyleSheet()
    H1 = ParagraphStyle('H1', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=17, textColor=colors.HexColor('#0D9488'), spaceBefore=14, spaceAfter=8)
    H2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12.5, textColor=colors.HexColor('#0f766e'), spaceBefore=10, spaceAfter=4)
    BODY = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=6)
    BULLET = ParagraphStyle('Bullet', parent=BODY, leftIndent=14, spaceAfter=2)
    COVER_T = ParagraphStyle('CoverT', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=30, textColor=colors.HexColor('#0D9488'), alignment=TA_CENTER, leading=36)
    COVER_S = ParagraphStyle('CoverS', parent=styles['Normal'], fontSize=13, alignment=TA_CENTER, textColor=colors.HexColor('#334155'), leading=20)

    def decorate(canvas, doc):
        w, h = A4
        canvas.saveState(); canvas.translate(w/2, h/2); canvas.rotate(35)
        canvas.setFont('Helvetica-Bold', 80); canvas.setFillColor(colors.HexColor('#0D9488')); canvas.setFillAlpha(0.06)
        canvas.drawCentredString(0, 0, "CALPUS"); canvas.setFont('Helvetica', 20); canvas.drawCentredString(0, -60, "AI Study Companion"); canvas.restoreState()
        canvas.saveState(); canvas.setFont('Helvetica', 8); canvas.setFillColor(colors.HexColor('#0D9488')); canvas.drawString(18*mm, 12*mm, "Calpus  -  Textbook")
        canvas.setFillColor(colors.HexColor('#94a3b8')); canvas.drawRightString(w-18*mm, 12*mm, (COURSE + " . " + SUBTITLE)[:90])
        canvas.setStrokeColor(colors.HexColor('#cbd5e1')); canvas.line(18*mm, 15*mm, w-18*mm, 15*mm); canvas.drawCentredString(w/2, 8*mm, "Page %d" % doc.page); canvas.restoreState()

    def render(story, blocks, drop=True):
        first = True
        for kind, text in blocks:
            if first and drop and kind == 'H' and re.match(r'^MODULE', text, re.I): first = False; continue
            first = False
            if kind == 'H': story.append(Paragraph(_esc(text), H2))
            elif kind == 'B': story.append(Paragraph("–&nbsp;&nbsp;" + _esc(text), BULLET))
            else: story.append(Paragraph(_esc(text), BODY))

    study, syl = _collect(SRC)
    story = [Spacer(1, 70),
             Paragraph("CALPUS", ParagraphStyle('b', parent=COVER_S, fontSize=15, textColor=colors.HexColor('#0D9488'), spaceAfter=6)),
             Paragraph("Textbook", COVER_T), Spacer(1, 10),
             Paragraph(COURSE, ParagraphStyle('s', parent=COVER_T, fontSize=19, textColor=colors.HexColor('#134E4A'))), Spacer(1, 18),
             HRFlowable(width="40%", color=colors.HexColor('#2DD4BF'), thickness=2, spaceAfter=18, hAlign='CENTER'),
             Paragraph(SUBTITLE, COVER_S), Spacer(1, 20),
             Paragraph("Compiled by Calpus from %d module file(s)." % len(study), COVER_S), PageBreak(),
             Paragraph("Part 1 — Textbook (Modules)", H1), HRFlowable(width="100%", color=colors.HexColor('#2DD4BF'), thickness=1, spaceAfter=8)]
    for p in study:
        story.append(Paragraph(_esc(re.sub(r'\.pdf$', '', os.path.basename(p), flags=re.I).replace('-', ' ').title()), H1))
        render(story, _reflow(_extract_clean(p))); story.append(PageBreak())
    story += [Paragraph("Part 2 — Official Syllabus", H1), HRFlowable(width="100%", color=colors.HexColor('#2DD4BF'), thickness=1, spaceAfter=8)]
    if syl:
        for p in syl: render(story, _reflow(_extract_clean(p)), drop=False)
    else:
        story.append(Paragraph("No syllabus file found.", BODY))
    doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=20*mm, title="Calpus Textbook - " + COURSE, author="Calpus")
    doc.addPageTemplates([PageTemplate(id='all', frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='m')], onPage=decorate)])
    doc.build(story)
    return len(study), len(syl)

if __name__ == "__main__":
    sub = sys.argv[4] if len(sys.argv) > 4 else "Calicut University"
    st, sy = build(sys.argv[1], sys.argv[2], sys.argv[3], sub)
    print("WROTE:", os.path.basename(sys.argv[3]), "| study:", st, "| syllabus:", sy)
