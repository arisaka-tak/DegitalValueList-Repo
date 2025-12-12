"""
AI処理専用スクリプト（シンプル版）
Document Intelligence結果JSONファイルからAI解析のみ実行
"""
import os
import sys
import json
import pickle
import django
import logging
from typing import List, Dict, Optional

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Django設定
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from openai import AzureOpenAI
import httpx
from dashboard.products_master.pdf_processing.extract_di_only import get_proxy_settings

# Azure OpenAI設定
AZURE_OPENAI_ENDPOINT = "https://zlc-ai-dev.openai.azure.com/"
AZURE_OPENAI_API_KEY = "Firp3Exko4QXYsrfIrd0TxH7pbpi5Y01w3r1xzBYyoA5dhmlh0iHJQQJ99BLACi0881XJ3w3AAABACOGeR0n"
AZURE_OPENAI_DEPLOYMENT = "ZLC-gpt-4.1-mini"

class AITableAnalyzer:
    """AI表解析専用クラス"""
    
    def __init__(self):
        self.openai_client = self._init_openai_client()
    
    def _init_openai_client(self):
        """Azure OpenAI クライアント初期化"""
        try:
            proxy_url = get_proxy_settings()
            
            if proxy_url:
                logger.info(f"プロキシを使用: {proxy_url}")
                try:
                    http_client = httpx.Client(proxy=proxy_url)
                except TypeError:
                    http_client = httpx.Client(proxies={'http': proxy_url, 'https': proxy_url})
                
                client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version="2024-08-01-preview",
                    http_client=http_client
                )
            else:
                logger.info("プロキシなしで接続")
                client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version="2024-08-01-preview"
                )
            
            logger.info("✓ Azure OpenAI クライアント初期化成功")
            return client
            
        except Exception as e:
            logger.error(f"✗ Azure OpenAI 初期化エラー: {e}")
            return None
    
    def analyze_table_structure(self, table_data: List[List[str]]) -> tuple:
        """表構造をAIで解析"""
        if self.openai_client is None:
            return None, None, None, None, None
        
        try:
            sample_data = table_data[:min(10, len(table_data))]
            
            schema = {
                "type": "object",
                "properties": {
                    "header_row": {
                        "type": "integer",
                        "description": "ヘッダー行のインデックス(0から開始)"
                    },
                    "product_column": {
                        "type": "integer",
                        "description": "商品名列のインデックス(0から開始)"
                    },
                    "price_column": {
                        "type": "integer",
                        "description": "価格列のインデックス(0から開始)"
                    },
                    "model_column": {
                        "type": ["integer", "null"],
                        "description": "型式列のインデックス(0から開始)、ない場合はnull"
                    },
                    "spec_column": {
                        "type": ["integer", "null"],
                        "description": "規格列のインデックス(0から開始)、ない場合はnull"
                    }
                },
                "required": ["header_row", "product_column", "price_column", "model_column", "spec_column"],
                "additionalProperties": False
            }
            
            prompt = f"""
これは商品仕入価格の変更通知書の表データです。
最初のヘッダー行と各列を特定してください。

表データ:
{sample_data}

注意事項:
- 商品名列: 「商品」「品名」「製品」などを含む列
- 価格列: 「仕切価格」「新価格」「改定後」などを含む列
- 型式列: 「コード」「型式」などを含む列（ない場合はnull）
- 規格列: 「仕様」「規格」などを含む列（ない場合はnull）
"""
            
            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "あなたは商品仕入価格変更通知書の解析専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "table_structure_analysis",
                        "schema": schema,
                        "strict": True
                    }
                }
            )
            
            result = json.loads(response.choices[0].message.content)
            return (result["header_row"], result["product_column"], result["price_column"], 
                    result["model_column"], result["spec_column"])
            
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
            return None, None, None, None, None
    
    def extract_document_metadata(self, all_text: str) -> dict:
        """文書全体からメタデータを抽出"""
        if self.openai_client is None:
            return {"sender": None, "reason": None}
        
        try:
            schema = {
                "type": "object",
                "properties": {
                    "sender": {
                        "type": ["string", "null"],
                        "description": "通知の送信元の会社名のみ（㈱、株式会社、部署名、特品部などは除外）"
                    },
                    "reason": {
                        "type": ["string", "null"],
                        "description": "価格変更の理由を20文字以内で『～のため』で終わる短文に要約"
                    }
                },
                "required": ["sender", "reason"],
                "additionalProperties": False
            }
            
            prompt = f"""
以下の文書から「通知の送信元」と「価格変更理由」を抽出してください。

文書内容:
{all_text[:3000]}...

抽出項目:
1. 通知の送信元: 会社名のみ（㈱、株式会社、部署名、特品部などは除外）
2. 価格変更理由: 20文字以内で『～のため』で終わる短文に要約（例：原材料費上昇のため、運送費増加のため）

見つからない場合はnullを返してください。
"""
            
            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "あなたは文書解析の専門家です。正確に情報を抽出してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "document_metadata",
                        "schema": schema,
                        "strict": True
                    }
                }
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"文書メタデータ抽出エラー: {e}")
            return {"sender": None, "reason": None}
    
    def extract_products_from_text(self, text: str) -> List[dict]:
        """文章から商品価格情報を抽出"""
        if self.openai_client is None:
            return []
        
        try:
            schema = {
                "type": "object",
                "properties": {
                    "products": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "商品名"
                                },
                                "price": {
                                    "type": "string",
                                    "description": "価格（数字のみ）"
                                },
                                "model": {
                                    "type": ["string", "null"],
                                    "description": "型式・コード（ある場合のみ）"
                                },
                                "spec": {
                                    "type": ["string", "null"],
                                    "description": "規格・仕様（ある場合のみ）"
                                }
                            },
                            "required": ["name", "price", "model", "spec"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["products"],
                "additionalProperties": False
            }
            
            prompt = f"""
以下の文書から商品価格情報を抽出してください。

文書内容:
{text[:4000]}...

抽出条件:
- 商品名が明記されているもの（価格がなくても可）
- 価格は改定後・新価格・変更後の価格を優先
- 価格は数字のみで抽出（カンマや円マークは除外）
- 型式やコードがある場合はmodelフィールドに抽出
- 規格や仕様がある場合はspecフィールドに抽出
- 「終売」「販売終了」「廃番」「取扱終了」「生産終了」「製造終了」の場合はprice: "0"
- 廃番商品リストからも商品名・型式・コードを抽出

注意:
- 曖昧な表現（「一律10%値上げ」など）は除外
- 商品名やコードが特定できるもののみ抽出
- 見つからない場合は空配列を返す
"""
            
            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "あなたは商品価格抽出の専門家です。文章から正確に商品名と価格を抽出してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "text_product_extraction",
                        "schema": schema,
                        "strict": True
                    }
                }
            )
            
            result = json.loads(response.choices[0].message.content)
            return result["products"]
            
        except Exception as e:
            logger.error(f"文章商品抽出エラー: {e}")
            return []

