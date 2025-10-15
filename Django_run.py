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
        
        # 停止を待つ
        for _ in range(5):
            time.sleep(1)
            if not is_port_in_use(8000):
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

def main():
    # プロジェクトルートディレクトリ（manage.pyがある場所）
    project_root = Path(__file__).parent
    
    if not (project_root / "manage.py").exists():
        return
    
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
    
    # ポート8000が使用中かチェック
    if is_port_in_use(8000):
        kill_existing_server()
    
    # サーバー起動（バックグラウンドで実行）
    try:
        # サーバープロセスを開始（ログを表示するため標準出力をキャプチャしない）
        process = subprocess.Popen([
            venv_python, "manage.py", "runserver", "127.0.0.1:8000"
        ])
        
        # サーバーが起動するまで待機
        for i in range(10):
            time.sleep(1)
            if is_port_in_use(8000):
                break
        
        # ブラウザを開く
        webbrowser.open("http://127.0.0.1:8000/")
        
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