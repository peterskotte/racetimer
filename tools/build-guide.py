#!/usr/bin/env python3
"""Byg vejledningen (docs/vejledning.md) som én HTML-fil og som PDF – til klubbens webhotel.

    python3 tools/build-guide.py

Resultat i webhotel/racetimer/vejledning/:
  index.html                  hele vejledningen i én fil (billederne er lagt ind i filen)
  vejledning.pdf              til print (A4), lavet med Chrome, hvis Chrome findes på maskinen
  statuslampe-farvekoder.pdf  det printbare ark, som vejledningen linker til

Markdown-delen dækker det, vejledningen bruger: overskrifter, afsnit, lister (også indrykkede og
tjeklister), tabeller, citater, kodeblokke, fed/kursiv/kode, links, billeder og indlejret <img>/<p>.
Links til andre .md-filer peger på GitHub, så de virker fra webhotellet.
"""
import base64
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = os.path.join(ROOT, "docs")
SRC = os.path.join(DOCS, "vejledning.md")
OUT = os.path.join(ROOT, "webhotel", "racetimer", "vejledning")
GITHUB = "https://github.com/peterskotte/racetimer/blob/main/"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
COPY = ["statuslampe-farvekoder.pdf"]  # filer i docs/, som vejledningen linker direkte til
MIME = {".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}


def slug(text):
    """Samme anker som GitHub laver for en overskrift (så indholdsfortegnelsen virker)."""
    t = re.sub(r"<[^>]+>", "", text).strip().lower()
    t = re.sub(r"[^\w\- ]", "", t)
    return t.replace(" ", "-")


SMALL = {}  # til PDF'en: mindre JPEG-udgaver af billederne (ellers bliver PDF'en over 10 MB)


def data_uri(src):
    path = os.path.normpath(os.path.join(DOCS, src))
    if SMALL.get("dir") and shutil.which("sips"):
        jpg = os.path.join(SMALL["dir"], os.path.basename(path) + ".jpg")
        if not os.path.exists(jpg):
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "70", "-Z", "1400", path, "--out", jpg],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        with open(jpg, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    with open(path, "rb") as f:
        return f"data:{MIME[os.path.splitext(path)[1].lower()]};base64," + base64.b64encode(f.read()).decode()


def href(url):
    """Relative links fra docs/: billeder lægges ind, .md-filer peger på GitHub, PDF'er ligger ved siden af."""
    if re.match(r"^(https?:|mailto:|#)", url):
        return url
    path, _, anchor = url.partition("#")
    if os.path.basename(path) in COPY:
        return os.path.basename(path)
    rel = os.path.relpath(os.path.normpath(os.path.join(DOCS, path)), ROOT)
    return GITHUB + rel.replace(os.sep, "/") + ("#" + anchor if anchor else "")


def inline(t):
    code = []
    t = re.sub(r"`([^`]+)`", lambda m: code.append(html.escape(m.group(1))) or f"\0{len(code) - 1}\0", t)
    # rå HTML i markdown-filen (fx <img … width>) bevares; alt andet escapes
    raw = []
    t = re.sub(r"<(/?)(img|p|br|b|i|small)\b[^>]*>", lambda m: raw.append(m.group(0)) or f"\1{len(raw) - 1}\1", t)
    t = html.escape(t, quote=False)
    t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: f'<img src="{data_uri(m.group(2))}" alt="{html.escape(m.group(1))}">', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(href(m.group(2)))}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)

    def fix_raw(m):
        tag = raw[int(m.group(1))]
        return re.sub(r'src="([^"]+)"', lambda s: f'src="{data_uri(s.group(1)) if not s.group(1).startswith(("http", "data:")) else s.group(1)}"', tag)
    t = re.sub("\x01(\\d+)\x01", fix_raw, t)
    return re.sub("\x00(\\d+)\x00", lambda m: f"<code>{code[int(m.group(1))]}</code>", t)


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]
    out = ["<div class=tablewrap><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"]
    out += ["<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body]
    return "\n".join(out) + "</tbody></table></div>"


def lists(lines):
    """Lister med indrykning → indlejrede <ul>/<ol>. lines: rå linjer (med indrykning)."""
    out, stack = [], []  # stack: (indrykning, tag)
    for ln in lines:
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", ln)
        if not m:  # fortsættelse af forrige punkt
            out[-1] = out[-1][:-5] + " " + inline(ln.strip()) + "</li>"
            continue
        ind, tag = len(m.group(1)), "ol" if m.group(2)[0].isdigit() else "ul"
        while stack and ind < stack[-1][0]:
            out.append(f"</{stack.pop()[1]}>")
        if not stack or ind > stack[-1][0]:
            if stack and out[-1].endswith("</li>"):
                out[-1] = out[-1][:-5]  # undertitel hører til forrige punkt
                stack.append((ind, tag, True))
            else:
                stack.append((ind, tag, False))
            out.append(f"<{tag}>")
        text = m.group(3)
        task = re.match(r"^\[( |x)\]\s+(.*)$", text)
        if task:
            out.append(f'<li class=task><span class=box>{"☑" if task.group(1) == "x" else "☐"}</span> {inline(task.group(2))}</li>')
        else:
            out.append(f"<li>{inline(text)}</li>")
    while stack:
        ind, tag, *nested = stack.pop()
        out.append(f"</{tag}>" + ("</li>" if nested and nested[0] else ""))
    return "\n".join(out)


def convert(md):
    lines = md.split("\n")
    out, i, toc = [], 0, []
    para = []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush(); i += 1; continue
        if s.startswith("```"):
            flush()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(l[len(ln) - len(ln.lstrip()):] for l in lines[i + 1:j])) + "</code></pre>")
            i = j + 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            flush()
            n, text = len(m.group(1)), m.group(2)
            if n == 2:
                toc.append((slug(text), text))
            out.append(f'<h{n} id="{slug(text)}">{inline(text)}</h{n}>')
            i += 1; continue
        if re.match(r"^<(p|img)\b", s):  # rå HTML-linje (fx billeder med bredde)
            flush(); out.append(inline(s) if s.startswith("<p") else "<p>" + inline(s) + "</p>"); i += 1; continue
        if re.match(r"^-{3,}$", s):
            flush(); out.append("<hr>"); i += 1; continue
        if s.startswith("|"):
            flush()
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            out.append(table(lines[i:j])); i = j; continue
        if s.startswith(">"):
            flush()
            j = i
            while j < len(lines) and lines[j].strip().startswith(">"):
                j += 1
            out.append("<blockquote>" + inline(" ".join(l.strip()[1:].strip() for l in lines[i:j])) + "</blockquote>")
            i = j; continue
        if re.match(r"^([-*]|\d+\.)\s+", s):
            flush()
            j, block = i, []
            while j < len(lines) and lines[j].strip():
                if lines[j].strip().startswith("```"):  # kodeblok inde i en liste: afslut listen
                    break
                block.append(lines[j]); j += 1
            out.append(lists(block)); i = j; continue
        if re.match(r"^\*[^*].*\*$", s) and out and out[-1].startswith("<p><img"):
            out[-1] = out[-1].replace("<p>", "<figure>", 1)[:-4] + f"<figcaption>{inline(s[1:-1])}</figcaption></figure>"
            i += 1; continue
        para.append(s); i += 1
    flush()
    return "\n".join(out), toc


