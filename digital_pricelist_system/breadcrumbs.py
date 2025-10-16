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
        'product_list': '/products/products/',
        'approval_list': '/products/approvals/',
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
            {'title': '商品一覧', 'url': URLS['product_list']},
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
    }
    
    return breadcrumbs_map.get(page_type, [])