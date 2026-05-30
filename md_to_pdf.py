"""
Conversor de PASSO_A_PASSO.md -> PDF usando markdown + WeasyPrint.
Executado dentro do contêiner Docker (Python 3.12 + libs de sistema do Pango).
"""
import pathlib
import markdown
from weasyprint import HTML

BASE = pathlib.Path(__file__).resolve().parent
MD = BASE / "PASSO_A_PASSO.md"
PDF = BASE / "PASSO_A_PASSO.pdf"

texto = MD.read_text(encoding="utf-8")
corpo = markdown.markdown(
    texto,
    extensions=["markdown.extensions.tables", "markdown.extensions.fenced_code"],
)

CSS = """
@page { size: A4; margin: 2cm 1.8cm;
  @bottom-center { content: "Página " counter(page) " de " counter(pages);
                   font-family: Helvetica, Arial, sans-serif; font-size: 8px; color: #7a8694; } }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5px; color: #1f2933; line-height: 1.5; }
h1 { color: #14467a; font-size: 22px; border-bottom: 3px solid #1b7a3d; padding-bottom: 6px; }
h2 { color: #1b7a3d; font-size: 16px; margin-top: 20px; border-bottom: 1px solid #cfe6d6;
     padding-bottom: 3px; page-break-after: avoid; }
h3 { color: #14467a; font-size: 13px; margin-top: 12px; page-break-after: avoid; }
h4 { color: #45525f; font-size: 11px; margin-bottom: 2px; page-break-after: avoid; }
p, li { font-size: 10.5px; }
a { color: #14467a; text-decoration: none; }
code { font-family: "DejaVu Sans Mono", monospace; background: #eef1f4; font-size: 9.3px;
       padding: 0 3px; border-radius: 3px; }
pre { background: #0f1b2d; color: #d6e4ff; font-family: "DejaVu Sans Mono", monospace; font-size: 8.6px;
      padding: 9px 11px; border-radius: 5px; line-height: 1.4; page-break-inside: avoid; }
pre code { background: transparent; color: #d6e4ff; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9.3px; page-break-inside: avoid; }
th { background: #e8f5ec; color: #1b7a3d; border: 1px solid #cfd8e0; padding: 5px 7px; text-align: left; }
td { border: 1px solid #e3e8ed; padding: 5px 7px; }
blockquote { background: #fff4e5; border-left: 4px solid #f0a500; margin: 8px 0;
             padding: 6px 12px; color: #7a4a00; }
hr { border: none; border-top: 1px solid #d6dbe0; margin: 14px 0; }
"""

html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>{corpo}</body></html>"""

HTML(string=html).write_pdf(str(PDF))
print(f"PDF gerado: {PDF.name} ({PDF.stat().st_size} bytes)")
