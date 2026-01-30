#!/usr/bin/env python3
"""
バージョンチェッカー 軽量ビルドスクリプト
"""

import subprocess
import sys
from pathlib import Path

def build_version_checker():
    """軽量バージョンチェッカーをビルド"""
    
    # プロジェクトルート
    project_root = Path(__file__).parent.parent
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--console',
        '--name=デジタル価格表',
        
        # 軽量化オプション
        '--noupx',
        '--optimize=2',  # Pythonバイトコード最適化
        
        # 不要モジュールを除外（PyInstaller必須モジュールは除外しない）
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=PIL',
        '--exclude-module=cv2',
        '--exclude-module=scipy',
        '--exclude-module=django',
        '--exclude-module=flask',
        '--exclude-module=requests',
        '--exclude-module=urllib3',
        '--exclude-module=certifi',
        '--exclude-module=charset_normalizer',
        '--exclude-module=idna',
        '--exclude-module=setuptools',
        '--exclude-module=pkg_resources',
        '--exclude-module=email',
        '--exclude-module=xml',
        '--exclude-module=html',
        '--exclude-module=http',
        '--exclude-module=sqlite3',
        '--exclude-module=ssl',
        '--exclude-module=unittest',
        '--exclude-module=doctest',
        '--exclude-module=pdb',
        '--exclude-module=trace',
        '--exclude-module=profile',
        '--exclude-module=cProfile',
        '--exclude-module=pstats',
        '--exclude-module=timeit',
        
        # 出力ディレクトリ
        '--distpath=dist',
        '--workpath=build_checker',
        '--specpath=.',
        
        # エントリーポイント
        str(project_root / 'version_checker.py')
    ]
    
    print("軽量バージョンチェッカーのビルドを開始...")
    print(f"コマンド: {' '.join(cmd[:10])}... (省略)")
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print("✅ ビルド完了")
        print(f"📁 出力先: {project_root / 'dist'}")
        
        # ファイルサイズを表示
        exe_path = project_root / 'dist' / 'デジタル価格表.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📊 ファイルサイズ: {size_mb:.1f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ビルドエラー: {e}")
        return False
    
    return True

if __name__ == "__main__":
    build_version_checker()