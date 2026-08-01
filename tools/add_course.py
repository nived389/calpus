#!/usr/bin/env python3
"""
Add a whole course to Calpus in ONE command:
  1) builds the watermarked textbook from a folder of module PDFs
  2) copies it into  textbooks/<slug>.pdf
  3) archives the raw source into  data/<Dept>-<Sem>-<slug>/
  4) wires the entry into the TEXTBOOKS library inside index.html

Usage:
  python3 tools/add_course.py "<source_folder>" "<Department>" "<Semester>" "<Subject Title>"
Example:
  python3 tools/add_course.py "~/Downloads/BBA sem3/Marketing" "BBA" "Sem 3" "Marketing Management"

Requires: pip3 install pdfplumber reportlab
"""
import os, re, sys, glob, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_textbook import build

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def main():
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)
    src = os.path.expanduser(sys.argv[1]); dept = sys.argv[2].strip(); sem = sys.argv[3].strip(); subject = sys.argv[4].strip()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the vidya/ repo root
    if not os.path.isdir(src):
        print("!! source folder not found:", src); sys.exit(1)
    if not glob.glob(os.path.join(src, "*.pdf")):
        print("!! no PDFs in source folder:", src); sys.exit(1)

    slug = slugify(subject)
    tb_dir = os.path.join(root, "textbooks"); data_dir = os.path.join(root, "data", "%s-%s-%s" % (slugify(dept), slugify(sem), slug))
    os.makedirs(tb_dir, exist_ok=True); os.makedirs(data_dir, exist_ok=True)
    out_pdf = os.path.join(tb_dir, slug + ".pdf")

    # 1) build textbook
    st, sy = build(src, subject, out_pdf, "%s %s . Calicut University" % (dept, sem))
    print("built textbook:", os.path.basename(out_pdf), "(%d modules, %d syllabus)" % (st, sy))

    # 2) archive raw source
    n = 0
    for p in glob.glob(os.path.join(src, "*.pdf")):
        shutil.copy2(p, os.path.join(data_dir, os.path.basename(p))); n += 1
    print("archived %d source PDF(s) -> data/%s/" % (n, os.path.basename(data_dir)))

    # 3) wire into TEXTBOOKS map in index.html
    idx = os.path.join(root, "index.html"); s = open(idx, encoding='utf-8').read()
    entry = "{s:'%s',f:'textbooks/%s.pdf'}" % (subject.replace("'", "’"), slug)
    line_hint = "Under '%s' -> '%s':  %s" % (dept, sem, entry)
    if entry in s:
        print("library: already present.  ", line_hint); done = True
    else:
        m = re.search(r"var TEXTBOOKS=\{", s); done = False
        if m:
            dkey = "'%s':{" % dept; di = s.find(dkey, m.start())
            if di >= 0:
                # scope the dept object to the next dept key or map end
                nxt = re.search(r"\n\s*'[^']+':\{", s[di+len(dkey):])
                dept_end = di + len(dkey) + (nxt.start() if nxt else len(s))
                skey = "'%s':[" % sem; si = s.find(skey, di)
                if 0 <= si < dept_end:
                    ins = si + len(skey); s = s[:ins] + entry + "," + s[ins:]
                    print("library: added under existing %s / %s" % (dept, sem)); done = True
                else:
                    ins = di + len(dkey); s = s[:ins] + "'%s':[%s]," % (sem, entry) + s[ins:]
                    print("library: added new semester %s under %s" % (sem, dept)); done = True
            else:
                ins = m.end(); s = s[:ins] + "\n  '%s':{'%s':[%s]}," % (dept, sem, entry) + s[ins:]
                print("library: added new department %s" % dept); done = True
            if done:
                open(idx, 'w', encoding='utf-8').write(s)
    if not done:
        print("!! could not auto-wire. Paste this into the TEXTBOOKS map in index.html:")
        print("   ", line_hint)

    print("\nDONE. Commit + push, then it appears after login under %s / %s." % (dept, sem))

if __name__ == "__main__":
    main()
