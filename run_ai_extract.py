#!/usr/bin/env python
"""
AI抽出処理単体実行スクリプト
"""
import os
import sys

# プロジェクトルートを追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
import django
django.setup()

# AI処理モジュールをインポート
from dashboard.products_master.pdf_processing.process_ai_only import process_tables_with_ai

if __name__ == "__main__":
    # 入力ファイル
    input_pkl = r"C:\Project\ZCS_DegitalValueList\di_result.pkl"
    
    # 出力ファイル
    output_json = r"C:\Project\ZCS_DegitalValueList\ai_extract_result.json"
    
    print(f"入力ファイル: {input_pkl}")
    print(f"出力ファイル: {output_json}")
    
    # AI抽出処理実行
    process_tables_with_ai(input_pkl, output_json)