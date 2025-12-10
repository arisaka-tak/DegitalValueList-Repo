#!/usr/bin/env python
"""
シンプルな正規化関数のテスト
"""
import unicodedata

def normalize_simple(text):
    """全角・半角英数字のみ正規化（長音記号は変換しない）"""
    if not text:
        return ""
    
    # 全角英数字→半角英数字のみ
    text = unicodedata.normalize('NFKC', text)
    
    # 大文字小文字統一
    text = text.upper()
    
    return text

# テスト
test_cases = [
    ("ファーム", "ファームノート"),
    ("Ａ", "A"),
    ("１２３", "123"),
    ("ＡＢＣ", "ABC"),
]

for search, target in test_cases:
    norm_search = normalize_simple(search)
    norm_target = normalize_simple(target)
    match = norm_search in norm_target
    
    print(f"検索: '{search}' → '{norm_search}'")
    print(f"対象: '{target}' → '{norm_target}'")
    print(f"マッチ: {match}")
    print()