CSS = """
:root { --ink:#17201b; --soft:#5b6760; --rule:#dfe3dc; --panel:#f3f4ef; --brand:#e5682a; --link:#b9501b; --paper:#fbfbf8; --code:#eef0ea; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --ink:#e8ece6; --soft:#a3ada6; --rule:#2c3530; --panel:#18201b;
  --link:#ff9a5c; --paper:#0f1512; --code:#1d2621; } }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin:0; background:var(--paper); color:var(--ink); font:17px/1.6 -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
.top { border-bottom:3px solid var(--brand); background:var(--panel); }
.top .in { max-width:900px; margin:0 auto; padding:12px 16px; display:flex; gap:12px; align-items:center; justify-content:space-between; flex-wrap:wrap; }
.top b { font-weight:800; font-style:italic; font-size:20px; }
.top a.pdf { color:var(--link); font-weight:600; text-decoration:none; }
main { max-width:900px; margin:0 auto; padding:8px 16px 64px; }
h1 { font-size:34px; line-height:1.15; margin:28px 0 12px; }
h2 { font-size:26px; margin:44px 0 10px; padding-top:12px; border-top:1px solid var(--rule); }
h3 { font-size:20px; margin:28px 0 6px; }
a { color:var(--link); }
img { max-width:100%; height:auto; border-radius:8px; vertical-align:top; }
main p > img, figure img { display:block; margin:8px 0; }  /* billedtekst under billedet, ikke ved siden af */
main p > img:has(+ img), main p > img + img { display:inline-block; }  /* to billeder side om side */
p img + img { margin-left:8px; }
figure { margin:12px 0; } figcaption { color:var(--soft); font-style:italic; font-size:15px; margin-top:4px; }
blockquote { margin:16px 0; padding:10px 16px; background:var(--panel); border-left:4px solid var(--brand); border-radius:0 8px 8px 0; }
code { font:14px/1.4 ui-monospace, Menlo, Consolas, monospace; background:var(--code); padding:1px 5px; border-radius:4px; overflow-wrap:anywhere; }
pre { background:var(--code); padding:12px 14px; border-radius:8px; overflow-x:auto; } pre code { padding:0; background:none; }
.tablewrap { overflow-x:auto; margin:12px 0; }
table { border-collapse:collapse; width:100%; font-size:15px; }
th, td { text-align:left; vertical-align:top; padding:8px 10px; border-bottom:1px solid var(--rule); }
th { background:var(--panel); }
li { margin:3px 0; } li.task { list-style:none; margin-left:-1.2em; } .box { font-size:1.1em; }
hr { border:0; border-top:1px solid var(--rule); margin:24px 0; }
footer { color:var(--soft); font-size:14px; border-top:1px solid var(--rule); margin-top:48px; padding-top:12px; }
@media (max-width:600px) { body { font-size:16px; } h1 { font-size:28px; } h2 { font-size:22px; } p img + img { margin:8px 0 0; } }
@media print {
  @page { size:A4; margin:14mm 14mm 16mm; }
  :root { --ink:#000; --soft:#444; --paper:#fff; --panel:#f2f2ee; --code:#f0f0ec; --link:#9a3f12; }
  body { font-size:11pt; line-height:1.45; background:#fff; }
  .top { display:none; } main { max-width:none; padding:0; }
  h1 { margin-top:0; }
  h2 { break-before:page; border-top:0; margin-top:0; }
  h2, h3 { break-after:avoid; }
  img, figure, table, tr, blockquote, pre { break-inside:avoid; }
  img { max-height:100mm; width:auto; }
  .tablewrap { overflow:visible; }
  a { text-decoration:none; }
  footer { display:none; }
}
"""


