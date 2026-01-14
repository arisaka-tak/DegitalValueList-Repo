#!/usr/bin/env python
"""
batch_ai_extract.py をPyInstallerでonefileビルドするスクリプト
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    # プロジェクトルート
    project_root = Path(__file__).parent.parent
    script_path = project_root / "batch_ai_extract.py"
    
    if not script_path.exists():
        print(f"エラー: {script_path} が見つかりません")
        return
    
    # ビルド用の一時フォルダ
    build_dir = project_root / "build_batch"
    dist_dir = build_dir / "dist"
    
    # 既存のビルドフォルダを削除
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    print("=== batch_ai_extract.py PyInstallerビルド開始 ===")
    print(f"対象スクリプト: {script_path}")
    print(f"ビルドフォルダ: {build_dir}")
    
    # PyInstallerコマンド
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "BatchAIExtract",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir / "work"),
        "--specpath", str(build_dir),
        "--console",
        "--clean",
        str(script_path)
    ]
    
    print(f"実行コマンド: {' '.join(cmd)}")
    
    try:
        # PyInstallerを実行
        result = subprocess.run(cmd, cwd=str(project_root), check=True)
        
        exe_path = dist_dir / "BatchAIExtract.exe"
        if exe_path.exists():
            print(f"✓ ビルド成功: {exe_path}")
            print(f"ファイルサイズ: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
        else:
            print("❌ ビルド失敗: exeファイルが見つかりません")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstallerエラー: {e}")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
    
    print("=== ビルド終了 ===")

if __name__ == "__main__":
    main()