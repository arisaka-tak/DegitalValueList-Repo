#!/usr/bin/env python
"""
テンプレートファイルの使用状況を確認するスクリプト
"""
import os
import subprocess
from pathlib import Path

def check_template_usage(template_name):
    """テンプレートファイルの使用状況をチェック"""
    project_root = Path(__file__).parent
    
    print(f"=== Checking: {template_name} ===")
    
    # プロジェクトのソースコードディレクトリのみを対象
    search_dirs = [
        "dashboard",
        "templates"
    ]
    
    found_references = []
    
    for search_dir in search_dirs:
        search_path = project_root / search_dir
        if not search_path.exists():
            continue
            
        try:
            # Windowsのfindstrコマンドを使用
            result = subprocess.run([
                'findstr', '/r', '/s', template_name, 
                str(search_path / "*.py"), 
                str(search_path / "*.html")
            ], capture_output=True, text=True, cwd=str(project_root))
            
            if result.stdout:
                found_references.extend(result.stdout.strip().split('\n'))
                
        except Exception as e:
            print(f"Error searching in {search_dir}: {e}")
    
    if found_references:
        print("✅ USED - Found references:")
        for ref in found_references:
            if ref.strip():
                print(f"  {ref}")
    else:
        print("❌ UNUSED - No references found")
    
    print()
    return len(found_references) > 0

def main():
    """メイン処理"""
    project_root = Path(__file__).parent
    templates_dir = project_root / "templates" / "products_master"
    
    if not templates_dir.exists():
        print("Templates directory not found!")
        return
    
    # del_プレフィックス以外のHTMLファイルを取得
    template_files = [
        f.stem for f in templates_dir.glob("*.html") 
        if not f.name.startswith("del_")
    ]
    
    print("Template Usage Check Report")
    print("=" * 50)
    
    used_count = 0
    unused_files = []
    
    for template_name in sorted(template_files):
        is_used = check_template_usage(template_name)
        if is_used:
            used_count += 1
        else:
            unused_files.append(template_name)
    
    print("=" * 50)
    print(f"Summary: {used_count}/{len(template_files)} templates are used")
    
    if unused_files:
        print(f"\nUnused templates ({len(unused_files)}):")
        for template in unused_files:
            print(f"  - {template}.html")
        print("\nThese files can be renamed with 'del_' prefix for deletion.")

if __name__ == "__main__":
    main()