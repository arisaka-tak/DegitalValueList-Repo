#!/usr/bin/env python
"""
AI抽出バッチ処理スクリプト
指定フォルダのPDFを自動処理してAI抽出結果をデータベースに保存
"""
import os
import sys
import tempfile
import shutil
import uuid
import configparser
import logging
import traceback
from datetime import datetime
from pathlib import Path

# プロジェクトルートを追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
import django
django.setup()

from dashboard.products_master.pdf_processing.extract_di_only import main as extract_di_main
from dashboard.products_master.pdf_processing.process_ai_simple import main as process_ai_main
from dashboard.products_master.ai_extract_models import AIExtractTransaction, AIExtractTransactionDetail
from dashboard.products_master.ai_services import process_extraction_results
from dashboard.products_master.models import Product
from django.core.files.base import ContentFile

def validate_config_paths():
    """設定ファイルのパスを検証"""
    if getattr(sys, 'frozen', False):
        config_path = Path(sys.executable).parent / "config.ini"
    else:
        config_path = Path(__file__).parent / "config.ini"
    
    if not config_path.exists():
        print(f"❗ エラー: 設定ファイルが見つかりません: {config_path}")
        sys.exit(1)
    
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')
    
    # バッチ処理用フォルダチェック
    watch_folder = config.get('AI_BATCH', 'watch_folder', fallback=r'C:\S3\batch_input')
    error_folder = config.get('AI_BATCH', 'error_folder', fallback=r'C:\S3\batch_error')
    
    if not Path(watch_folder).exists():
        print(f"❗ エラー: 監視フォルダが見つかりません: {watch_folder}")
        print("config.iniの[AI_BATCH]watch_folder設定を確認してください")
        sys.exit(1)
    
    if not Path(error_folder).exists():
        print(f"❗ エラー: エラーフォルダが見つかりません: {error_folder}")
        print("config.iniの[AI_BATCH]error_folder設定を確認してください")
        sys.exit(1)
    
    # データベースファイルチェック
    db_path = config.get('DATABASE', 'path', fallback='db.sqlite3')
    if not Path(db_path).exists():
        print(f"❗ エラー: データベースファイルが見つかりません: {db_path}")
        print("config.iniの[DATABASE]path設定を確認してください")
        sys.exit(1)

def load_config():
    """設定ファイルを読み込み"""
    config = configparser.ConfigParser()
    
    # PyInstaller環境ではexeと同じフォルダのconfig.iniを参照
    if getattr(sys, 'frozen', False):
        config_path = Path(sys.executable).parent / "config.ini"
    else:
        config_path = Path(__file__).parent / "config.ini"
    
    # デフォルト値
    defaults = {
        'watch_folder': r'C:\S3\batch_input',
        'error_folder': r'C:\S3\batch_error',
        'media_root': 'media',
        'http_proxy': '',
        'https_proxy': '',
        'proxy_auth': '',
        'pac_url': ''
    }
    
    if config_path.exists():
        try:
            config.read(config_path, encoding='utf-8')
            watch_folder = config.get('AI_BATCH', 'watch_folder', fallback=defaults['watch_folder'])
            error_folder = config.get('AI_BATCH', 'error_folder', fallback=defaults['error_folder'])
            media_root = config.get('FILES', 'media_root', fallback=defaults['media_root'])
            http_proxy = config.get('PROXY', 'http_proxy', fallback=defaults['http_proxy'])
            https_proxy = config.get('PROXY', 'https_proxy', fallback=defaults['https_proxy'])
            proxy_auth = config.get('PROXY', 'proxy_auth', fallback=defaults['proxy_auth'])
            pac_url = config.get('PROXY', 'pac_url', fallback=defaults['pac_url'])
            return watch_folder, error_folder, media_root, http_proxy, https_proxy, proxy_auth, pac_url
        except Exception:
            pass
    
    return defaults['watch_folder'], defaults['error_folder'], defaults['media_root'], defaults['http_proxy'], defaults['https_proxy'], defaults['proxy_auth'], defaults['pac_url']

