#!/usr/bin/env python
"""
batch_ai_extract.spec を使用してPyInstallerビルドするスクリプト
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    # プロジェクトルート
    project_root = Path(__file__).parent.parent
    spec_path = Path(__file__).parent / "batch_ai_extract.spec"
    
    if not spec_path.exists():
        print(f"エラー: {spec_path} が見つかりません")
        return
    
    # ビルド用の一時フォルダ
    build_dir = project_root / "build_batch"
    dist_dir = build_dir / "dist"
    
    # 既存のビルドフォルダを削除
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    print("=== batch_ai_extract.py PyInstallerビルド開始 (specファイル使用) ===")
    print(f"specファイル: {spec_path}")
    print(f"ビルドフォルダ: {build_dir}")
    
    # PyInstallerコマンド（specファイル使用）
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir / "work"),
        "--console",  # コンソール表示を明示的に指定
        "--clean",
        str(spec_path)
    ]
    
    print(f"実行コマンド: {' '.join(cmd)}")
    
    try:
        # PyInstallerを実行
        result = subprocess.run(cmd, cwd=str(project_root), check=True)
        
        exe_path = dist_dir / "BatchAIExtract.exe"
        if exe_path.exists():
            print(f"✓ ビルド成功: {exe_path}")
            print(f"ファイルサイズ: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
            
            # 最終的な配置先にコピー
            final_path = project_root / "BatchAIExtract.exe"
            shutil.copy2(exe_path, final_path)
            print(f"✓ 最終配置: {final_path}")
            
        else:
            print("❌ ビルド失敗: exeファイルが見つかりません")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstallerエラー: {e}")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
    
    print("=== ビルド終了 ===")

if __name__ == "__main__":
    main()