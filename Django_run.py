#!/usr/bin/env python
"""
digital_pricelist_system Djangoサーバーを起動してブラウザを自動で開くスクリプト
"""
import os
import sys
import time
import webbrowser
import subprocess
import socket
import configparser
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

def main():
    # プロジェクトルートディレクトリ（manage.pyがある場所）
    project_root = Path(__file__).parent
    
    if not (project_root / "manage.py").exists():
        return
    
    # 設定読み込み
    port, auto_browser, db_path = load_config()
    
    # データベースパスを環境変数に設定
    os.environ['DATABASE_PATH'] = str(project_root / db_path)
    
    # 仮想環境のPythonを取得
    venv_python = find_venv_python()
    
    # Djangoがインストールされているかチェック
    try:
        subprocess.run([venv_python, '-c', 'import django'], 
                      capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return
    
    # 現在のディレクトリを変更
    os.chdir(project_root)
    
    # 指定ポートが使用中かチェック
    if is_port_in_use(port):
        kill_existing_server()
    
    # サーバー起動（バックグラウンドで実行）
    try:
        # サーバープロセスを開始（ログを表示するため標準出力をキャプチャしない）
        process = subprocess.Popen([
            venv_python, "manage.py", "runserver", f"127.0.0.1:{port}"
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
        process.terminate()
        process.wait()
    except Exception:
        pass

if __name__ == "__main__":
    main()