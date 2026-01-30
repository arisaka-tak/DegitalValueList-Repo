"""
AI価格抽出関連のサービス
"""
import unicodedata
import re
import logging
from datetime import datetime

from .models import Product

# ログ設定
logger = logging.getLogger(__name__)


def get_bigrams(text):
    """文字列を2-gramに分割（日本語と英数字の境界で分離）"""
    if not text:
        return set()
    
    # 文字種別に分割（ひらがな、カタカナ、漢字、英字、数字を個別に扱う）
    segments = re.findall(r'[\u3040-\u309F]+|[\u30A0-\u30FF]+|[\u4E00-\u9FAF]+|[A-Za-z]+|[0-9]+', text.replace(' ', ''))
    
    bigrams = set()
    for segment in segments:
        if len(segment) >= 2:
            # セグメント内で2-gram作成のみ
            bigrams.update([segment[i:i+2] for i in range(len(segment) - 1)])
        elif len(segment) == 1:
            # 1文字の場合はそのまま追加
            bigrams.add(segment)
    
    return bigrams

def calculate_field_score(ai_text, master_text, max_points):
    """
    フィールド別スコア計算（2-gramマッチ率ベース）
    
    Args:
        ai_text (str): AI抽出テキスト
        master_text (str): マスターテキスト
        max_points (int): 最大点数
    
    Returns:
        int: スコア (0-max_points)
    """
    if not ai_text or not master_text:
        return 0
    
    ai_bigrams = get_bigrams(normalize_text(ai_text))
    master_bigrams = get_bigrams(normalize_text(master_text))
    
    if not ai_bigrams:
        return 0
    
    # AI側の2-gramのうち何個がマスターに含まれるか
    matched_count = len(ai_bigrams & master_bigrams)
    match_ratio = matched_count / len(ai_bigrams)
    
    # 70%以上のマッチでスコア付与
    if match_ratio >= 0.7:
        return int(max_points * match_ratio)
    
    return 0



def normalize_text(text):
    """テキストを正規化（全角→半角、ひらがな→カタカナ、記号統一、空白除去等）"""
    if not text:
        return ""
    
    # 1. 全角英数字→半角英数字
    text = unicodedata.normalize('NFKC', text)
    
    # 2. ひらがな→カタカナ（漢字はそのまま）
    text = ''.join([chr(ord(c) + 0x60) if 'ひ' <= c <= 'ゖ' else c for c in text])
    
    # 3. 記号の統一（検索時は長音記号を保持）
    # text = re.sub(r'[−–—ー－ｰ]', ' ', text)  # 各種ハイフン→半角スペース（検索時は無効化）
    text = re.sub(r'[・·•]', ' ', text)  # 中点→半角スペース
    text = re.sub(r'[（）]', ' ', text)  # 全角括弧→半角スペース
    text = re.sub(r'[\(\)]', ' ', text)  # 半角括弧→半角スペース
    
    # 4. 空白文字統一（除去しない）
    text = re.sub(r'\s+', ' ', text)  # 複数の空白を1つに統一
    
    # 5. 大文字小文字統一
    text = text.upper()
    
    return text


