"""Rebuild the standalone web/index.html from trusted local source files."""
from pathlib import Path
import base64
import hashlib
import re


def build(directory):
    page = directory / 'index.html'
    html = page.read_text(encoding='utf-8')
    js = '\n'.join((directory / name).read_text(encoding='utf-8') for name in ('converter.js', 'app.js'))
    css = (directory / 'style.css').read_text(encoding='utf-8')
    for tag, content, policy in [('script', js, 'script-src'), ('style', css, 'style-src')]:
        digest = base64.b64encode(hashlib.sha256(content.encode()).digest()).decode()
        html, count = re.subn(fr'<{tag}>.*?</{tag}>', lambda m: f'<{tag}>{content}</{tag}>', html, flags=re.S)
        if count != 1:
            raise ValueError(f'Expected one embedded {tag}, found {count}')
        html, count = re.subn(policy + r" 'sha256-[^']+'", lambda m: policy + " 'sha256-" + digest + "'", html)
        if count != 1:
            raise ValueError(f'Missing CSP directive: {policy}')
    page.write_text(html, encoding='utf-8')


if __name__ == '__main__':
    build(Path(__file__).resolve().parent / 'web')
