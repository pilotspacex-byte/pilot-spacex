# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for pilot-cli sidecar binary.

Build: pyinstaller cli/pilot.spec --noconfirm
Output: dist/pilot-cli/ (onedir bundle)

The entry point binary is dist/pilot-cli/pilot-cli which Tauri
spawns as a sidecar. The entire dist/pilot-cli/ directory must be
copied to tauri-app/src-tauri/binaries/ with the main binary
renamed to pilot-cli-{target_triple}.
"""
import sys
from pathlib import Path

block_cipher = None

# Resolve paths relative to spec file location
cli_dir = Path(SPECPATH)
src_dir = cli_dir / 'src'

a = Analysis(
    [str(cli_dir / 'src' / 'pilot_cli' / 'main.py')],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[
        # Include Jinja2 templates used by implement command
        (str(cli_dir / 'src' / 'pilot_cli' / 'templates'), 'pilot_cli/templates'),
    ],
    hiddenimports=[
        # Core CLI framework
        'typer',
        'typer.main',
        'typer.core',
        'click',
        'click.core',
        'click.decorators',
        # HTTP client
        'httpx',
        'httpx._transports',
        'httpx._transports.default',
        'httpcore',
        'h11',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'sniffio',
        'certifi',
        'idna',
        # Rich console output
        'rich',
        'rich.console',
        'rich.text',
        'rich.markup',
        'rich.progress',
        'rich.prompt',
        'pygments',
        # Git operations
        'git',
        'gitdb',
        'smmap',
        # Jinja2 templating
        'jinja2',
        'jinja2.ext',
        'markupsafe',
        # TOML writing
        'tomli_w',
        # Cryptography (used by backup encryption: AES-256-GCM)
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.asymmetric',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.ciphers.aead',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.primitives.kdf.scrypt',
        'cryptography.hazmat.backends',
        # Pilot CLI modules (main commands)
        'pilot_cli',
        'pilot_cli.main',
        'pilot_cli.commands',
        'pilot_cli.commands.implement',
        'pilot_cli.commands.login',
        'pilot_cli.commands.backup',
        'pilot_cli.config',
        'pilot_cli.api_client',
        'pilot_cli.github_client',
        # Pilot CLI backup subpackage
        'pilot_cli.backup',
        'pilot_cli.backup.archive',
        'pilot_cli.backup.encryption',
        'pilot_cli.backup.pg_backup',
        'pilot_cli.backup.storage_backup',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Dev-only deps — not needed in binary
        'pytest',
        'pytest_asyncio',
        'respx',
        'mypy',
        'ruff',
        'pytest_cov',
        # Unused stdlib modules — reduce binary size
        'tkinter',
        'unittest',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir mode — binaries go in COLLECT
    name='pilot-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # CLI tool — needs console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pilot-cli',
)
