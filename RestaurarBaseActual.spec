# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

raiz = Path(SPECPATH)
base = raiz / "installer" / "restore_payload" / "academia.db"

analisis = Analysis(
    ["restaurador_base.py"],
    pathex=[str(raiz)],
    binaries=[],
    datas=[(str(base), ".")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analisis.pure)

exe = EXE(
    pyz,
    analisis.scripts,
    analisis.binaries,
    analisis.datas,
    [],
    name="Restaurar_Base_Gestion_Academia",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(raiz / "installer" / "academia.ico"),
)
