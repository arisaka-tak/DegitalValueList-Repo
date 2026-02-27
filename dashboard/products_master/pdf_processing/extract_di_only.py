"""
Document Intelligence 抽出専用スクリプト
PDFから表データを抽出してJSONファイルに保存
"""
import os
import sys
import pickle
import urllib.request
import re
import getpass
import logging
from urllib.parse import urlparse
import httpx
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import httpx_auth
    HTTPX_AUTH_AVAILABLE = True
except ImportError:
    HTTPX_AUTH_AVAILABLE = False

try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False

# Document Intelligence設定
DOCUMENT_INTELLIGENCE_ENDPOINT = "https://digital-valuelist-prd.cognitiveservices.azure.com/"
DOCUMENT_INTELLIGENCE_API_KEY = "397a72600d7e45f6b2462d5b99edc38a"

def get_proxy_settings():
    """プロキシ設定をconfig.iniから取得、なければ自動検出"""
    try:
        # まずconfig.iniからプロキシ設定を取得
        try:
            import configparser
            from digital_pricelist_system.config_paths import CONFIG_PATH
            
            logger.info(f"[DI処理] config.iniパス: {CONFIG_PATH}")
            logger.info(f"[DI処理] config.ini存在: {CONFIG_PATH.exists()}")
            
            config = configparser.ConfigParser()
            if CONFIG_PATH.exists():
                config.read(CONFIG_PATH, encoding='utf-8')
                http_proxy = config.get('PROXY', 'http_proxy', fallback='')
                proxy_auth = config.get('PROXY', 'proxy_auth', fallback='')
                
                logger.info(f"[DI処理] プロキシ設定読み込み: http_proxy={bool(http_proxy)}, auth={bool(proxy_auth)}")
                
                if http_proxy:
                    clean_proxy = http_proxy.replace('http://', '').replace('https://', '')
                    if proxy_auth:
                        proxy_url = f"http://{proxy_auth}@{clean_proxy}"
                    else:
                        proxy_url = f"http://{clean_proxy}"
                    logger.info(f"[DI処理] config.iniからプロキシ設定: {clean_proxy}")
                    return proxy_url
            else:
                logger.warning(f"[DI処理] config.iniが見つかりません")
        except Exception as e:
            logger.warning(f"[DI処理] config.ini読み込みエラー: {e}")
        
        # config.iniに設定がない場合は自動検出
        logger.info(f"[DI処理] 自動プロキシ検出を実行")
        # 環境変数からプロキシを取得
        proxies = urllib.request.getproxies()
        if proxies:
            logger.info(f"[DI処理] 検出されたプロキシ設定: {proxies}")
            return proxies.get('https') or proxies.get('http')
        
        # Windows レジストリからプロキシ設定を取得
        if os.name == 'nt' and WINREG_AVAILABLE:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
                
                # PACファイルのチェック
                try:
                    auto_config_url, _ = winreg.QueryValueEx(key, "AutoConfigURL")
                    if auto_config_url:
                        logger.info(f"[DI処理] PACファイル検出: {auto_config_url}")
                        # PACファイルからプロキシを解析
                        proxy = parse_pac_file(auto_config_url)
                        if proxy:
                            winreg.CloseKey(key)
                            return proxy
                except FileNotFoundError:
                    pass
                
                # 直接プロキシ設定のチェック
                try:
                    proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                    if proxy_enable:
                        proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                        logger.info(f"[DI処理] Windows 直接プロキシ: {proxy_server}")
                        winreg.CloseKey(key)
                        return f"http://{proxy_server}"
                except FileNotFoundError:
                    pass
                
                winreg.CloseKey(key)
            except Exception as e:
                logger.error(f"[DI処理] Windowsレジストリエラー: {e}")
        
        logger.info(f"[DI処理] プロキシ設定が見つかりません")
        return None
    except Exception as e:
        logger.error(f"[DI処理] プロキシ検出エラー: {e}")
        return None

def parse_pac_file(pac_url):
    """簡易PACファイルパーサー"""
    try:
        
        logger.info(f"PACファイルを取得中: {pac_url}")
        
        # PACファイルをダウンロード
        with urllib.request.urlopen(pac_url, timeout=10) as response:
            pac_bytes = response.read()
            
        # 文字エンコーディングを自動検出
        try:
            pac_content = pac_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                pac_content = pac_bytes.decode('shift_jis')
            except UnicodeDecodeError:
                try:
                    pac_content = pac_bytes.decode('latin1')
                except UnicodeDecodeError:
                    logger.error(f"PACファイルの文字エンコーディングを判定できません")
                    return None
        
        # PROXY 指定を検索（簡易版）
        proxy_pattern = r'PROXY\s+([^;\s]+)'
        matches = re.findall(proxy_pattern, pac_content, re.IGNORECASE)
        
        if matches:
            proxy_server = matches[0].strip('"\' ')
            logger.info(f"PACからプロキシを検出: {proxy_server}")
            return f"http://{proxy_server}"
        
        logger.warning("PACファイルからプロキシを検出できませんでした")
        return None
        
    except Exception as e:
        logger.error(f"PACファイル解析エラー: {e}")
        return None

