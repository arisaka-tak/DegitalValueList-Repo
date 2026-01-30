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
            # PyInstaller版の場合は実行ファイル名で検索
            if getattr(sys, 'frozen', False):
                exe_name = Path(sys.executable).name
                result = subprocess.run([
                    'wmic', 'process', 'where', 
                    f"Name='{exe_name}'", 
                    'get', 'ProcessId'
                ], capture_output=True, text=True, check=False)
                
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    current_pid = os.getpid()
                    for line in lines[1:]:  # ヘッダーをスキップ
                        pid = line.strip()
                        if pid and pid.isdigit() and int(pid) != current_pid:
                            subprocess.run(['taskkill', '/f', '/pid', pid], 
                                         capture_output=True, check=False)
            else:
                # 開発環境の場合
                result = subprocess.run([
                    'wmic', 'process', 'where', 
                    "CommandLine like '%manage.py%runserver%'", 
                    'get', 'ProcessId'
                ], capture_output=True, text=True, check=False)
                
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:
                        pid = line.strip()
                        if pid and pid.isdigit():
                            subprocess.run(['taskkill', '/f', '/pid', pid], 
                                         capture_output=True, check=False)
        else:  # Unix/Linux/Mac
            if getattr(sys, 'frozen', False):
                exe_name = Path(sys.executable).name
                subprocess.run(['pkill', '-f', exe_name], 
                             capture_output=True, check=False)
            else:
                subprocess.run(['pkill', '-f', 'manage.py runserver'], 
                             capture_output=True, check=False)
        
        # 停止を待つ
        port, _, _, _ = load_config()
        for _ in range(5):
            time.sleep(1)
            if not is_port_in_use(port):
                break
                
    except Exception:
        pass

from digital_pricelist_system.config_paths import CONFIG_PATH
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


    # デフォルト値
    defaults = {
        'port': 8000,
        # 'host': '0.0.0.0',  # 全てのIPアドレスからアクセス可能
        'host': '127.0.0.1',  # ローカルのみアクセス可能
        'auto_browser': True,
        'db_path': 'db.sqlite3'
    }
    
    if CONFIG_PATH.exists():
        try:
            config.read(CONFIG_PATH, encoding='utf-8')
            port = config.getint('SYSTEM', 'port', fallback=defaults['port'])
            host = config.get('SYSTEM', 'host', fallback=defaults['host'])
            auto_browser = config.getboolean('SYSTEM', 'auto_browser', fallback=defaults['auto_browser'])
            db_path = config.get('DATABASE', 'path', fallback=defaults['db_path'])
            return port, host, auto_browser, db_path
        except Exception:
            pass
    
    return defaults['port'], defaults['host'], defaults['auto_browser'], defaults['db_path']

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
    try:
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            print(f"PyInstaller環境: {exe_dir}")
        else:
            exe_dir = Path(__file__).parent
            print(f"開発環境: {exe_dir}")
        
        config_path = CONFIG_PATH
        print(f"config.iniチェック: {config_path}")
        if not config_path.exists():
            print(f"エラー: config.iniが見つかりません: {config_path}")
            if not getattr(sys, 'frozen', False):  # 開発環境のみ
                input("何かキーを押して終了...")
            sys.exit(1)
        
        config = configparser.ConfigParser()
        config.read(CONFIG_PATH, encoding='utf-8')
        print("config.ini読み込み完了")
        
        # データベースファイルチェック
        db_path = config.get('DATABASE', 'path', fallback='db.sqlite3')
        print(f"DBファイルチェック: {db_path}")
        if not Path(db_path).exists():
            print(f"エラー: DBファイルが見つかりません: {db_path}")
            if not getattr(sys, 'frozen', False):  # 開発環境のみ
                input("何かキーを押して終了...")
            sys.exit(1)
        
        # MEDIA_ROOTチェック
        media_root = config.get('FILES', 'media_root', fallback='media')
        print(f"MEDIA_ROOTチェック: {media_root}")
        if not Path(media_root).exists():
            print(f"エラー: MEDIA_ROOTが見つかりません: {media_root}")
            if not getattr(sys, 'frozen', False):  # 開発環境のみ
                input("何かキーを押して終了...")
            sys.exit(1)
        
        print("設定ファイル検証完了")
    except Exception as e:
        print(f"validate_config_pathsエラー: {e}")
        if not getattr(sys, 'frozen', False):  # 開発環境のみ
            input("何かキーを押して終了...")
        sys.exit(1)

