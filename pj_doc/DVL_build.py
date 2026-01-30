#!/usr/bin/env python
"""
最適化onefile版ビルドスクリプト（_internal共有）
"""
import subprocess
import sys
import shutil
from pathlib import Path

def main():
    """最適化onefileビルド"""
    project_root = Path(__file__).parent.parent
    
    print("=== 最適化onefile配布ビルド ===")
    cmd_console = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--debug=all",
        "--name=DigitalValueList",
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
    
    
    print("ビルド中...")
    result_console = subprocess.run(cmd_console, cwd=project_root)
    
    if result_console.returncode != 0:
        print("❌ ビルドに失敗しました")
        return
    print("✅ ビルド完了!")

if __name__ == "__main__":
    main()