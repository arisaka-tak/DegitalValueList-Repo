#!/usr/bin/env python
"""
シンプルな配布用ビルドスクリプト
"""
import subprocess
import sys
from pathlib import Path

def main():
    """シンプルビルド"""
    project_root = Path(__file__).parent.parent  # pj_docからプロジェクトルートへ
    
    print("=== シンプル配布ビルド ===")
    
    # PyInstallerで直接ビルド
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name=DigitalPriceList", 
        "--add-data=templates;templates",
        "--add-data=static;static", 
        "--add-data=dashboard;dashboard",
        "--add-data=digital_pricelist_system;digital_pricelist_system",
        "--add-data=manage.py;.",
        "--hidden-import=django",
        "--hidden-import=dashboard.products_master",
        "Django_run.py"
    ]
    
    print("PyInstallerを実行中...")
    subprocess.run(cmd, cwd=project_root)
    
    print("✅ ビルド完了!")
    print("📁 dist/DigitalPriceList.exe が作成されました")
    print("")
    print("📁 配布構成:")
    print("  DigitalPriceList.exe  # 実行ファイル")
    print("  config.ini           # 環境設定ファイル（本番/テスト切り替え用）")
    print("  db.sqlite3           # データベースファイル")
    print("")
    print("🔄 環境切り替え: config.iniを差し替えて再起動")

if __name__ == "__main__":
    main()