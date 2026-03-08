# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [m for m in collect_submodules('pandas') if not m.startswith('pandas.tests')]

block_cipher = None

a = Analysis(
    ['../run_gui.py'],
    pathex=['..', '../src'],
    binaries=[],
    datas=[
        ('../config/config.example.yaml', 'config'),
        ('../src/ad_security_reporter/assets/dark.qss', 'ad_security_reporter/assets'),
        ('../src/ad_security_reporter/assets/light.qss', 'ad_security_reporter/assets'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ADSecurityReporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
