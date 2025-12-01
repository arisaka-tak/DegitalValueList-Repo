#!/usr/bin/env python
"""
配布用パッケージビルドスクリプト
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    """配布パッケージをビルド"""
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    
    print("=== デジタル価格表システム 配布パッケージビルド ===")
    
    # 1. 既存のビルドファイルを削除
    print("1. 既存のビルドファイルを削除中...")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    # 2. PyInstallerでexeを作成
    print("2. PyInstallerでexeファイルを作成中...")
    try:
        subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "build_config.spec"
        ], check=True, cwd=project_root)
    except subprocess.CalledProcessError as e:
        print(f"PyInstallerでエラーが発生しました: {e}")
        return False
    
    # 3. 配布用ディレクトリを作成
    print("3. 配布用ディレクトリを準備中...")
    release_dir = project_root / "release"
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()
    
    # 4. 必要なファイルをコピー
    print("4. 必要なファイルをコピー中...")
    
    # exeファイル
    exe_file = dist_dir / "DigitalPriceList.exe"
    if exe_file.exists():
        shutil.copy2(exe_file, release_dir / "DigitalPriceList.exe")
    else:
        print("エラー: exeファイルが見つかりません")
        return False
    
    # 初期データベース（空のデータベースを作成）
    print("5. 初期データベースを作成中...")
    try:
        # 一時的にDjangoを使ってマイグレーション実行
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
        
        # 空のデータベースファイルを作成
        temp_db = release_dir / "db.sqlite3"
        if not temp_db.exists():
            temp_db.touch()
        
        # マイグレーション実行
        subprocess.run([
            sys.executable, "manage.py", "migrate", "--settings=digital_pricelist_system.settings"
        ], cwd=project_root, check=True)
        
        # 作成されたデータベースをコピー
        if (project_root / "db.sqlite3").exists():
            shutil.copy2(project_root / "db.sqlite3", release_dir / "db.sqlite3")
        
    except Exception as e:
        print(f"データベース作成でエラー: {e}")
        # 空のファイルを作成
        (release_dir / "db.sqlite3").touch()
    
    # 6. READMEファイルを作成
    print("6. 配布用READMEを作成中...")
    readme_content = """# デジタル価格表システム

## 使用方法

1. DigitalPriceList.exe をダブルクリックして起動
2. 自動的にブラウザが開きます
3. システムを終了するには、コンソールウィンドウを閉じてください

## ファイル構成

- DigitalPriceList.exe : メインアプリケーション
- db.sqlite3 : データベースファイル
- README.txt : このファイル

## 注意事項

- db.sqlite3 ファイルを削除すると、全てのデータが失われます
- ポート8000が他のアプリケーションで使用されている場合は起動できません
- インターネット接続は不要です（ローカルで動作）

## トラブルシューティング

### 起動しない場合
1. ポート8000が使用されていないか確認
2. db.sqlite3 ファイルが存在するか確認
3. ウイルス対策ソフトがブロックしていないか確認

### データをバックアップしたい場合
db.sqlite3 ファイルをコピーして保存してください

## サポート

問題が発生した場合は、システム管理者にお問い合わせください。
"""
    
    with open(release_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"✅ 配布パッケージが完成しました: {release_dir}")
    print(f"📁 配布用ファイル:")
    for file in release_dir.iterdir():
        print(f"   - {file.name}")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 ビルド完了!")
    else:
        print("\n❌ ビルド失敗")
    input("Enterキーを押して終了...")