def find_similar_products(extracted_data, threshold=70, debug=False):
    """
    抽出されたデータから類似商品を検索
    
    Args:
        extracted_data (dict): AI抽出データ
        threshold (int): 類似度閾値
        debug (bool): デバッグ情報出力
    
    Returns:
        list: 候補商品リスト
    """
    # AI抽出データを取得
    ai_product_name = extracted_data.get('product_name', '')
    ai_specification = extracted_data.get('specification', '')
    ai_model_number = extracted_data.get('model_number', '')
    
    # AI側のキーワードリストBを作成
    ai_product_bigrams = get_bigrams(normalize_text(ai_product_name))
    ai_spec_bigrams = get_bigrams(normalize_text(ai_specification))
    ai_model_bigrams = get_bigrams(normalize_text(ai_model_number))
    ai_keyword_list = ai_product_bigrams | ai_spec_bigrams | ai_model_bigrams
    
    # NFJ 310の場合のみデバッグ出力
    is_nfj310_debug = debug and 'NFJ 310' in ai_product_name
    
    # AI側の正規化処理をデバッグ出力
    if is_nfj310_debug:
        logger.debug(f"AI側データ正規化")
        logger.debug(f"AI生データ: 商品名='{ai_product_name}', 型式='{ai_model_number}', 規格='{ai_specification}'")
        logger.debug(f"AI正規化後: 商品名='{normalize_text(ai_product_name)}', 型式='{normalize_text(ai_model_number)}', 規格='{normalize_text(ai_specification)}'")
        logger.debug(f"AIキーワード: {list(ai_keyword_list)}")
    
    # 空のキーワードリストの場合は早期リターン
    if not ai_keyword_list:
        if is_nfj310_debug:
            logger.debug("AIキーワードリストが空のためスキップ")
        return []
    
    # 全商品を対象とした照合（関連データも一括取得）
    products = Product.objects.select_related('manufacturer', 'livestock_type', 'category').all()
    if is_nfj310_debug:
        logger.debug(f"全商品対象: {products.count()}件")
    
    candidates = []
    debug_info = []
    processed_count = 0
    first_product_checked = False
    
    # 早期終了を無効化して安定した結果を保証
    max_candidates = 50  # より多くの候補を確認
    high_score_threshold = 100  # 早期終了を実質無効化
    
    for product in products:
        # マスター側のキーワードリストAを作成（常に動的生成）
        master_product_bigrams = get_bigrams(normalize_text(product.product_name or ''))
        master_spec_bigrams = get_bigrams(normalize_text(product.specification or ''))
        master_model_bigrams = get_bigrams(normalize_text(product.model_number or ''))
        master_keyword_list = master_product_bigrams | master_spec_bigrams | master_model_bigrams
        
        # 空のキーワードリストの場合はスキップ
        if not ai_keyword_list or not master_keyword_list:
            continue
        
        # キーワードリストの一致率を計算
        matched_keywords = len(ai_keyword_list & master_keyword_list)
        total_ai_keywords = len(ai_keyword_list)
        match_ratio = matched_keywords / total_ai_keywords if total_ai_keywords > 0 else 0
        
        # 基本加点: AI→マスタ一致率 * 80
        base_score = int(match_ratio * 80)
        
        # 余剰減点: マスタの余剰部分による減点
        excess_ratio = (len(master_keyword_list) - matched_keywords) / len(master_keyword_list) if len(master_keyword_list) > 0 else 0
        penalty = int(excess_ratio * 20)
        
        # ボーナススコアを計算
        bonus_score = 0
        best_match_field = '2-gramキーワードリスト'
        
        # 商品名由来キーワードの一致率ボーナス（AI商品名 vs マスタキーワードカラム）
        product_bonus_ratio = 0
        if ai_product_bigrams and master_keyword_list:
            product_matched = len(ai_product_bigrams & master_keyword_list)
            product_bonus_ratio = product_matched / len(ai_product_bigrams)
            if product_bonus_ratio >= 0.7:  # 70%以上
                bonus_score += 15
        
        # 型式由来キーワードの一致率ボーナス（AI型式 vs マスタキーワードカラム）
        model_bonus_ratio = 0
        if ai_model_bigrams and master_keyword_list:
            model_matched = len(ai_model_bigrams & master_keyword_list)
            model_bonus_ratio = model_matched / len(ai_model_bigrams)
            if model_bonus_ratio >= 0.7:  # 70%以上
                bonus_score += 15
        
        # マスタ型式網羅チェック（AI抽出の品名・型式・規格のいずれかにマスタ型式が含まれる）
        model_coverage_matched = False
        master_model_clean = ''
        if product.model_number:
            master_model_stripped = product.model_number.strip()
            # 数字オンリーの場合は6桁以上、それ以外は4桁以上
            min_length = 6 if master_model_stripped.isdigit() else 4
            
            if len(master_model_stripped) >= min_length:
                master_model_normalized = normalize_text(product.model_number)
                ai_all_fields = f"{ai_product_name} {ai_model_number} {ai_specification}"
                ai_all_normalized = normalize_text(ai_all_fields)
                
                # 記号を除去して3文字以上の型式のみチェック
                def clean_model_text(text):
                    """記号を除去してアルファベット・数字・漢字・ひらがな・カタカナのみにする"""
                    return re.sub(r'[^A-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '', text) if text else ''
                
                master_model_clean = clean_model_text(master_model_normalized)
                ai_all_clean = clean_model_text(ai_all_normalized)
                
                if master_model_clean and len(master_model_clean) >= min_length:
                    if master_model_clean in ai_all_clean:
                        model_coverage_matched = True
                        best_match_field = 'マスタ型式網羅(記号除去)'
                
            # デバッグ出力（商品739とNFJ310と220の問題を調査）
            if is_nfj310_debug and (product.pk == 739 or product.model_number == '220' or 'NFJ310' in (product.model_number or '')):
                clean_match = master_model_clean in ai_all_clean if master_model_clean else False
                logger.debug(f"商品{product.pk}[型式:{product.model_number}]: 正規化='{master_model_normalized}' 記号除去='{master_model_clean}' マッチ={clean_match} スコア={base_score}")
        
        # メーカー名一致ボーナス（2-gram照合70%以上）
        manufacturer_bonus = 0
        ai_manufacturer = extracted_data.get('manufacturer', '')
        if ai_manufacturer and product.manufacturer:
            ai_manufacturer_bigrams = get_bigrams(normalize_text(ai_manufacturer))
            master_manufacturer_bigrams = get_bigrams(normalize_text(str(product.manufacturer)))
            if ai_manufacturer_bigrams:
                manufacturer_matched = len(ai_manufacturer_bigrams & master_manufacturer_bigrams)
                manufacturer_match_ratio = manufacturer_matched / len(ai_manufacturer_bigrams)
                if manufacturer_match_ratio >= 0.7:  # 70%以上
                    manufacturer_bonus = 5
                    bonus_score += manufacturer_bonus
        
        # 新価格と仕切価格の範囲チェックボーナス（±10%の範囲で+10点）
        price_range_bonus = 0
        ai_new_price = extracted_data.get('new_price')
        if ai_new_price and product.price_histories.exists():
            try:
                # AI側の新価格を数値に変換
                ai_price_num = float(str(ai_new_price).replace(',', '').strip())
                
                # マスタ側の処理日時点の仕切価格を取得
                today = datetime.now().strftime('%Y/%m')
                latest_price_history = product.price_histories.filter(
                    is_active=True,
                    effective_year_month__lte=today
                ).order_by('-effective_year_month').first()
                if latest_price_history and latest_price_history.wholesale_price:
                    master_price_str = str(latest_price_history.wholesale_price).strip()
                    # 数値のみの場合に処理
                    if master_price_str.replace(',', '').replace('.', '').isdigit():
                        master_price_num = float(master_price_str.replace(',', ''))
                        
                        # ±10%の範囲チェック
                        price_diff_ratio = abs(ai_price_num - master_price_num) / master_price_num
                        if price_diff_ratio <= 0.1:  # 10%以内
                            price_range_bonus = 10
                            bonus_score += price_range_bonus
            except (ValueError, TypeError, ZeroDivisionError):
                # 数値変換エラーや0除算エラーは無視
                pass
        
        # 最終スコア = 基本加点 - 余剰減点 + ボーナス
        max_score = base_score - penalty + bonus_score
        
        # マスタ型式網羅時は最低70点を保証
        if model_coverage_matched:
            max_score = max(max_score, 70)
            if is_nfj310_debug:
                logger.debug(f"型式マッチ: {product.product_name} | 型式:{product.model_number} | 記号除去後:'{master_model_clean}' | スコア:{max_score}")
        
        # デバッグ出力を無効化
        # if not first_product_checked and 'エコクーラー' in product.product_name:
        #     first_product_checked = True
        
        # デバッグ情報収集（商品739、スコア30以上またはNFJ関連のみ）
        if is_nfj310_debug and (product.pk == 739 or max_score >= 30 or 'NFJ' in (product.model_number or '') or product.model_number == '220'):
            debug_info.append({
                'product_name': product.product_name,
                'model_number': product.model_number,
                'score': max_score,
                'base_score': base_score,
                'penalty': penalty,
                'bonus_score': bonus_score,
                'match_ratio': f"{match_ratio:.2%}",
                'excess_ratio': f"{excess_ratio:.2%}",
                'matched_keywords': f"{matched_keywords}/{total_ai_keywords}",
                'product_bonus_ratio': product_bonus_ratio,
                'model_bonus_ratio': model_bonus_ratio,
                'model_coverage_matched': model_coverage_matched,
                'manufacturer_bonus': manufacturer_bonus,
                'master_keywords': list(master_keyword_list),
                'best_match_field': best_match_field,
                'threshold': threshold
            })
        
        # 型式網羅マッチの場合は閾値を下げる
        effective_threshold = 30 if model_coverage_matched else threshold
        
        # 商品739とNFJ310と220のデバッグ情報を追加出力
        if is_nfj310_debug and (product.pk == 739 or product.model_number == '220' or 'NFJ310' in (product.model_number or '')):
            print(f"商品{product.pk}[型式:{product.model_number}] 最終スコア: {max_score} (閾値:{effective_threshold}) 型式網羅:{model_coverage_matched} 記号除去後:'{master_model_clean}' マッチキーワード:{matched_keywords}/{total_ai_keywords}")
        
        # 閾値以上の場合のみ候補に追加
        if max_score >= effective_threshold and max_score > 0:
            candidates.append({
                'product': {
                    'pk': product.pk,
                    'product_name': product.product_name,
                    'model_number': product.model_number,
                    'specification': product.specification,
                    'manufacturer': product.manufacturer,
                },
                'score': min(max_score, 98),  # 98%上限
                'matched_field': best_match_field,
                'display_info': f"{product.product_name} | {product.model_number or '-'} | {product.specification or '-'}",
                'manufacturer': str(product.manufacturer) if product.manufacturer else '-',
            })
            
            # 早期終了を無効化（安定性のため）
            # if max_score >= high_score_threshold or len(candidates) >= max_candidates:
            #     if debug:
            #         print(f"早期終了: スコア{max_score}点 または 候補数{len(candidates)}件で打ち切り")
            #     break
        
        processed_count += 1
    
    # デバッグ情報出力
    if is_nfj310_debug:
        print(f"\n=== 照合結果: {extracted_data.get('product_name', 'Unknown')} ===")
        print(f"AI入力: 商品名='{ai_product_name}', 型式='{ai_model_number}', 規格='{ai_specification}', メーカー='{extracted_data.get('manufacturer', '')}'")
        print(f"AI正規化後キーワード: {list(ai_keyword_list)}")
        print(f"照合対象商品数: {len(debug_info)}件")
        print(f"\n--- 上位5件の照合詳細 ---")
        for info in sorted(debug_info, key=lambda x: x['score'], reverse=True)[:5]:
            print(f"\n商品: {info['product_name']}")
            print(f"  最終スコア: {info['score']}点 (閾値:{threshold}点)")
            print(f"  内訳: ベース{info['base_score']} - 減点{info['penalty']} + ボーナス{info['bonus_score']} = {info['score']}")
            print(f"  基本一致率: {info['match_ratio']} ({info['matched_keywords']})")
            print(f"  商品名ボーナス: {info.get('product_bonus_ratio', 0):.1%} → {'+15点' if info.get('product_bonus_ratio', 0) >= 0.7 else '0点'}")
            print(f"  型式ボーナス: {info.get('model_bonus_ratio', 0):.1%} → {'+15点' if info.get('model_bonus_ratio', 0) >= 0.7 else '0点'}")
            print(f"  メーカーボーナス: → {'+5点' if info.get('manufacturer_bonus', 0) > 0 else '0点'}")
            print(f"  マスターキーワード: {info['master_keywords'][:15]}{'...' if len(info['master_keywords']) > 15 else ''}")
        print(f"\n結果: {len(candidates)}件が閾値{threshold}点以上でマッチ")
    
    # スコア順でソートして上位10件を返す
    sorted_candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
    return sorted_candidates[:10]  # 上位10件に制限


def process_extraction_results(json_data):
    """
    AI抽出結果を処理して商品照合を実行
    
    Args:
        json_data (dict): AI抽出JSON
    
    Returns:
        dict: 処理結果
    """
    if 'products' not in json_data:
        logger.debug(f"Processing product {i}: {product_data}")
        return {
            'status': 'error',
            'message': 'JSONに"products"キーが見つかりません'
        }
    
    results = []
    
    for i, product_data in enumerate(json_data['products']):
        # 必須フィールドチェック（商品名、型式、規格のいずれかが必要）
        if not any([product_data.get('product_name'), product_data.get('model_number'), product_data.get('specification')]):
            results.append({
                'index': i,
                'status': 'error',
                'message': '商品名、型式、規格のいずれかが必要です',
                'extracted_data': product_data,
                'candidates': []
            })
            continue
        
        # 商品照合実行
        candidates = find_similar_products(product_data, threshold=50, debug=True)
        
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