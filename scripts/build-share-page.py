"""Publish the same counseling page under a fresh social-preview identity."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
base = 'https://wonseong620.github.io/bible-krv/'
html = (root/'index.html').read_text(encoding='utf-8')
html = html.replace(f'rel="canonical" href="{base}"', f'rel="canonical" href="{base}share.html"')
html = html.replace(f'property="og:url" content="{base}"', f'property="og:url" content="{base}share.html"')
(root/'share.html').write_text(html, encoding='utf-8')
