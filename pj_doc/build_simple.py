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
    
    # PyInstallerで直接ビルド（noconsole版）
    cmd_noconsole = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name=DegitalValueList",
        "--distpath=dist/web",
        "--add-data=templates;templates",
        "--add-data=static;static", 
        "--add-data=dashboard;dashboard",
        "--add-data=digital_pricelist_system;digital_pricelist_system",
        "--add-data=manage.py;.",
        "--add-data=dashboard/products_master/pdf_processing;dashboard/products_master/pdf_processing",
        "--add-data=degital_value_list.xlsx;.",
        "--hidden-import=django",
        "--hidden-import=dashboard.products_master",
        "Django_run.py"
    ]
    
    # PyInstallerでコンソール版もビルド
    cmd_console = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name=DegitalValueList_Console",
        "--distpath=dist/console",
        "--add-data=templates;templates",
        "--add-data=static;static", 
        "--add-data=dashboard;dashboard",
        "--add-data=digital_pricelist_system;digital_pricelist_system",
        "--add-data=manage.py;.",
        "--add-data=dashboard/products_master/pdf_processing;dashboard/products_master/pdf_processing",
        "--add-data=degital_value_list.xlsx;.",
        "--hidden-import=django",
        "--hidden-import=dashboard.products_master",
        "Django_run.py"
    ]
    
    print("PyInstaller（noconsole版）を実行中...")
    result_noconsole = subprocess.run(cmd_noconsole, cwd=project_root)
    
    if result_noconsole.returncode != 0:
        print("❌ PyInstaller（noconsole版）ビルドに失敗しました")
        return
    
    print("PyInstaller（console版）を実行中...")
    result_console = subprocess.run(cmd_console, cwd=project_root)
    
    if result_console.returncode != 0:
        print("❌ PyInstaller（console版）ビルドに失敗しました")
        return
    
    # バッチ処理用exeをビルド
    batch_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name=batch_ai_extract",
        "--distpath=dist/batch",
        "--add-data=dashboard;dashboard",
        "--add-data=digital_pricelist_system;digital_pricelist_system",
        "--add-data=manage.py;.",
        "--hidden-import=django",
        "--hidden-import=dashboard.products_master",
        "batch_ai_extract.py"
    ]
    
    print("バッチ処理用exeをビルド中...")
    batch_result = subprocess.run(batch_cmd, cwd=project_root)
    
    if batch_result.returncode != 0:
        print("❌ バッチ処理用exeビルドに失敗しました")
        return
    
    # 配布用フォルダを作成
    deploy_dir = project_root / "deploy"
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    deploy_dir.mkdir()
    
    print("配布用フォルダを作成中...")
    
    # exeファイルをコピー（noconsole版）
    exe_src = project_root / "dist" / "web" / "DegitalValueList.exe"
    exe_dst = deploy_dir / "DegitalValueList.exe"
    if exe_src.exists():
        shutil.copy2(exe_src, exe_dst)
        print(f"  ✅ {exe_dst.name} をコピー（noconsole版）")
    
    # exeファイルをコピー（console版）
    exe_console_src = project_root / "dist" / "console" / "DegitalValueList_Console.exe"
    exe_console_dst = deploy_dir / "DegitalValueList_Console.exe"
    if exe_console_src.exists():
        shutil.copy2(exe_console_src, exe_console_dst)
        print(f"  ✅ {exe_console_dst.name} をコピー（console版）")
    
    # バッチ処理用exeをコピー
    batch_exe_src = project_root / "dist" / "batch" / "batch_ai_extract.exe"
    batch_exe_dst = deploy_dir / "batch_ai_extract.exe"
    if batch_exe_src.exists():
        shutil.copy2(batch_exe_src, batch_exe_dst)
        print(f"  ✅ {batch_exe_dst.name} をコピー")
    
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
    
    # mediaフォルダを作成
    media_dir = deploy_dir / "media"
    media_dir.mkdir(exist_ok=True)
    print(f"  ✅ {media_dir.name} フォルダを作成")
    
    # media/approvalフォルダを作成
    approval_dir = media_dir / "approval"
    approval_dir.mkdir(exist_ok=True)
    print(f"  ✅ {approval_dir.name} フォルダを作成")
    
    # media/ai_extractフォルダを作成
    ai_extract_dir = media_dir / "ai_extract"
    ai_extract_dir.mkdir(exist_ok=True)
    print(f"  ✅ {ai_extract_dir.name} フォルダを作成")
    
    # Excelテンプレートファイルをコピー
    excel_template_src = project_root / "degital_value_list.xlsx"
    excel_template_dst = deploy_dir / "degital_value_list.xlsx"
    if excel_template_src.exists():
        shutil.copy2(excel_template_src, excel_template_dst)
        print(f"  ✅ {excel_template_dst.name} をコピー")
    
    print("")
    print("✅ ビルド完了!")
    print(f"📁 配布フォルダ: {deploy_dir}")
    print("")
    print("📁 配布構成:")
    print("  deploy/")
    print("  ├── DegitalValueList.exe  # Webアプリ実行ファイル（noconsole版）")
    print("  ├── DegitalValueList_Console.exe  # Webアプリ実行ファイル（console版）")
    print("  ├── batch_ai_extract.exe  # バッチ処理実行ファイル")
    print("  ├── config.ini           # 環境設定ファイル")
    print("  ├── db.sqlite3           # データベースファイル")
    print("  ├── degital_value_list.xlsx # Excelテンプレートファイル")
    print("  └── media/               # ファイル保存フォルダ")
    print("      ├── approval/        # 決裁書PDF")
    print("      └── ai_extract/      # AI抽出PDF")
    print("")
    print("🚀 配布方法: deployフォルダを丸ごとコピーして配布")
    print("💡 使い分け:")
    print("   - DegitalValueList.exe: 通常使用（コンソール非表示）")
    print("   - DegitalValueList_Console.exe: 終了時やトラブル時（コンソール表示）")
    print("🔄 環境切り替え: config.iniを差し替えて再起動")
    print("⏰ バッチ処理: batch_ai_extract.exe をタスクスケジューラで定期実行")

if __name__ == "__main__":
    main()