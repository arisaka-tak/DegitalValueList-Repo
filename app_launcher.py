#!/usr/bin/env python
"""
デジタル価格表システム - 配布用ランチャー
PyInstaller --onefile 対応版
"""
import os
import sys
import time
import webbrowser
import socket
import threading
import configparser
from pathlib import Path

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings_production')

def is_port_in_use(port):
    """指定ポートが使用中かチェック"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def setup_django_environment():
    """Django環境をセットアップ"""
    # 実行ファイルのディレクトリを取得
    if getattr(sys, 'frozen', False):
        # PyInstallerでビルドされた場合
        app_dir = Path(sys.executable).parent
        # 一時ディレクトリを設定（PyInstallerの内部ファイル用）
        if hasattr(sys, '_MEIPASS'):
            sys.path.insert(0, sys._MEIPASS)
    else:
        # 開発環境
        app_dir = Path(__file__).parent
        sys.path.insert(0, str(app_dir))
    
    # 作業ディレクトリを設定
    os.chdir(app_dir)
    
    return app_dir

def run_django_server():
    """Djangoサーバーを起動"""
    import django
    from django.core.management import execute_from_command_line
    from django.core.wsgi import get_wsgi_application
    
    # Django初期化
    django.setup()
    
    # データベース初期化（必要に応じて）
    try:
        execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])
    except:
        pass
    
    # サーバー起動
    execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000', '--noreload'])

def main():
    """メイン処理"""
    try:
        # Django環境セットアップ
        app_dir = setup_django_environment()
        
        # 設定ファイルからデータベースパスを読み込み
        config = configparser.ConfigParser()
        config_path = app_dir / 'config.ini'
        
        db_locations = [app_dir / 'db.sqlite3']  # デフォルト
        
        if config_path.exists():
            config.read(config_path, encoding='utf-8')
            if 'DATABASE' in config and 'path' in config['DATABASE']:
                db_path_str = config['DATABASE']['path']
                if db_path_str:
                    db_locations.insert(0, Path(db_path_str))
        
        # データベースファイルの存在チェック
        db_found = False
        for db_path in db_locations:
            try:
                if db_path.exists():
                    print(f"データベースを発見: {db_path}")
                    db_found = True
                    break
            except (OSError, PermissionError):
                continue
        
        if not db_found:
            print("データベースファイルが見つかりません。")
            print("config.ini の [DATABASE] path を確認してください。")
            input("Enterキーを押して終了...")
            return
        
        # ポートチェック
        if is_port_in_use(8000):
            print("ポート8000は既に使用されています。")
            input("Enterキーを押して終了...")
            return
        
        print("デジタル価格表システムを起動しています...")
        
        # Djangoサーバーを別スレッドで起動
        server_thread = threading.Thread(target=run_django_server, daemon=True)
        server_thread.start()
        
        # サーバー起動を待機
        for i in range(30):  # 30秒待機
            if is_port_in_use(8000):
                break
            time.sleep(1)
        else:
            print("サーバーの起動に失敗しました。")
            input("Enterキーを押して終了...")
            return
        
        print("サーバーが起動しました。ブラウザを開きます...")
        
        # ブラウザを開く
        webbrowser.open("http://127.0.0.1:8000/")
        
        print("システムが起動しました。")
        print("ブラウザでアプリケーションをご利用ください。")
        print("終了するには、このウィンドウを閉じるかCtrl+Cを押してください。")
        
        # メインスレッドを維持
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nシステムを終了しています...")
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        input("Enterキーを押して終了...")

if __name__ == "__main__":
    main()