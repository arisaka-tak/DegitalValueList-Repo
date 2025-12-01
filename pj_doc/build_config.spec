# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# プロジェクトルート
project_root = Path(SPECPATH)

# 収集するデータファイル
datas = [
    # Djangoテンプレート
    (str(project_root / 'templates'), 'templates'),
    # 静的ファイル
    (str(project_root / 'static'), 'static'),
    # Django設定
    (str(project_root / 'digital_pricelist_system'), 'digital_pricelist_system'),
    # アプリケーション
    (str(project_root / 'dashboard'), 'dashboard'),
    # manage.py
    (str(project_root / 'manage.py'), '.'),
    # 初期データベース（存在する場合）
    (str(project_root / 'db.sqlite3'), '.') if (project_root / 'db.sqlite3').exists() else None,
]

# Noneを除去
datas = [d for d in datas if d is not None]

# 隠れたインポート
hiddenimports = [
    'django',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard.products_master',
    'dashboard.products_master.apps',
    'dashboard.products_master.models',
    'dashboard.products_master.forms',
    'dashboard.products_master.product_list.views',
    'dashboard.products_master.product_detail.views',
    'dashboard.products_master.product_create.views',
    'dashboard.products_master.integrated_pricelist.views',
    'digital_pricelist_system.settings',
    'digital_pricelist_system.urls',
    'digital_pricelist_system.wsgi',
]

a = Analysis(
    ['app_launcher.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DigitalPriceList',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)