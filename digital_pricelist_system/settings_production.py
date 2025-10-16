"""
本番環境用設定（PyInstaller配布版）
"""
import os
from pathlib import Path
from .settings import *

# データベース設定を環境変数またはファイル検索で決定
def find_database_path():
    """データベースファイルを検索"""
    # 1. 環境変数で指定
    if 'DATABASE_PATH' in os.environ:
        return os.environ['DATABASE_PATH']
    
    # 2. 実行ファイルと同じディレクトリ
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent.parent
    
    db_path = exe_dir / 'db.sqlite3'
    if db_path.exists():
        return str(db_path)
    
    # 3. ネットワークドライブを検索
    network_paths = [
        'Z:/DigitalPriceList/db.sqlite3',  # 例：Zドライブ
        '//server/share/DigitalPriceList/db.sqlite3',  # UNCパス
    ]
    
    for path in network_paths:
        if Path(path).exists():
            return path
    
    # 4. デフォルト（ローカル）
    return str(exe_dir / 'db.sqlite3')

# データベース設定
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': find_database_path(),
        'OPTIONS': {
            'timeout': 30,  # ネットワーク遅延対応
        }
    }
}

# 静的ファイル設定（PyInstaller用）
STATIC_URL = '/static/'
STATIC_ROOT = None  # 開発サーバー使用時は不要

# デバッグ設定
DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# ログ設定
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'digital_pricelist.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}