def test_proxy_connection(proxy_url):
    """プロキシ接続をテスト"""
    try:
        import requests
        proxies = {'http': proxy_url, 'https': proxy_url}
        # PyInstaller環境ではタイムアウトを短くしてフォールバックを早くする
        timeout = 5 if getattr(sys, 'frozen', False) else 10
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        print(f"プロキシテストエラー: {e}")
        return False

def setup_proxy_environment(http_proxy, https_proxy, proxy_auth):
    """プロキシ環境変数を設定"""
    if http_proxy:
        # プロトコルを除去して正しい形式に変換
        clean_proxy = http_proxy.replace('http://', '').replace('https://', '')
        if proxy_auth:
            proxy_url = f"http://{proxy_auth}@{clean_proxy}"
            os.environ['HTTP_PROXY'] = proxy_url
        else:
            proxy_url = f"http://{clean_proxy}"
            os.environ['HTTP_PROXY'] = proxy_url
        
        # PyInstaller環境ではプロキシテストをスキップして直接設定
        if getattr(sys, 'frozen', False):
            print(f"プロキシ設定: {clean_proxy} (PyInstaller環境 - テストスキップ)")
        else:
            # プロキシ接続テスト
            print(f"プロキシ接続テスト中: {clean_proxy}")
            if test_proxy_connection(proxy_url):
                print("プロキシ接続: 成功")
            else:
                print("プロキシ接続: 失敗 - 直接接続を試行")
                # プロキシ設定をクリア
                if 'HTTP_PROXY' in os.environ:
                    del os.environ['HTTP_PROXY']
                if 'HTTPS_PROXY' in os.environ:
                    del os.environ['HTTPS_PROXY']
    
    if https_proxy and 'HTTP_PROXY' in os.environ:
        # HTTPプロキシが設定されている場合のみHTTPSも設定
        clean_proxy = https_proxy.replace('http://', '').replace('https://', '')
        if proxy_auth:
            os.environ['HTTPS_PROXY'] = f"http://{proxy_auth}@{clean_proxy}"
        else:
            os.environ['HTTPS_PROXY'] = f"http://{clean_proxy}"
    
    print(f"プロキシ設定: HTTP={os.environ.get('HTTP_PROXY', 'なし')}, HTTPS={os.environ.get('HTTPS_PROXY', 'なし')}")

# 設定読み込み
WATCH_FOLDER, ERROR_FOLDER, MEDIA_ROOT, HTTP_PROXY, HTTPS_PROXY, PROXY_AUTH, PAC_URL = load_config()

def ensure_folders():
    """必要なフォルダを作成"""
    try:
        for folder in [WATCH_FOLDER, ERROR_FOLDER]:
            Path(folder).mkdir(parents=True, exist_ok=True)
        # logフォルダをinputフォルダの下に作成
        log_folder = Path(WATCH_FOLDER) / "log"
        log_folder.mkdir(exist_ok=True)
        print(f"フォルダ作成完了")
        return log_folder
    except Exception as e:
        print(f"フォルダ作成エラー: {e}")
        sys.exit(1)

