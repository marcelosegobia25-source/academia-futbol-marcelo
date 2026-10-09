# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

raiz = Path(SPECPATH)

analisis = Analysis(
    ["desktop.py"],
    pathex=[str(raiz)],
    binaries=[],
    datas=[
        (str(raiz / "app" / "templates"), "app/templates"),
        (str(raiz / "app" / "static"), "app/static"),
    ],
    hiddenimports=["PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analisis.pure)

exe = EXE(
    pyz,
    analisis.scripts,
    [],
    exclude_binaries=True,
    name="AcademiaFutbol",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

coleccion = COLLECT(
    exe,
    analisis.binaries,
    analisis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AcademiaFutbol",
)
