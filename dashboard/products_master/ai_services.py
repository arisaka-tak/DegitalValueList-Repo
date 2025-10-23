"""
AI価格抽出関連のサービス
"""
import unicodedata
import re
try:
    from fuzzywuzzy import fuzz
except ImportError:
    # fuzzywuzzyが利用できない場合のフォールバック
    class MockFuzz:
        @staticmethod
        def ratio(a, b):
            return 80 if a.lower() in b.lower() or b.lower() in a.lower() else 50
        
        @staticmethod
        def partial_ratio(a, b):
            return MockFuzz.ratio(a, b)
        
        @staticmethod
        def token_sort_ratio(a, b):
            return MockFuzz.ratio(a, b)
        
        @staticmethod
        def token_set_ratio(a, b):
            return MockFuzz.ratio(a, b)
    
    fuzz = MockFuzz()

from .models import Product


def normalize_text(text):
    """テキストを正規化（全角→半角、カタカナ統一等）"""
    if not text:
        return ""
    
    # 1. 全角英数字→半角英数字
    text = unicodedata.normalize('NFKC', text)
    
    # 2. ひらがな→カタカナ
    text = ''.join([chr(ord(c) + 0x60) if 'ひ' <= c <= 'ゖ' else c for c in text])
    
    # 3. 空白文字統一・除去
    text = re.sub(r'\s+', '', text)
    
    # 4. 大文字小文字統一
    text = text.upper()
    
    return text


def find_similar_products(extracted_data, threshold=70):
    """
    抽出されたデータから類似商品を検索
    
    Args:
        extracted_data (dict): AI抽出データ
        threshold (int): 類似度閾値
    
    Returns:
        list: 候補商品リスト
    """
    # 抽出データから検索キーワード生成
    search_keywords = {
        'product_name': extracted_data.get('product_name', ''),
        'model_number': extracted_data.get('model_number', ''),
        'manufacturer': extracted_data.get('manufacturer', ''),
        'specification': extracted_data.get('specification', ''),
    }
    
    # メーカー名での事前絞り込み
    if search_keywords['manufacturer'] and search_keywords['manufacturer'].strip():
        normalized_manufacturer = normalize_text(search_keywords['manufacturer'])
        products = Product.objects.filter(
            manufacturer__icontains=normalized_manufacturer[:10]  # 部分一致で絞り込み
        )
    else:
        products = Product.objects.all()
    
    candidates = []
    
    for product in products:
        # 商品マスタ側の検索対象テキスト（全パターン）
        search_targets = [
            # 基本パターン
            product.product_name or '',
            product.model_number or '',
            product.specification or '',
            
            # 組み合わせパターン
            f"{product.product_name or ''} {product.model_number or ''}".strip(),
            f"{product.product_name or ''} {product.specification or ''}".strip(),
            f"{product.model_number or ''} {product.specification or ''}".strip(),
            f"{product.manufacturer or ''} {product.product_name or ''}".strip(),
            
            # 全部入りパターン
            f"{product.manufacturer or ''} {product.product_name or ''} {product.model_number or ''} {product.specification or ''}".strip(),
        ]
        
        max_score = 0
        best_match_field = ''
        field_names = ['商品名', '型式', '規格', '商品名+型式', '商品名+規格', '型式+規格', 'メーカー+商品名', '全項目']
        
        # 抽出データの各フィールドと照合
        for keyword_name, keyword_value in search_keywords.items():
            if not keyword_value or keyword_value.strip() == '':
                continue
                
            normalized_keyword = normalize_text(keyword_value)
            
            for i, target in enumerate(search_targets):
                if target and len(target.strip()) > 0:
                    normalized_target = normalize_text(target)
                    
                    # 複数の類似度計算
                    scores = [
                        fuzz.ratio(normalized_keyword, normalized_target),
                        fuzz.partial_ratio(normalized_keyword, normalized_target),
                        fuzz.token_sort_ratio(normalized_keyword, normalized_target),
                        fuzz.token_set_ratio(normalized_keyword, normalized_target),  # 順序無視
                    ]
                    
                    current_max = max(scores)
                    if current_max > max_score:
                        max_score = current_max
                        best_match_field = field_names[i]
        
        # メーカー一致ボーナス
        if (search_keywords['manufacturer'] and product.manufacturer and 
            normalize_text(search_keywords['manufacturer']) in normalize_text(product.manufacturer)):
            max_score += 10
        
        # 型式完全一致ボーナス  
        if (search_keywords['model_number'] and product.model_number and 
            normalize_text(search_keywords['model_number']) == normalize_text(product.model_number)):
            max_score += 15
        
        # 閾値以上の場合のみ候補に追加
        if max_score >= threshold:
            candidates.append({
                'product': {
                    'pk': product.pk,
                    'product_name': product.product_name,
                    'model_number': product.model_number,
                    'specification': product.specification,
                    'manufacturer': product.manufacturer,
                    'product_number': product.product_number,
                },
                'score': min(max_score, 100),  # 100%上限
                'matched_field': best_match_field,
                'display_info': f"{product.product_name} | {product.model_number or '-'} | {product.specification or '-'}",
                'manufacturer': product.manufacturer or '-',
                'product_number': product.product_number,
            })
    
    # スコア順でソート
    return sorted(candidates, key=lambda x: x['score'], reverse=True)[:10]


def process_extraction_results(json_data):
    """
    AI抽出結果を処理して商品照合を実行
    
    Args:
        json_data (dict): AI抽出JSON
    
    Returns:
        dict: 処理結果
    """
    if 'products' not in json_data:
        return {
            'status': 'error',
            'message': 'JSONに"products"キーが見つかりません'
        }
    
    results = []
    
    for i, product_data in enumerate(json_data['products']):
        # 必須フィールドチェック
        if not product_data.get('product_name'):
            results.append({
                'index': i,
                'status': 'error',
                'message': '商品名が見つかりません',
                'extracted_data': product_data,
                'candidates': []
            })
            continue
        
        # 商品照合実行
        candidates = find_similar_products(product_data)
        
        results.append({
            'index': i,
            'status': 'success' if candidates else 'no_match',
            'message': f'{len(candidates)}件の候補が見つかりました' if candidates else '該当する商品はありません',
            'extracted_data': product_data,
            'candidates': candidates
        })
    
    return {
        'status': 'success',
        'results': results,
        'total_products': len(json_data['products'])
    }