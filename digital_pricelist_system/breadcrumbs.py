"""
パンくずリスト管理ユーティリティ
"""

def get_breadcrumbs(page_type, **kwargs):
    """
    ページタイプに応じたパンくずリストを返す
    
    Args:
        page_type (str): ページタイプ
        **kwargs: 動的な値（商品名など）
    
    Returns:
        list: パンくずリストの辞書配列
    """
    
    # ベースURL定義
    URLS = {
        'product_list': '/products/',
        'approval_list': '/products/approvals/',
        'integrated_pricelist': '/products/integrated-pricelist/',
    }
    
    breadcrumbs_map = {
        # 商品関連
        'product_list': [
            {'title': '商品一覧', 'url': None}
        ],
        'product_detail': [
            {'title': '商品一覧', 'url': URLS['product_list']},
            {'title': kwargs.get('product_name', '商品詳細'), 'url': None}
        ],
        'product_new': [
            {'title': kwargs.get('from_page_title', '商品一覧'), 'url': kwargs.get('from_page_url', URLS['product_list'])},
            {'title': '新規作成', 'url': None}
        ],
        'product_edit': [
            {'title': '商品一覧', 'url': URLS['product_list']},
            {'title': kwargs.get('product_name', '商品'), 'url': kwargs.get('product_url')},
            {'title': '編集', 'url': None}
        ],
        'product_delete': [
            {'title': '商品一覧', 'url': URLS['product_list']},
            {'title': kwargs.get('product_name', '商品'), 'url': kwargs.get('product_url')},
            {'title': '削除申請', 'url': None}
        ],
        
        # 承認関連
        'approval_list': [
            {'title': '承認待ち一覧', 'url': None}
        ],
        'approval_detail': [
            {'title': '承認待ち一覧', 'url': URLS['approval_list']},
            {'title': kwargs.get('product_name', '申請詳細'), 'url': None}
        ],
        
        # デジタル価格表
        'integrated_pricelist': [
            {'title': 'デジタル価格表', 'url': None}
        ],
        
        # AI価格抽出
        'ai_extract': [
            {'title': kwargs.get('from_page_title', '商品一覧'), 'url': kwargs.get('from_page_url', URLS['product_list'])},
            {'title': 'AI価格抽出', 'url': None}
        ],
        'ai_extract_results': [
            {'title': '商品一覧', 'url': URLS['product_list']},
            {'title': 'AI価格抽出', 'url': '/products/ai-extract/'},
            {'title': '照合結果', 'url': None}
        ],
        'ai_extract_history': [
            {'title': '商品一覧', 'url': URLS['product_list']},
            {'title': 'AI価格抽出', 'url': '/products/ai-extract/'},
            {'title': '抽出履歴', 'url': None}
        ],
        'ai_extract_history_detail': [
            {'title': '商品一覧', 'url': URLS['product_list']},
            {'title': 'AI価格抽出', 'url': '/products/ai-extract/'},
            {'title': '抽出履歴', 'url': '/products/ai-extract/history/'},
            {'title': kwargs.get('transaction_name', '照合結果'), 'url': None}
        ],
        'upload_approval_pdf': [
            {'title': '決裁書アップロード', 'url': None}
        ],
        
        # マスタメンテナンス
        'livestock_type_list': [
            {'title': '畜種マスタ', 'url': None}
        ],
        'livestock_type_create': [
            {'title': '畜種マスタ', 'url': '/products/masters/livestock-types/'},
            {'title': '新規作成', 'url': None}
        ],
        'livestock_type_edit': [
            {'title': '畜種マスタ', 'url': '/products/masters/livestock-types/'},
            {'title': kwargs.get('livestock_type_name', '編集'), 'url': None}
        ],
        'category_list': [
            {'title': '分類マスタ', 'url': None}
        ],
        'category_create': [
            {'title': '分類マスタ', 'url': '/products/masters/categories/'},
            {'title': '新規作成', 'url': None}
        ],
        'category_edit': [
            {'title': '分類マスタ', 'url': '/products/masters/categories/'},
            {'title': kwargs.get('category_name', '編集'), 'url': None}
        ],
        'manufacturer_list': [
            {'title': 'メーカーマスタ', 'url': None}
        ],
        'manufacturer_create': [
            {'title': 'メーカーマスタ', 'url': '/products/masters/manufacturers/'},
            {'title': '新規作成', 'url': None}
        ],
        'manufacturer_edit': [
            {'title': 'メーカーマスタ', 'url': '/products/masters/manufacturers/'},
            {'title': kwargs.get('manufacturer_name', '編集'), 'url': None}
        ],
    }
    
    return breadcrumbs_map.get(page_type, [])