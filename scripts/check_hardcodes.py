#!/usr/bin/env python3
"""扫描前端源码里的硬编码样式线索（颜色/px/字体/z-index/圆角）。

线索不是判决：输出只用于写后自检，逐条判断是 token、结构性值还是漏网。
用法：
  python3 check_hardcodes.py <路径...> [--json] [--include-tokens] [--fail]
跳过 node_modules/.git/dist/build 等目录；token/theme/variables 文件默认跳过。
行内加 `hardcode-ok` 可豁免。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {'.git', 'node_modules', 'dist', 'build', 'coverage', '.next', '.nuxt', 'vendor', '.cache'}
EXTS = {'.css', '.scss', '.sass', '.less', '.ts', '.tsx', '.js', '.jsx', '.vue', '.svelte', '.html', '.astro'}
TOKEN_HINTS = ('token', 'theme', 'variables', 'design-system', 'designsystem')

PATTERNS = [
    ('color', re.compile(r'#[0-9a-fA-F]{3,8}\b')),
    ('color', re.compile(r'\b(?:rgb|rgba|hsl|hsla)\s*\(')),
    ('size', re.compile(r'(?<![\w-])-?\d+(?:\.\d+)?px\b')),
    ('font', re.compile(r'font-family\s*:')),
    ('z-index', re.compile(r'z-index\s*:\s*-?\d+')),
    ('radius', re.compile(r'border-radius\s*:\s*[^;\n]*\d')),
]
IGNORE_MARK = re.compile(r'hardcode-ok|stylelint-disable|@ts-ignore-hardcode')


def is_token_file(p: Path) -> bool:
    s = str(p).lower()
    return any(h in s for h in TOKEN_HINTS)


def scan(paths, include_tokens=False):
    findings, scanned, skipped = [], 0, 0
    for root in paths:
        root = Path(root)
        it = [root] if root.is_file() else root.rglob('*')
        for p in it:
            if not p.is_file() or p.suffix.lower() not in EXTS:
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if not include_tokens and is_token_file(p):
                skipped += 1
                continue
            scanned += 1
            try:
                lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
            except OSError:
                continue
            for ln, line in enumerate(lines, 1):
                if IGNORE_MARK.search(line):
                    continue
                for cat, pat in PATTERNS:
                    for m in pat.finditer(line):
                        findings.append({
                            'file': str(p), 'line': ln, 'col': m.start() + 1,
                            'category': cat, 'match': m.group(0),
                            'snippet': line.strip()[:160],
                        })
    return findings, scanned, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--include-tokens', action='store_true')
    ap.add_argument('--fail', action='store_true')
    args = ap.parse_args()

    findings, scanned, skipped = scan(args.paths, args.include_tokens)
    if args.json:
        print(json.dumps({'scanned': scanned, 'skipped_token_files': skipped, 'findings': findings},
                         ensure_ascii=False, indent=1))
    else:
        for f in findings:
            print(f"{f['file']}:{f['line']}:{f['col']}  [{f['category']}]  {f['match']}  |  {f['snippet']}")
        by = {}
        for f in findings:
            by[f['category']] = by.get(f['category'], 0) + 1
        print(f"\n扫描 {scanned} 个文件；线索 {len(findings)} 条（{by}）；跳过 token/theme 文件 {skipped} 个。")
        print("线索不是判决：逐条确认是 token、结构性值（如 0/1px 边框）还是漏网。")
    raise SystemExit(1 if (args.fail and findings) else 0)


if __name__ == '__main__':
    main()
