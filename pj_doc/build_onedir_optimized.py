#!/usr/bin/env python
"""
最適化onedir版ビルドスクリプト（_internal共有）
"""
import subprocess
import sys
import shutil
from pathlib import Path

def main():
    """最適化onedirビルド"""
    project_root = Path(__file__).parent.parent
    
    print("=== 最適化onedir配布ビルド ===")
    cmd_console = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--debug=all",
        "--name=DegitalValueList",
        "--distpath=dist/onedir_console",
        "--workpath=build/onedir_console",
        "--noconfirm",
        "--add-data=templates;templates",
        "--add-data=static;static", 
        "--add-data=dashboard;dashboard",
        "--add-data=digital_pricelist_system;digital_pricelist_system",
        "--add-data=manage.py;.",
        "--add-data=degital_value_list.xlsx;.",
        "--hidden-import=django",
        "--hidden-import=dashboard.products_master",
        "Django_run.py"
    ]
    
    
    print("console版をビルド中...")
    result_console = subprocess.run(cmd_console, cwd=project_root)
    
    if result_console.returncode != 0:
        print("❌ console版ビルドに失敗しました")
        return
    
    # 配布用フォルダを作成
    deploy_dir = project_root / "deploy"
    deploy_dir.mkdir(exist_ok=True)
    
    # 実行ファイルをコピー
    exe_src = project_root / "dist" / "onedir_console" / "DegitalValueList.exe"
    exe_dst = deploy_dir / "DegitalValueList.exe"
    if exe_src.exists():
        shutil.copy2(exe_src, exe_dst)
        print(f"  ✅ {exe_src.name} をコピー")
    
    # 設定ファイル等をコピー
    for file_name in ["config.ini", "db.sqlite3", "degital_value_list.xlsx"]:
         src = project_root / file_name
         dst = deploy_dir / file_name
         if src.exists():
             shutil.copy2(src, dst)
             print(f"  ✅ {file_name} をコピー")
    
    # mediaフォルダを作成
    media_dir = deploy_dir / "media"
    media_dir.mkdir(exist_ok=True)
    (media_dir / "approval").mkdir(exist_ok=True)
    (media_dir / "ai_extract").mkdir(exist_ok=True)
    print("  ✅ media/ フォルダを作成")
    
    print("")
    print("✅ console版onedirビルド完了!")
    print(f"📁 配布フォルダ: {deploy_dir}")
    print("")
    print("📁 console版構成:")
    print("  deploy/")
    print("  ├── DegitalValueList.exe # 実行ファイル")
    print("  ├── config.ini")
    print("  ├── db.sqlite3")
    print("  └── media/")

if __name__ == "__main__":
    main()