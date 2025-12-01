"""
商品マスタ関連のサービス機能
"""
import json
from .models import Product
from .ai_services import get_bigrams, normalize_text


def update_product_keywords(product):
    """
    商品マスタの2-gramキーワードを再生成
    
    Args:
        product (Product): 商品オブジェクト
    """
    # 商品名+規格+型式の2-gramを生成
    keywords = set()
    
    for field_value in [product.product_name, product.specification, product.model_number]:
        if field_value:
            field_bigrams = get_bigrams(normalize_text(field_value))
            keywords.update(field_bigrams)
    
    # JSON文字列として保存
    product.bigram_keywords = json.dumps(list(keywords), ensure_ascii=False)
    product.save(update_fields=['bigram_keywords'])


def regenerate_all_product_keywords():
    """
    全商品マスタの2-gramキーワードを一括再生成（バッチ処理）
    
    Returns:
        dict: 処理結果
    """
    products = Product.objects.all()
    total_count = products.count()
    processed_count = 0
    
    print(f"全{total_count}件の商品マスタのキーワード再生成を開始...")
    
    for product in products:
        try:
            update_product_keywords(product)
            processed_count += 1
            
            # 100件ごとに進捗表示
            if processed_count % 100 == 0:
                print(f"進捗: {processed_count}/{total_count} ({processed_count/total_count*100:.1f}%)")
                
        except Exception as e:
            print(f"エラー: 商品ID {product.pk} - {str(e)}")
    
    print(f"キーワード再生成完了: {processed_count}/{total_count}件")
    
    return {
        'total_count': total_count,
        'processed_count': processed_count,
        'success_rate': processed_count / total_count * 100 if total_count > 0 else 0
    }