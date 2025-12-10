#!/usr/bin/env python
"""
normalize_text関数のテスト
"""
import os
import sys
import django

# Django設定
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.ai_services import normalize_text

# テスト
search_term = "ファーム"
manufacturer_name = "ファームノート"

print(f"検索語: '{search_term}'")
print(f"正規化後: '{normalize_text(search_term)}'")
print()
print(f"メーカー名: '{manufacturer_name}'")
print(f"正規化後: '{normalize_text(manufacturer_name)}'")
print()

# icontains相当のテスト
normalized_search = normalize_text(search_term)
normalized_manufacturer = normalize_text(manufacturer_name)

print(f"'{normalized_search}' in '{normalized_manufacturer}': {normalized_search in normalized_manufacturer}")