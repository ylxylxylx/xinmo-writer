# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None
base_dir = Path(os.path.abspath(SPECPATH))

a = Analysis(
    [str(base_dir / 'backend' / 'main_desktop.py')],
    pathex=[str(base_dir / 'backend')],
    binaries=[],
    datas=[
        (str(base_dir / 'data'), 'data'),
        (str(base_dir / 'frontend' / 'dist'), 'frontend/dist'),
        (str(base_dir / 'config.json'), '.'),
    ],
    hiddenimports=[
        'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
        'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan', 'uvicorn.lifespan.on',
        'fastapi', 'openai', 'jinja2', 'aiofiles', 'webview',
        'webview.platforms.edgechromium',
        'novel.models', 'novel.db', 'novel.writer', 'novel.prompts', 'novel.writers',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='芯墨写作工坊',
    debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=False,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='芯墨写作工坊',
)
