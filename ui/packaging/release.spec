from pathlib import Path
root = Path(SPECPATH).resolve().parents[1]
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=[],
    datas=[(str(root / 'scenes'), 'scenes'), (str(root / 'LICENSE'), '.')],
    hiddenimports=[], hookspath=[], runtime_hooks=[str(Path(SPECPATH) / 'smoke_hook.py')],
    excludes=['torch', 'tensorflow', 'matplotlib', 'pandas', 'scipy', 'IPython', 'pytest'],
    module_collection_mode={'physics.kernels': 'pyz+py'})
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='Celestial-Evolution-Scientific-Simulation-0.1-Windows-x64',
    debug=False, strip=False, upx=False, console=False)
