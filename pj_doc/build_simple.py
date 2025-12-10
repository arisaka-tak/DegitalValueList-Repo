#!/usr/bin/env python
"""
シンプルな配布用ビルドスクリプト
"""
import subprocess
import sys
import shutil
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
        "--add-data=dashboard/products_master/pdf_processing;dashboard/products_master/pdf_processing",
        "--hidden-import=django",
        "--hidden-import=dashboard.products_master",
        "Django_run.py"
    ]
    
    print("PyInstallerを実行中...")
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode != 0:
        print("❌ PyInstallerビルドに失敗しました")
        return
    
    # 配布用フォルダを作成
    deploy_dir = project_root / "deploy"
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    deploy_dir.mkdir()
    
    print("配布用フォルダを作成中...")
    
    # exeファイルをコピー
    exe_src = project_root / "dist" / "DigitalPriceList.exe"
    exe_dst = deploy_dir / "DigitalPriceList.exe"
    if exe_src.exists():
        shutil.copy2(exe_src, exe_dst)
        print(f"  ✅ {exe_dst.name} をコピー")
    
    # config.iniをコピー
    config_src = project_root / "config.ini"
    config_dst = deploy_dir / "config.ini"
    if config_src.exists():
        shutil.copy2(config_src, config_dst)
        print(f"  ✅ {config_dst.name} をコピー")
    
    # データベースファイルをコピー
    db_src = project_root / "db.sqlite3"
    db_dst = deploy_dir / "db.sqlite3"
    if db_src.exists():
        shutil.copy2(db_src, db_dst)
        print(f"  ✅ {db_dst.name} をコピー")
    
    print("")
    print("✅ ビルド完了!")
    print(f"📁 配布フォルダ: {deploy_dir}")
    print("")
    print("📁 配布構成:")
    print("  deploy/")
    print("  ├── DigitalPriceList.exe  # 実行ファイル")
    print("  ├── config.ini           # 環境設定ファイル")
    print("  └── db.sqlite3           # データベースファイル")
    print("")
    print("🚀 配布方法: deployフォルダを丸ごとコピーして配布")
    print("🔄 環境切り替え: config.iniを差し替えて再起動")

if __name__ == "__main__":
    main()