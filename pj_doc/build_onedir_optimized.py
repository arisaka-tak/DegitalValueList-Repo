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
    
    # まずnoconsole版をビルド
    # cmd_noconsole = [
    #     sys.executable, "-m", "PyInstaller",
    #     "--onedir",
    #     "--noconsole",
    #     "--name=DegitalValueList",
    #     "--distpath=dist/onedir_base",
    #     "--workpath=build/onedir_base",
    #     "--noconfirm",
    #     "--add-data=templates;templates",
    #     "--add-data=static;static", 
    #     "--add-data=dashboard;dashboard",
    #     "--add-data=digital_pricelist_system;digital_pricelist_system",
    #     "--add-data=manage.py;.",
    #     "--add-data=degital_value_list.xlsx;.",
    #     "--hidden-import=django",
    #     "--hidden-import=dashboard.products_master",
    #     "Django_run.py"
    # ]
    
    # console版もonedirでビルド（同じ構成）
    cmd_console = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
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
    
    # print("ベース版（noconsole + _internal）をビルド中...")
    # result_base = subprocess.run(cmd_noconsole, cwd=project_root)
    # 
    # if result_base.returncode != 0:
    #     print("❌ ベース版ビルドに失敗しました")
    #     return
    
    print("console版をビルド中...")
    result_console = subprocess.run(cmd_console, cwd=project_root)
    
    if result_console.returncode != 0:
        print("❌ console版ビルドに失敗しました")
        return
    
    # 配布用フォルダを作成
    deploy_dir = project_root / "deploy_onedir_optimized"
    # if deploy_dir.exists():
    #     shutil.rmtree(deploy_dir)
    deploy_dir.mkdir(exist_ok=True)
    
    # print("console版のみ配布フォルダを作成中...")
    
    # console版をコピー（実際のフォルダ名を使用）
    # console_src = project_root / "dist" / "onedir_console" / "DegitalValueList_Console"
    # if console_src.exists():
    #     shutil.copytree(console_src, deploy_dir, dirs_exist_ok=True)
    #     print("  ✅ console版（_internal含む）をコピー")
    
    # 以下はコメントアウト（noconsole版用）
    # base_src = project_root / "dist" / "onedir_base" / "DegitalValueList"
    # if base_src.exists():
    #     shutil.copytree(base_src, deploy_dir, dirs_exist_ok=True)
    #     print("  ✅ ベース版（noconsole + _internal）をコピー")
    # 
    # console_exe_src = project_root / "dist" / "onedir_console" / "DegitalValueList_Console" / "DegitalValueList_Console.exe"
    # console_exe_dst = deploy_dir / "DegitalValueList_Console.exe"
    # if console_exe_src.exists():
    #     shutil.copy2(console_exe_src, console_exe_dst)
    #     print("  ✅ console版exeを追加")
    
    # 設定ファイル等をコピー
    # for file_name in ["config.ini", "db.sqlite3", "degital_value_list.xlsx"]:
    #     src = project_root / file_name
    #     dst = deploy_dir / file_name
    #     if src.exists():
    #         shutil.copy2(src, dst)
    #         print(f"  ✅ {file_name} をコピー")
    
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
    print("  deploy_onedir_optimized/")
    print("  ├── DegitalValueList_Console.exe # console版")
    print("  ├── _internal/                   # ライブラリ群")
    print("  ├── config.ini")
    print("  ├── db.sqlite3")
    print("  └── media/")
    print("")
    print("💡 console版のみでテスト用")
    print("⚡ 特徴: onefile版より高速起動")

if __name__ == "__main__":
    main()