def extract_from_pdf(pdf_path: str, output_path: str = None):
    """PDFからDocument Intelligence結果を抽出してpickleファイルに保存"""
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "di_result.pkl")
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDFファイルが見つかりません: {pdf_path}")
        return
    
    logger.info("Document Intelligence 抽出開始...")
    logger.info(f"入力ファイル: {pdf_path}")
    logger.info(f"出力ファイル: {output_path}")
    
    try:
        # プロキシ設定を取得
        proxy_url = get_proxy_settings()
        
        # Document Intelligence クライアント初期化
        if proxy_url:
            logger.info(f"プロキシを使用: {proxy_url}")
            
            # Windows統合認証付きプロキシ設定
            try:
                # 現在のユーザーの認証情報を取得
                
                username = os.environ.get('USERNAME', getpass.getuser())
                domain = os.environ.get('USERDOMAIN', '')
                
                if domain:
                    auth_user = f"{domain}\\{username}"
                else:
                    auth_user = username
                
                logger.info(f"認証ユーザー: {auth_user}")
                
                # 認証付きプロキシURLを作成
                parsed = urlparse(proxy_url)
                
                # プロキシ設定を試行（タイムアウト延長）
                try:
                    # httpx 0.27.xの新しいAPI（タイムアウト300秒=5分）
                    http_client = httpx.Client(
                        proxy=proxy_url,
                        timeout=httpx.Timeout(300.0, connect=30.0)
                    )
                    logger.info("プロキシ接続を試行（タイムアウト300秒）")
                except TypeError:
                    # 古いhttpxバージョン
                    http_client = httpx.Client(
                        proxies={'http': proxy_url, 'https': proxy_url},
                        timeout=httpx.Timeout(300.0, connect=30.0)
                    )
                    logger.info("レガシープロキシ設定で接続（タイムアウト300秒）")
                
            except Exception as e:
                logger.error(f"プロキシ設定エラー: {e}")
                # フォールバック: プロキシなし
                http_client = httpx.Client()
                logger.info("プロキシなしで接続にフォールバック")
            
            client = DocumentIntelligenceClient(
                endpoint=DOCUMENT_INTELLIGENCE_ENDPOINT,
                credential=AzureKeyCredential(DOCUMENT_INTELLIGENCE_API_KEY),
                http_client=http_client
            )
        else:
            logger.info("プロキシなしで接続")
            # プロキシなしでもタイムアウト設定（300秒=5分）
            http_client = httpx.Client(timeout=httpx.Timeout(300.0, connect=30.0))
            client = DocumentIntelligenceClient(
                endpoint=DOCUMENT_INTELLIGENCE_ENDPOINT,
                credential=AzureKeyCredential(DOCUMENT_INTELLIGENCE_API_KEY),
                http_client=http_client
            )
        
        # PDF解析実行
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        logger.info(f"ファイルサイズ: {len(pdf_content)} bytes")
        
        poller = client.begin_analyze_document("prebuilt-layout", pdf_content)
        result = poller.result()
        
        logger.info(f"検出された表数: {len(result.tables)}")
        logger.info(f"検出された段落数: {len(result.paragraphs)}")
        logger.info(f"検出されたページ数: {len(result.pages)}")
        
        # resultオブジェクトをそのままpickleで保存
        with open(output_path, 'wb') as f:
            pickle.dump(result, f)
        
        logger.info(f"✓ 抽出完了: {output_path} に保存しました")
        logger.info(f"  - 表: {len(result.tables)}個")
        logger.info(f"  - 段落: {len(result.paragraphs)}個")
        logger.info(f"  - ページ: {len(result.pages)}個")
        
        # 簡易プレビュー表示
        for i, table in enumerate(result.tables):
            logger.info(f"表 {i+1}: {table.row_count}行 x {table.column_count}列")
        
        logger.info(f"最初の5段落:")
        for i, paragraph in enumerate(result.paragraphs[:5]):
            content_preview = paragraph.content[:100] + "..." if len(paragraph.content) > 100 else paragraph.content
            logger.info(f"  {i+1}: {content_preview}")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def main(pdf_path=None, output_path=None):
    """メイン関数"""
    # コマンドラインからの実行時のみ sys.argv を使用
    if pdf_path is None and __name__ == "__main__":
        if len(sys.argv) > 1:
            pdf_path = sys.argv[1]
        else:
            pdf_path = "C:\Project\ZCS_DegitalValueList\キ　木村農産・土佐農機訂正　0204値上げ.pdf"
    
    if output_path is None:
        if __name__ == "__main__" and len(sys.argv) > 2:
            output_path = sys.argv[2]
        else:
            output_path = os.path.join(os.path.dirname(__file__), "di_result.pkl")
    
    # パラメータが指定されていない場合はエラー
    if pdf_path is None:
        raise ValueError("入力PDFパスが指定されていません")
    
    extract_from_pdf(pdf_path, output_path)

if __name__ == "__main__":
    main()