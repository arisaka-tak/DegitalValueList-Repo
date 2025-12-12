#!/usr/bin/env python
"""
onedir版配布用ビルドスクリプト（高速起動）
"""
import subprocess
import sys
import shutil
from pathlib import Path

def main():
    """onedirビルド"""
    project_root = Path(__file__).parent.parent
    
    print("=== onedir配布ビルド（高速起動版） ===")
    
    # PyInstallerでonedirビルド（noconsole版）
    cmd_noconsole = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--noconsole",
        "--name=DegitalValueList",
        "--distpath=dist/onedir_web",
        "--workpath=build/onedir_web",
        "--noconfirm",
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
    
    # PyInstallerでonedirビルド（console版）
    cmd_console = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--name=DegitalValueList_Console",
        "--distpath=dist/onedir_console",
        "--workpath=build/onedir_console",
        "--noconfirm",
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
    
    # バッチ処理用onedirビルド
    batch_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--name=batch_ai_extract",
        "--distpath=dist/onedir_batch",
        "--workpath=build/onedir_batch",
        "--noconfirm",
        "--add-data=dashboard;dashboard",
        "--add-data=digital_pricelist_system;digital_pricelist_system",
        "--add-data=manage.py;.",
        "--hidden-import=django",
        "--hidden-import=dashboard.products_master",
        "batch_ai_extract.py"
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
    
    print("バッチ処理用exeをビルド中...")
    batch_result = subprocess.run(batch_cmd, cwd=project_root)
    
    if batch_result.returncode != 0:
        print("❌ バッチ処理用exeビルドに失敗しました")
        return
    
    # 配布用フォルダを作成
    deploy_dir = project_root / "deploy_onedir"
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    deploy_dir.mkdir()
    
    print("配布用フォルダを作成中...")
    
    # onedirフォルダをコピー（noconsole版）
    onedir_src = project_root / "dist" / "onedir_web" / "DegitalValueList"
    onedir_dst = deploy_dir / "DegitalValueList"
    if onedir_src.exists():
        shutil.copytree(onedir_src, onedir_dst)
        print(f"  ✅ {onedir_dst.name}/ をコピー（noconsole版）")
    
    # onedirフォルダをコピー（console版）
    onedir_console_src = project_root / "dist" / "onedir_console" / "DegitalValueList_Console"
    onedir_console_dst = deploy_dir / "DegitalValueList_Console"
    if onedir_console_src.exists():
        shutil.copytree(onedir_console_src, onedir_console_dst)
        print(f"  ✅ {onedir_console_dst.name}/ をコピー（console版）")
    
    # バッチ処理用onedirフォルダをコピー
    batch_onedir_src = project_root / "dist" / "onedir_batch" / "batch_ai_extract"
    batch_onedir_dst = deploy_dir / "batch_ai_extract"
    if batch_onedir_src.exists():
        shutil.copytree(batch_onedir_src, batch_onedir_dst)
        print(f"  ✅ {batch_onedir_dst.name}/ をコピー")
    
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
    (media_dir / "approval").mkdir(exist_ok=True)
    (media_dir / "ai_extract").mkdir(exist_ok=True)
    print(f"  ✅ {media_dir.name}/ フォルダを作成")
    
    # Excelテンプレートファイルをコピー
    excel_template_src = project_root / "degital_value_list.xlsx"
    excel_template_dst = deploy_dir / "degital_value_list.xlsx"
    if excel_template_src.exists():
        shutil.copy2(excel_template_src, excel_template_dst)
        print(f"  ✅ {excel_template_dst.name} をコピー")
    
    print("")
    print("✅ onedirビルド完了!")
    print(f"📁 配布フォルダ: {deploy_dir}")
    print("")
    print("📁 配布構成:")
    print("  deploy_onedir/")
    print("  ├── DegitalValueList/           # Webアプリフォルダ（noconsole版）")
    print("  │   ├── DegitalValueList.exe    # 実行ファイル")
    print("  │   └── _internal/              # ライブラリ群")
    print("  ├── DegitalValueList_Console/   # Webアプリフォルダ（console版）")
    print("  │   ├── DegitalValueList_Console.exe")
    print("  │   └── _internal/")
    print("  ├── batch_ai_extract/           # バッチ処理フォルダ")
    print("  │   ├── batch_ai_extract.exe")
    print("  │   └── _internal/")
    print("  ├── config.ini                 # 環境設定ファイル")
    print("  ├── db.sqlite3                 # データベースファイル")
    print("  ├── degital_value_list.xlsx    # Excelテンプレートファイル")
    print("  └── media/                     # ファイル保存フォルダ")
    print("      ├── approval/              # 決裁書PDF")
    print("      └── ai_extract/            # AI抽出PDF")
    print("")
    print("🚀 配布方法: deploy_onedirフォルダを丸ごとコピーして配布")
    print("💡 使い分け:")
    print("   - DegitalValueList/DegitalValueList.exe: 通常使用（高速起動・コンソール非表示）")
    print("   - DegitalValueList_Console/DegitalValueList_Console.exe: 終了時やトラブル時（高速起動・コンソール表示）")
    print("🔄 環境切り替え: config.iniを差し替えて再起動")
    print("⏰ バッチ処理: batch_ai_extract/batch_ai_extract.exe をタスクスケジューラで定期実行")
    print("⚡ 特徴: onefile版より起動が高速（フォルダ配布）")

if __name__ == "__main__":
    main()