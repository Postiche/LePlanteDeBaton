"""Assemble l'aperçu autonome en un seul fichier HTML (CSS, JS, icône et données inline).

    cd frontend && VITE_PREVIEW=1 npx vite build && python ../scripts/preview/build_preview.py dist-preview immopro-apercu.html
"""
import base64
import re
import sys
from pathlib import Path

dist, out = Path(sys.argv[1]), Path(sys.argv[2])
html = (dist / "index.html").read_text(encoding="utf-8")
css = "".join((dist / m).read_text(encoding="utf-8") for m in re.findall(r'href="\./(assets/[^"]+\.css)"', html))
js = "".join((dist / m).read_text(encoding="utf-8") for m in re.findall(r'src="\./(assets/[^"]+\.js)"', html))
icon = "data:image/svg+xml;base64," + base64.b64encode((dist / "icons" / "icon.svg").read_bytes()).decode()
js = re.sub(r'(["`])/icons/icon\.svg\1', lambda m: m.group(1) + icon + m.group(1), js).replace("</script", "<\\/script")
page = (
    "<title>ImmoPro Entreprise</title>\n"
    '<meta name="robots" content="noindex, nofollow">\n'
    f"<style>{css}\nhtml,body{{background:var(--bg)}}</style>\n"
    '<div id="root"></div>\n'
    f'<script type="module">{js}</script>\n'
)
out.write_text(page, encoding="utf-8")
print(f"{out} : {out.stat().st_size // 1024} Ko")
