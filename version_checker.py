"""
デジタル価格表システム バージョンチェッカー
"""
import shutil
import subprocess
import sys
import os
from pathlib import Path
import time

# サーバー上のファイルパス
SERVER_EXE_PATH = Path(r"\\128.167.100.10\資材・大家畜事業部\04資材部\★デジタル価格表作成プログラム\DigitalValueList.exe")
SERVER_VERSION_PATH = Path(r"\\128.167.100.10\資材・大家畜事業部\04資材部\★デジタル価格表作成プログラム\version.txt")

# ローカルファイルパス
LOCAL_DIR = Path(r"C:\ZBS\DVL")
LOCAL_EXE_PATH = LOCAL_DIR / "DigitalValueList.exe"
LOCAL_VERSION_PATH = LOCAL_DIR / "version.txt"

def get_local_version():
    """ローカルのバージョンを取得"""
    try:
        if LOCAL_VERSION_PATH.exists():
            return LOCAL_VERSION_PATH.read_text(encoding='utf-8').strip()
        return "v202501010001"
    except Exception:
        return "v202501010001"

def get_server_version():
    """サーバーのバージョンを取得"""
    try:
        if SERVER_VERSION_PATH.exists():
            return SERVER_VERSION_PATH.read_text(encoding='utf-8').strip()
        return "v202501010001"
    except Exception:
        return "v202501010001"

def is_newer_version(server_version, local_version):
    """バージョン比較"""
    def extract_version_number(v):
        # v{yyyymmddnnn}から数値部分を抽出
        if v.startswith('v') and len(v) >= 11:
            return int(v[1:])
        return 0
    
    try:
        server_num = extract_version_number(server_version)
        local_num = extract_version_number(local_version)
        print(f"デバッグ: サーバー={server_num}, ローカル={local_num}")
        return server_num > local_num
    except ValueError:
        return False

def update_program():
    """メインプログラムを更新"""
    if not SERVER_EXE_PATH.exists():
        print("❌ サーバー上にメインプログラムが見つかりません")
        return False
    
    try:
        print("📥 メインプログラムを更新中...")
        
        # ディレクトリを作成
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        
        # 実行中のプロセスを終了させる
        if LOCAL_EXE_PATH.exists():
            print("🔄 実行中のプロセスを終了中...")
            try:
                # Windowsで実行中のプロセスを終了
                subprocess.run([
                    'taskkill', '/f', '/im', 'DigitalValueList.exe'
                ], capture_output=True, check=False)
                time.sleep(2)  # プロセス終了を待つ
            except Exception:
                pass
        
        # バックアップ作成
        if LOCAL_EXE_PATH.exists():
            backup_path = LOCAL_EXE_PATH.with_suffix('.exe.backup')
            try:
                shutil.copy2(LOCAL_EXE_PATH, backup_path)
                print("💾 バックアップ作成完了")
            except Exception as e:
                print(f"⚠️ バックアップ作成失敗: {e}")
        
        # 既存ファイルを削除（ロックされている場合の対策）
        if LOCAL_EXE_PATH.exists():
            try:
                LOCAL_EXE_PATH.unlink()
                print("🗑️ 既存ファイルを削除")
            except Exception as e:
                print(f"⚠️ 既存ファイル削除失敗: {e}")
                # 一時ファイル名で更新を試行
                temp_path = LOCAL_EXE_PATH.with_suffix('.exe.new')
                shutil.copy2(SERVER_EXE_PATH, temp_path)
                print(f"📦 一時ファイルとして保存: {temp_path}")
                print("⚠️ 次回起動時に手動でファイルを置き換えてください")
                return False
        
        # 新しいファイルをコピー
        shutil.copy2(SERVER_EXE_PATH, LOCAL_EXE_PATH)
        print("📦 新しいファイルをコピー")
        
        # バージョンファイルもコピー
        if SERVER_VERSION_PATH.exists():
            shutil.copy2(SERVER_VERSION_PATH, LOCAL_VERSION_PATH)
        
        print("✅ 更新完了")
        return True
        
    except Exception as e:
        print(f"❌ 更新エラー: {e}")
        return False

def launch_main_program():
    """メインプログラムを起動"""
    if not LOCAL_EXE_PATH.exists():
        print("❌ メインプログラムが見つかりません")
        return False
    
    try:
        print("🚀 メインプログラムを起動中...")
        # Windowsで独立したプロセスとして起動
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                [str(LOCAL_EXE_PATH)], 
                cwd=LOCAL_DIR,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:  # Unix/Linux/Mac
            subprocess.Popen([str(LOCAL_EXE_PATH)], cwd=LOCAL_DIR)
        return True
    except Exception as e:
        print(f"❌ 起動エラー: {e}")
        return False

def main():
    print("=== デジタル価格表システム バージョンチェッカー ===")
    
    # バージョンチェック
    local_version = get_local_version()
    server_version = get_server_version()
    
    print(f"ローカルバージョン: {local_version}")
    print(f"サーバーバージョン: {server_version}")
    
    # 更新が必要かチェック
    if is_newer_version(server_version, local_version) or not LOCAL_EXE_PATH.exists():
        if is_newer_version(server_version, local_version):
            print("🔄 新しいバージョンが利用可能です")
        else:
            print("📥 メインプログラムが見つからないためダウンロードします")
        if update_program():
            print("✅ 更新が完了しました")
        else:
            print("❌ 更新に失敗しました")
            input("何かキーを押して終了...")
            return
    else:
        print("✅ 最新バージョンです")
    
    # メインプログラム起動
    if launch_main_program():
        print("✅ メインプログラムを起動しました")
    else:
        print("❌ メインプログラムの起動に失敗しました")
        input("何かキーを押して終了...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 致命的エラー: {e}")
        input("何かキーを押して終了...")