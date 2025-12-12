#!/usr/bin/env python
"""
digital_valuelist_system Djangoサーバーを起動してブラウザを自動で開くスクリプト
"""
import os
import sys
import time
import webbrowser
import subprocess
import socket
import configparser
import logging
from datetime import datetime
from pathlib import Path

def is_port_in_use(port):
    """指定ポートが使用中かチェック"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def kill_existing_server():
    """既存のDjangoサーバーを停止"""
    try:
        if os.name == 'nt':  # Windows
            # Djangoサーバーのみを特定して停止
            result = subprocess.run([
                'wmic', 'process', 'where', 
                "CommandLine like '%manage.py%runserver%'", 
                'get', 'ProcessId'
            ], capture_output=True, text=True, check=False)
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # ヘッダーをスキップ
                    pid = line.strip()
                    if pid and pid.isdigit():
                        subprocess.run(['taskkill', '/f', '/pid', pid], 
                                     capture_output=True, check=False)
        else:  # Unix/Linux/Mac
            subprocess.run(['pkill', '-f', 'manage.py runserver'], 
                         capture_output=True, check=False)
        
        # 停止を待つ（ポート番号は動的に取得）
        port, _, _ = load_config()
        for _ in range(5):
            time.sleep(1)
            if not is_port_in_use(port):
                break
                
    except Exception:
        pass

def find_venv_python():
    """仮想環境のPythonを探す"""
    project_root = Path(__file__).parent
    
    # 仮想環境のパスを探す
    venv_paths = [
        project_root / "venv" / "Scripts" / "python.exe",  # Windows
        project_root / "venv" / "bin" / "python",          # Unix/Linux/Mac
        project_root / ".venv" / "Scripts" / "python.exe", # Windows (.venv)
        project_root / ".venv" / "bin" / "python",         # Unix/Linux/Mac (.venv)
    ]
    
    for venv_python in venv_paths:
        if venv_python.exists():
            return str(venv_python)
    
    return sys.executable  # フォールバック

def load_config():
    """config.iniを読み込み"""
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent / "config.ini"
    
    # デフォルト値
    defaults = {
        'port': 8000,
        'auto_browser': True,
        'db_path': 'db.sqlite3'
    }
    
    if config_path.exists():
        try:
            config.read(config_path, encoding='utf-8')
            port = config.getint('SYSTEM', 'port', fallback=defaults['port'])
            auto_browser = config.getboolean('SYSTEM', 'auto_browser', fallback=defaults['auto_browser'])
            db_path = config.get('DATABASE', 'path', fallback=defaults['db_path'])
            return port, auto_browser, db_path
        except Exception:
            pass
    
    return defaults['port'], defaults['auto_browser'], defaults['db_path']

def setup_logging(project_root):
    """ログ設定"""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # ログ設定
    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    
    # 開発環境でのみコンソール出力を追加
    if not getattr(sys, 'frozen', False) and sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

def validate_config_paths():
    """設定ファイルのパスを検証"""
    if getattr(sys, 'frozen', False):
        project_root = Path(sys.executable).parent
    else:
        project_root = Path(__file__).parent
    
    config_path = project_root / "config.ini"
    if not config_path.exists():
        sys.exit(1)
    
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')
    
    # データベースファイルチェック
    db_path = config.get('DATABASE', 'path', fallback='db.sqlite3')
    if not Path(db_path).is_absolute():
        db_path = project_root / db_path
    if not Path(db_path).exists():
        sys.exit(1)
    
    # MEDIA_ROOTチェック
    media_root = config.get('FILES', 'media_root', fallback='media')
    if not Path(media_root).is_absolute():
        media_root = project_root / media_root
    if not Path(media_root).exists():
        sys.exit(1)

def main():
    # 設定ファイル検証
    validate_config_paths()
    
    # PyInstaller環境でのパス設定
    if getattr(sys, 'frozen', False):
        project_root = Path(sys.executable).parent
    else:
        project_root = Path(__file__).parent
    
    # ログ設定
    logger = setup_logging(project_root)
    
    logger.info("デジタル価格表システムを起動しています...")
    
    # manage.pyの存在チェック（PyInstaller環境ではスキップ）
    if not getattr(sys, 'frozen', False) and not (project_root / "manage.py").exists():
        logger.error(f"manage.pyが見つかりません: {project_root}")
        return
    
    # 設定読み込み
    config_path = project_root / "config.ini"
    logger.info(f"設定ファイル: {config_path} {'(存在)' if config_path.exists() else '(デフォルト値使用)'}")
    
    port, auto_browser, db_path = load_config()
    
    # データベースパスを環境変数に設定
    db_full_path = project_root / db_path
    os.environ['DATABASE_PATH'] = str(db_full_path)
    
    # DBパスを表示
    db_exists = db_full_path.exists()
    logger.info(f"DBファイル: {db_full_path} {'(存在)' if db_exists else '(新規作成)'}")
    
    # MEDIA_ROOTパスを表示
    from digital_pricelist_system.settings import get_media_root
    media_root = get_media_root()
    logger.info(f"MEDIA_ROOT: {media_root}")
    
    # Python実行ファイルを取得
    if getattr(sys, 'frozen', False):
        # PyInstaller環境では現在の実行ファイルを使用
        python_executable = sys.executable
        logger.info(f"Python実行ファイル: {python_executable}")
    else:
        # 開発環境では仮想環境を探す
        python_executable = find_venv_python()
        logger.info(f"仮想環境Python: {python_executable}")
        
        # Djangoがインストールされているかチェック
        try:
            subprocess.run([python_executable, '-c', 'import django'], 
                          capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            logger.error("Djangoがインストールされていません")
            return
    
    # 現在のディレクトリを変更
    os.chdir(project_root)
    
    # 指定ポートが使用中かチェック
    if is_port_in_use(port):
        kill_existing_server()
    
    # サーバー起動
    try:
        logger.info(f"ポート {port} でDjangoサーバーを起動中...")
        
        if getattr(sys, 'frozen', False):
            # PyInstaller環境ではDjangoを直接起動
            import django
            from django.core.management import execute_from_command_line
            
            # Django設定
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
            django.setup()
            
            logger.info("ブラウザを起動しています...")
            if auto_browser:
                webbrowser.open(f"http://127.0.0.1:{port}/")
            
            logger.info(f"サーバーが起動しました: http://127.0.0.1:{port}/")
            
            # 開発環境でのみコンソールメッセージ表示
            if not getattr(sys, 'frozen', False):
                logger.info("ブラウザを起動しています...")
                logger.info(f"サーバーが起動しました: http://127.0.0.1:{port}/")
                logger.info("終了するには、このウィンドウを閉じるかCtrl+Cを押してください。")
            
            # Djangoサーバーを起動
            execute_from_command_line(['manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'])
        else:
            # 開発環境では従来通り
            process = subprocess.Popen([
                python_executable, "manage.py", "runserver", f"127.0.0.1:{port}"
            ])
            
            # サーバーが起動するまで待機
            for i in range(10):
                time.sleep(1)
                if is_port_in_use(port):
                    break
            
            # ブラウザを開く（設定で有効な場合のみ）
            if auto_browser:
                webbrowser.open(f"http://127.0.0.1:{port}/")
            
            # プロセスの終了を待つ
            try:
                process.wait()
            except KeyboardInterrupt:
                raise
        
        
    except KeyboardInterrupt:
        logger.info("システムを終了しています...")
        if not getattr(sys, 'frozen', False):
            process.terminate()
            process.wait()
    except Exception as e:
        logger.error(f"システム起動エラー: {e}")
        if not getattr(sys, 'frozen', False):
            logger.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()