def process_pdf_file(pdf_path):
    """単一PDFファイルを処理"""
    print(f"処理開始: {pdf_path}")
    
    try:
        # 一時ファイルパス
        temp_dir = tempfile.gettempdir()
        di_result_path = os.path.join(temp_dir, f"batch_di_{os.getpid()}_{uuid.uuid4().hex[:8]}.pkl")
        ai_result_path = os.path.join(temp_dir, f"batch_ai_{os.getpid()}_{uuid.uuid4().hex[:8]}.json")
        
        # Document Intelligence処理
        print("  Document Intelligence処理中...")
        extract_di_main(str(pdf_path), di_result_path)
        
        # AI解析処理
        print("  AI解析処理中...")
        ai_results = process_ai_main(di_result_path, ai_result_path)
        print(f"  AI解析結果: {ai_results is not None}")
        
        if ai_results is None:
            print("  AI解析がNoneを返しました")
            return False
        
        products = ai_results.get('products', [])
        print(f"  抽出された商品数: {len(products)}")
        
        if not products:
            print("  商品情報が抽出できませんでした")
            return False
        
        # トランザクション作成
        print("  トランザクション作成中...")
        transaction_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        document_metadata = ai_results.get('document_metadata', {})
        sender = document_metadata.get('sender', '')
        reason = document_metadata.get('reason', 'バッチ処理によるAI抽出')
        print(f"  送信元: {sender}, 理由: {reason}")
        
        # PDFファイルを読み込み
        print("  PDFファイル読み込み中...")
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        print(f"  PDFサイズ: {len(pdf_content)} bytes")
        
        print("  データベースにトランザクション保存中...")
        match_transaction = AIExtractTransaction.objects.create(
            transaction_id=transaction_id,
            executor='batch_system',
            effective_year_month='',
            revision_reason=reason,
            remarks=f"バッチ処理 - {pdf_path.name} (送信元: {sender})",
            uploaded_pdf=ContentFile(pdf_content, name=pdf_path.name),
            total_products=len(ai_results['products']),
            status='照合中'
        )
        print(f"  トランザクションID: {transaction_id}")
        
        # PDF保存パスをログ出力
        print(f"  PDF保存パス: {match_transaction.uploaded_pdf.path}")
        
        # 商品照合処理
        print("  商品照合処理中...")
        json_data = {
            'document_metadata': document_metadata,
            'products': [
                {
                    'product_name': entity.get('name'),
                    'new_price': entity.get('price'),
                    'model_number': entity.get('model'),
                    'manufacturer': sender if sender else None,
                    'specification': entity.get('spec')
                }
                for entity in ai_results['products']
            ]
        }
        print(f"  照合対象商品数: {len(json_data['products'])}")
        
        results = process_extraction_results(json_data)
        print(f"  照合結果: {results is not None}")
        
        if results is None:
            print("  商品照合処理が失敗しました")
            return False
        
        # 照合結果を明細テーブルに保存
        print("  明細データ保存中...")
        results_list = results.get('results', [])
        print(f"  保存対象明細数: {len(results_list)}")
        
        for i, result in enumerate(results_list):
            extracted_data = result.get('extracted_data', {})
            candidates = result.get('candidates', [])
            
            matched_product = None
            match_score = None
            if candidates:
                best_candidate = candidates[0]
                matched_product_id = best_candidate.get('product', {}).get('pk')
                if matched_product_id:
                    try:
                        matched_product = Product.objects.get(pk=matched_product_id)
                        match_score = best_candidate.get('score', 0)
                    except Product.DoesNotExist:
                        pass
            
            detail = AIExtractTransactionDetail.objects.create(
                transaction=match_transaction,
                sequence=i + 1,
                extracted_product_name=extracted_data.get('product_name'),
                extracted_model_number=extracted_data.get('model_number'),
                extracted_manufacturer=extracted_data.get('manufacturer'),
                extracted_specification=extracted_data.get('specification'),
                extracted_price=str(extracted_data.get('new_price', '')),
                extracted_revision_reason='',
                matched_product=matched_product,
                match_score=match_score,
                status='未処理'
            )
            print(f"    明細{i+1}: {extracted_data.get('product_name')} -> {matched_product.product_name if matched_product else 'マッチなし'}")
        
        # 一時ファイル削除
        for temp_file in [di_result_path, ai_result_path]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        print(f"  処理完了: トランザクションID {transaction_id}")
        print(f"  抽出商品数: {len(ai_results['products'])}")
        print(f"  保存された明細数: {len(results_list)}")
        return True
        
    except Exception as e:
        print(f"  エラー: {str(e)}")
        # PyInstaller環境では詳細なエラー情報をログに出力
        error_detail = traceback.format_exc()
        print(f"  詳細エラー: {error_detail}")
        
        # ログファイルにも詳細エラーを出力
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"PDF処理エラー: {pdf_path.name}")
        logger.error(f"エラー詳細: {str(e)}")
        logger.error(f"スタックトレース: {error_detail}")
        
        return False

