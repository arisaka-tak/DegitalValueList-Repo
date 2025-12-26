#!/usr/bin/env python3
"""
PyInstaller onefile 高速化ビルドスクリプト
"""

import subprocess
import sys
from pathlib import Path

def build_onefile_fast():
    """高速化されたonefileビルド"""
    
    # プロジェクトルート
    project_root = Path(__file__).parent.parent
    
    # 高速化オプション
    cmd = [
        'pyinstaller',
        '--onefile',
        '--noconsole',
        '--name=DigitalValueList',
        
        # 高速化オプション
        '--noupx',  # UPX圧縮を無効化（展開時間短縮）
        '--exclude-module=tkinter',  # 不要なモジュールを除外
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=PIL',
        '--exclude-module=cv2',
        '--exclude-module=scipy',
        
        # 必要なデータファイルのみ追加
        '--add-data=templates;templates',
        '--add-data=static;static',
        '--add-data=dashboard;dashboard',
        '--add-data=digital_pricelist_system;digital_pricelist_system',
        '--add-data=manage.py;.',
        
        # 隠れたインポート（最小限）
        '--hidden-import=django',
        '--hidden-import=dashboard.products_master',
        
        # 出力ディレクトリ
        '--distpath=deploy_fast',
        '--workpath=build_fast',
        '--specpath=.',
        
        # エントリーポイント
        str(project_root / 'Django_run.py')
    ]
    
    print("高速化onefileビルドを開始...")
    print(f"コマンド: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print("✅ ビルド完了")
        print(f"📁 出力先: {project_root / 'deploy_fast'}")
        
        # ファイルサイズを表示
        exe_path = project_root / 'deploy_fast' / 'DigitalPriceList_Fast.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📊 ファイルサイズ: {size_mb:.1f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ビルドエラー: {e}")
        return False
    
    return True

if __name__ == "__main__":
    build_onefile_fast()