def main():
    try:
        # PyInstaller環境での高速化
        if getattr(sys, 'frozen', False):
            print("デジタル価格表システムを起動中...")
            # プロセス優先度を上げる
            try:
                import psutil  # type: ignore
                p = psutil.Process()
                p.nice(psutil.HIGH_PRIORITY_CLASS)
            except ImportError:
                pass
        
        # 設定ファイル検証
        validate_config_paths()
    except Exception as e:
        print(f"初期化エラー: {e}")
        if not getattr(sys, 'frozen', False):  # 開発環境のみ
            input("何かキーを押して終了...")  # コンソールを開いたままにする
        return
    
    # PyInstaller環境でのパス設定
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent
    
    # ログ設定
    logger = setup_logging(exe_dir)
    
    logger.info("デジタル価格表システムを起動しています...")
    
    # manage.pyの存在チェック（PyInstaller環境ではスキップ）
    if not getattr(sys, 'frozen', False) and not (exe_dir / "manage.py").exists():
        logger.error(f"manage.pyが見つかりません: {exe_dir}")
        return
    
    # 設定読み込み
    logger.info(f"設定ファイル: {CONFIG_PATH} {'(存在)' if CONFIG_PATH.exists() else '(デフォルト値使用)'}")
    
    port, host, auto_browser, db_path = load_config()
    
    # サーバー情報を表示
    logger.info(f"サーバー設定: {host}:{port}")
    # if host == '0.0.0.0':
    #     import socket
    #     hostname = socket.gethostname()
    #     local_ip = socket.gethostbyname(hostname)
    #     logger.info(f"他のPCからアクセスする場合: http://{local_ip}:{port}/")
    #     logger.info(f"ホスト名でアクセスする場合: http://{hostname}:{port}/")
    
    # データベースパスを環境変数に設定
    db_full_path = exe_dir / db_path
    os.environ['DATABASE_PATH'] = str(db_full_path)
    
    # DBパスを表示
    db_exists = db_full_path.exists()
    logger.info(f"DBファイル: {db_full_path} {'(存在)' if db_exists else '(新規作成)'}")
    
    # MEDIA_ROOTパスを表示
    from digital_pricelist_system.settings import get_media_root
    media_root = get_media_root()
    logger.info(f"MEDIA_ROOT: {media_root}")
    logger.info(f"PDF保管先: {media_root / 'ai_extract'}")
    
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
    os.chdir(exe_dir)
    
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
            import io
            
            # noconsole環境でstdoutがNoneの場合の対策
            if sys.stdout is None:
                sys.stdout = io.StringIO()
            if sys.stderr is None:
                sys.stderr = io.StringIO()
            
            # Django設定
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
            django.setup()
            
            # Djangoサーバーを別スレッドで起動
            import threading
            def start_server():
                execute_from_command_line(['manage.py', 'runserver', f'{host}:{port}', '--noreload'])
            
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            
            # サーバーが起動するまで待機（30秒まで）
            logger.info("サーバー起動を待機中...")
            for i in range(30):
                time.sleep(1)
                if is_port_in_use(port):
                    logger.info(f"サーバー起動完了: http://127.0.0.1:{port}/")
                    break
            else:
                logger.error("サーバー起動タイムアウト")
                return
            
            # サーバー起動後にブラウザを開く
            if auto_browser:
                logger.info("ブラウザを起動中...")
                webbrowser.open(f'http://127.0.0.1:{port}/')
            
            # メインスレッドで待機
            try:
                while server_thread.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("システムを終了中...")
        else:
            # 開発環境ではサブプロセスで起動
            process = subprocess.Popen([
                python_executable, 'manage.py', 'runserver', f'{host}:{port}'
            ])
            
            # サーバーが起動するまで待機（30秒まで）
            logger.info("サーバー起動を待機中...")
            for i in range(30):
                time.sleep(1)
                if is_port_in_use(port):
                    logger.info(f"サーバー起動完了: http://127.0.0.1:{port}/")
                    break
            else:
                logger.error("サーバー起動タイムアウト")
                process.terminate()
                return
            
            # サーバー起動後にブラウザを開く
            if auto_browser:
                logger.info("ブラウザを起動中...")
                webbrowser.open(f'http://127.0.0.1:{port}/')
            
            # プロセスの終了を待つ
            try:
                process.wait()
            except KeyboardInterrupt:
                logger.info("システムを終了中...")
                process.terminate()
                process.wait()
        
        
    except KeyboardInterrupt:
        logger.info("システムを終了しています...")
        if not getattr(sys, 'frozen', False):
            process.terminate()
            process.wait()
    except Exception as e:
        print(f"システム起動エラー: {e}")
        if getattr(sys, 'frozen', False):
            input("何かキーを押して終了...")
        return

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"致命的エラー: {e}")
        if getattr(sys, 'frozen', False):
            input("何かキーを押して終了...")