def move_file(src_path, dest_folder):
    """ファイルを移動"""
    dest_path = Path(dest_folder) / src_path.name
    counter = 1
    while dest_path.exists():
        stem = src_path.stem
        suffix = src_path.suffix
        dest_path = Path(dest_folder) / f"{stem}_{counter}{suffix}"
        counter += 1
    
    shutil.move(str(src_path), str(dest_path))
    return dest_path

def main():
    """メイン処理"""
    print("=== AI抽出バッチ処理開始 ===")
    
    # 設定ファイル検証
    validate_config_paths()
    print(f"監視フォルダ: {WATCH_FOLDER}")
    print(f"エラーフォルダ: {ERROR_FOLDER}")
    print(f"PDF保存先: {MEDIA_ROOT} (画面と同じ場所)")
    print(f"設定ファイル: config.ini")
    
    # DBパスを取得・表示
    from digital_pricelist_system.settings import get_database_path
    db_path = get_database_path()
    print(f"DBファイル: {db_path}")
    
    # プロキシ設定を環境変数に設定
    setup_proxy_environment(HTTP_PROXY, HTTPS_PROXY, PROXY_AUTH)
    
    # フォルダ作成
    log_folder = ensure_folders()
    
    # ログ設定
    log_file = log_folder / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # config.iniパスを表示
    if getattr(sys, 'frozen', False):
        config_path = Path(sys.executable).parent / "config.ini"
    else:
        config_path = Path(__file__).parent / "config.ini"
    
    logger.info("=== AI抽出バッチ処理開始 ===")
    logger.info(f"設定ファイル: {config_path} {'(存在)' if config_path.exists() else '(デフォルト値使用)'}")
    logger.info(f"監視フォルダ: {WATCH_FOLDER}")
    logger.info(f"エラーフォルダ: {ERROR_FOLDER}")
    logger.info(f"DBファイル: {db_path}")
    logger.info(f"ログファイル: {log_file}")
    
    # MEDIA_ROOTパスを表示
    from digital_pricelist_system.settings import get_media_root
    media_root = get_media_root()
    logger.info(f"MEDIA_ROOT: {media_root}")
    
    # PDFファイルを検索
    watch_path = Path(WATCH_FOLDER)
    pdf_files = list(watch_path.glob("*.pdf"))
    
    if not pdf_files:
        print("処理対象のPDFファイルがありません")
        return
    
    print(f"処理対象ファイル数: {len(pdf_files)}")
    logger.info(f"処理対象ファイル数: {len(pdf_files)}")
    
    success_count = 0
    error_count = 0
    
    for pdf_file in pdf_files:
        print(f"\n--- {pdf_file.name} ---")
        logger.info(f"--- {pdf_file.name} ---")
        
        if process_pdf_file(pdf_file):
            # 成功時は元ファイルを削除（PDFはDjangoのメディアフォルダに保存済み）
            pdf_file.unlink()
            print(f"  処理完了: 元ファイル削除")
            logger.info(f"処理成功: {pdf_file.name}")
            success_count += 1
        else:
            # 失敗時はエラーフォルダに移動
            dest_path = move_file(pdf_file, ERROR_FOLDER)
            print(f"  エラーファイル移動先: {dest_path}")
            logger.error(f"処理失敗: {pdf_file.name} -> {dest_path}")
            error_count += 1
    
    print(f"\n=== 処理結果 ===")
    print(f"成功: {success_count}件")
    print(f"エラー: {error_count}件")
    print("=== バッチ処理終了 ===")
    
    logger.info(f"=== 処理結果 ===")
    logger.info(f"成功: {success_count}件")
    logger.info(f"エラー: {error_count}件")
    logger.info("=== バッチ処理終了 ===")

if __name__ == "__main__":
    main()