def page_html(md):
    body, toc = convert(md)
    title = re.search(r"^#\s+(.*)$", md, re.M).group(1)
    page = f"""<!doctype html>
<html lang="da">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="top"><div class="in"><b>RaceTimer</b><a class="pdf" href="vejledning.pdf">⬇ Hent som PDF</a></div></div>
<main>
{body}
<footer>Vejledningen er lavet ud fra <a href="{GITHUB}docs/vejledning.md">docs/vejledning.md</a> på GitHub.</footer>
</main>
</body>
</html>
"""
    return page, toc


def build():
    with open(SRC, encoding="utf-8") as f:
        md = f.read()
    page, toc = page_html(md)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    for name in COPY:
        shutil.copyfile(os.path.join(DOCS, name), os.path.join(OUT, name))
    print(f"✓ {os.path.relpath(os.path.join(OUT, 'index.html'), ROOT)} ({len(page) // 1024} kB, {len(toc)} afsnit)")
    chrome = os.environ.get("CHROME", CHROME)
    if not os.path.exists(chrome):
        print("  (Chrome ikke fundet – PDF'en er ikke lavet. Sæt CHROME=/sti/til/chrome)")
        return
    pdf = os.path.join(OUT, "vejledning.pdf")
    with tempfile.TemporaryDirectory() as tmp:
        SMALL["dir"] = tmp
        src = os.path.join(tmp, "vejledning.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(page_html(md)[0])
        SMALL.clear()
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tmp}/profil",
                        f"--print-to-pdf={pdf}", "file://" + src],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=True)
    print(f"✓ {os.path.relpath(pdf, ROOT)} ({os.path.getsize(pdf) // 1024} kB)")


if __name__ == "__main__":
    sys.exit(build())