def process_tables_with_ai(input_path: str = None, output_path: str = None):
    """Document Intelligence結果をAIで処理"""
    if input_path is None:
        input_path = os.path.join(os.path.dirname(__file__), "di_result.pkl")
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "ai_results.json")
    
    if not os.path.exists(input_path):
        logger.error(f"入力ファイルが見つかりません: {input_path}")
        return
    
    logger.info("AI処理開始...")
    
    with open(input_path, 'rb') as f:
        result = pickle.load(f)
    
    logger.info(f"処理対象: {len(result.tables)}個の表")
    
    analyzer = AITableAnalyzer()
    
    # 文書全体からメタデータを抽出
    logger.info("文書メタデータ抽出")
    all_text = " ".join([p.content for p in result.paragraphs if p.content])
    document_metadata = analyzer.extract_document_metadata(all_text)
    
    logger.info(f"通知の送信元: {document_metadata.get('sender', '未検出')}")
    logger.info(f"価格変更理由: {document_metadata.get('reason', '未検出')}")
    
    extracted_products = []
    
    for i, table in enumerate(result.tables):
        table_id = i + 1
        logger.info(f"表 {table_id}: {table.row_count}行 x {table.column_count}列")
        
        # 表データを2次元配列に変換
        table_matrix = [["" for _ in range(table.column_count)] 
                       for _ in range(table.row_count)]
        
        for cell in table.cells:
            table_matrix[cell.row_index][cell.column_index] = cell.content or ""
        
        # 表内容表示
        for row_idx in range(min(table.row_count, 10)):
            logger.debug(f"  行{row_idx}: {table_matrix[row_idx]}")
        
        # AI解析実行
        try:
            analysis_result = analyzer.analyze_table_structure(table_matrix)
            if analysis_result[0] is None:
                continue
            
            header_row, product_col, price_col, model_col, spec_col = analysis_result
            
            logger.info(f"  ヘッダー行: {header_row}")
            logger.info(f"  商品名列: {product_col}")
            logger.info(f"  価格列: {price_col}")
            logger.info(f"  型式列: {model_col}")
            logger.info(f"  規格列: {spec_col}")
            
            if product_col is None or price_col is None:
                logger.warning("  -> 商品名または価格列が見つかりません")
                continue
            
            # ヘッダー行以降のデータ行を直接処理
            for row_idx in range(header_row + 1, table.row_count):
                product_name = table_matrix[row_idx][product_col] if product_col < len(table_matrix[row_idx]) else ""
                price_value = table_matrix[row_idx][price_col] if price_col < len(table_matrix[row_idx]) else ""
                model_value = table_matrix[row_idx][model_col] if model_col is not None and model_col < len(table_matrix[row_idx]) else ""
                spec_value = table_matrix[row_idx][spec_col] if spec_col is not None and spec_col < len(table_matrix[row_idx]) else ""
                
                if product_name.strip() and price_value.strip():
                    clean_price = ''.join(filter(str.isdigit, price_value))
                    
                    if clean_price:
                        product_data = {
                            'table_id': table_id,
                            'name': product_name.strip(),
                            'price': clean_price
                        }
                        if model_value:
                            product_data['model'] = model_value.strip()
                        if spec_value:
                            product_data['spec'] = spec_value.strip()
                        
                        extracted_products.append(product_data)
                        
                        debug_info = f"  -> 抽出: {product_name.strip()} = {clean_price}円"
                        if model_value:
                            debug_info += f", 型式: {model_value.strip()}"
                        if spec_value:
                            debug_info += f", 規格: {spec_value.strip()}"
                        logger.info(debug_info)
        
        except Exception as e:
            logger.error(f"  -> エラー: {e}")
            continue
    
    # フォールバック処理: 表から商品が抽出できない場合、段落から抽出を試行
    if len(extracted_products) == 0:
        logger.info("フォールバック: 段落からの商品抽出開始")
        all_text = " ".join([p.content for p in result.paragraphs if p.content])
        logger.info(f"段落テキスト長: {len(all_text)}文字")
        
        if all_text.strip():
            try:
                text_products = analyzer.extract_products_from_text(all_text)
                if text_products:
                    for product in text_products:
                        product['table_id'] = 'text'
                        extracted_products.append(product)
                    logger.info(f"段落から {len(text_products)} 件の商品を抽出しました")
                else:
                    logger.warning("段落からも商品情報を抽出できませんでした")
            except Exception as e:
                logger.error(f"段落抽出エラー: {e}")
    
    # 結果保存
    result_data = {
        'source_file': input_path,
        'document_metadata': document_metadata,
        'processed_tables': len(result.tables),
        'extracted_products_count': len(extracted_products),
        'products': extracted_products
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"最終結果")
    logger.info(f"抽出商品: {len(extracted_products)} 件")
    for i, product in enumerate(extracted_products, 1):
        logger.info(f"{i:2d}. 商品名: {product['name']}")
        logger.info(f"    価格: {product['price']} 円")
        if 'model' in product:
            logger.info(f"    型式: {product['model']}")
        if 'spec' in product:
            logger.info(f"    規格: {product['spec']}")
        logger.info(f"    (表{product['table_id']}から抽出)")
    
    logger.info(f"✓ 処理完了: 結果を {output_path} に保存しました")
    return result_data

def main(input_file=None, output_file=None):
    """メイン関数"""
    if input_file is None:
        input_file = os.path.join(os.path.dirname(__file__), "di_result.pkl")
    
    if output_file is None:
        output_file = os.path.join(os.path.dirname(__file__), "ai_results.json")
    
    return process_tables_with_ai(input_file, output_file)

if __name__ == "__main__":
    main()