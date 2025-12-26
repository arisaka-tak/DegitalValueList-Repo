#!/usr/bin/env python
"""
シンプルonedirビルドスクリプト
"""
import subprocess
import sys
from pathlib import Path

def main():
    """シンプルonedirビルド"""
    project_root = Path(__file__).parent.parent
    
    print("=== シンプルonedirビルド ===")
    
    # console版onedirビルド
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--console",
        "--name=DegitalValueList_Console_dev",
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
    
    print("PyInstaller実行中...")
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        print("✅ ビルド完了!")
        print(f"📁 出力先: {project_root / 'dist'}")
    else:
        print("❌ ビルド失敗")

if __name__ == "__main__":
    main()