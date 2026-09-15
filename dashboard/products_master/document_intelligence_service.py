"""
Azure Document Intelligence サービス
FAXスキャン画像の構造化データ抽出
"""
import os
from typing import Dict, List, Optional
from django.core.files.uploadedfile import UploadedFile

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import json

# Document Intelligence用の設定
DOCUMENT_INTELLIGENCE_ENDPOINT = "https://digital-valuelist-prd.cognitiveservices.azure.com/"
DOCUMENT_INTELLIGENCE_API_KEY = "397a72600d7e45f6b2462d5b99edc38a"

# Azure OpenAI用の設定
AZURE_OPENAI_ENDPOINT = "https://zlc-ai-dev.openai.azure.com/"
AZURE_OPENAI_API_KEY = "Firp3Exko4QXYsrfIrd0TxH7pbpi5Y01w3r1xzBYyoA5dhmlh0iHJQQJ99BLACi0881XJ3w3AAABACOGeR0n"
AZURE_OPENAI_DEPLOYMENT = "ZLC-gpt-4.1-mini"

class DocumentIntelligenceService:
    """Azure Document Intelligence サービス"""
    
    def __init__(self):
        self.endpoint = DOCUMENT_INTELLIGENCE_ENDPOINT
        self.api_key = DOCUMENT_INTELLIGENCE_API_KEY
        
        # Azure OpenAI クライアント初期化
        try:
            import httpx
            
            # プロキシ設定を取得
            proxy_url = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
            
            if proxy_url:
                # プロキシありの場合
                http_client = httpx.Client(proxies=proxy_url)
                self.openai_client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version="2024-08-01-preview",
                    http_client=http_client
                )
            else:
                # プロキシなしの場合
                self.openai_client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version="2024-08-01-preview"
                )
            
            print("Azure OpenAIクライアント初期化成功")
        except Exception as e:
            print(f"Azure OpenAI初期化エラー: {e}")
            self.openai_client = None
        
        if not self.endpoint or not self.api_key:
            print("Warning: Document Intelligence credentials not configured")
    
    def extract_table_data(self, pdf_file: UploadedFile) -> List[Dict[str, str]]:
        """Document Intelligenceで表データを抽出"""
        try:
            # Azure Document Intelligence クライアント初期化
            client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
            
            # PDF解析実行
            pdf_file.seek(0)
            poller = client.begin_analyze_document(
                "prebuilt-layout",  # レイアウト解析モデル
                pdf_file.read()
            )
            result = poller.result()
            
            # 表データを抽出
            extracted_products = []
            
            for table in result.tables:
                # 表のヘッダー行を特定（Azure OpenAI使用）
                result_analysis = self._analyze_table_structure_with_ai(table)
                if result_analysis[0] is None:  # 商品価格表ではない
                    continue
                    
                header_row, product_col, price_col, model_col, spec_col = result_analysis
                
                if product_col is None or price_col is None:
                    continue
                
                # データ行を処理
                for row_idx in range(header_row + 1, table.row_count):
                    product_name = self._get_cell_content(table, row_idx, product_col)
                    price_value = self._get_cell_content(table, row_idx, price_col)
                    model_value = self._get_cell_content(table, row_idx, model_col) if model_col is not None else None
                    spec_value = self._get_cell_content(table, row_idx, spec_col) if spec_col is not None else None
                    
                    if product_name and price_value:
                        # 価格の数値抽出
                        clean_price = ''.join(filter(str.isdigit, price_value))
                        if clean_price:
                            product_data = {
                                'name': product_name.strip(),
                                'price': clean_price
                            }
                            if model_value:
                                product_data['model'] = model_value.strip()
                            if spec_value:
                                product_data['spec'] = spec_value.strip()
                            
                            extracted_products.append(product_data)
            
            return extracted_products
            
        except Exception as e:
            raise Exception(f"Document Intelligence処理エラー: {str(e)}")
    
    def extract_table_data_debug(self, pdf_file: UploadedFile) -> List[Dict[str, str]]:
        """デバッグ情報付き表データ抽出"""
        try:
            client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
            
            pdf_file.seek(0)
            poller = client.begin_analyze_document("prebuilt-layout", pdf_file.read())
            result = poller.result()
            
            print(f"検出された表数: {len(result.tables)}")
            
            extracted_products = []
            
            for i, table in enumerate(result.tables):
                print(f"\n表 {i+1}: {table.row_count}行 x {table.column_count}列")
                
                # 表の全内容を表示
                for row in range(table.row_count):
                    row_data = []
                    for col in range(table.column_count):
                        cell_content = self._get_cell_content(table, row, col)
                        row_data.append(cell_content or "")
                    print(f"  行{row}: {row_data}")
                
                # ヘッダー行と列の特定（Azure OpenAI使用）
                result = self._analyze_table_structure_with_ai(table)
                if result[0] is None:  # 商品価格表ではない
                    continue
                    
                header_row, product_col, price_col, model_col, spec_col = result
                
                print(f"  ヘッダー行: {header_row}")
                print(f"  商品名列: {product_col}")
                print(f"  価格列: {price_col}")
                print(f"  型式列: {model_col}")
                print(f"  規格列: {spec_col}")
                
                if product_col is None or price_col is None:
                    print("  -> 商品名または価格列が見つかりません")
                    continue
                
                # データ行を処理
                for row_idx in range(header_row + 1, table.row_count):
                    product_name = self._get_cell_content(table, row_idx, product_col)
                    price_value = self._get_cell_content(table, row_idx, price_col)
                    model_value = self._get_cell_content(table, row_idx, model_col) if model_col is not None else None
                    spec_value = self._get_cell_content(table, row_idx, spec_col) if spec_col is not None else None
                    
                    if product_name and price_value:
                        clean_price = ''.join(filter(str.isdigit, price_value))
                        if clean_price:
                            product_data = {
                                'name': product_name.strip(),
                                'price': clean_price
                            }
                            if model_value:
                                product_data['model'] = model_value.strip()
                            if spec_value:
                                product_data['spec'] = spec_value.strip()
                            
                            extracted_products.append(product_data)
                            
                            # デバッグ出力
                            debug_info = f"  -> 抽出: {product_name.strip()} = {clean_price}円"
                            if model_value:
                                debug_info += f", 型式: {model_value.strip()}"
                            if spec_value:
                                debug_info += f", 規格: {spec_value.strip()}"
                            print(debug_info)
            
            return extracted_products
            
        except Exception as e:
            raise Exception(f"Document Intelligence処理エラー: {str(e)}")
    
    def _analyze_table_structure_with_ai(self, table) -> tuple:
        """Azure OpenAI GPT-4.1-miniで表構造を解析"""
        # Azure OpenAIが利用不可の場合はフォールバック
        if self.openai_client is None:
            return self._fallback_analysis(table)
            
        try:
            # 表データを文字列形式で準備
            table_data = []
            for row in range(min(5, table.row_count)):  # 最初の5行のみ解析
                row_data = []
                for col in range(table.column_count):
                    cell_content = self._get_cell_content(table, row, col) or ""
                    row_data.append(cell_content)
                table_data.append(row_data)
            
            # JSONスキーマ定義
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
            
            # まず、この表が商品価格表かどうかを判定
            is_product_table = self._is_product_price_table(table_data)
            if not is_product_table:
                print(f"  -> 商品価格表ではないと判定しました")
                return None, None, None, None, None
            
            prompt = f"""
これは商品仕入価格の変更通知書の表データです。
ヘッダー行と各列を特定してください。

表データ:
{table_data}

注意事項:
- 商品名列: 「商品」「品名」「製品」「品番」などを含む列
- 価格列: 「改定後」「新価格」「仕入価格」「変更後」などを含む列
- 型式列: 「型式」「モデル」「コード」「品番」などを含む列（ない場合はnull）
- 規格列: 「規格」「入数」「ケース」「内容」「仕様」などを含む列（ない場合はnull）
- 「現在価格」「定価」「旧価格」は除外し、改定後の仕入価格のみを特定してください
"""
            
            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "あなたは商品仕入価格変更通知書の解析専門家です。改定後の仕入価格のみを正確に特定してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
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
            print(f"AI解析エラー: {e}")
            # テスト用: フォールバックを無効化してエラーで停止
            raise Exception(f"Azure OpenAI解析失敗: {e}")
            # フォールバック: 従来のロジック (コメントアウト)
            # return self._fallback_analysis(table)
    
    def _fallback_analysis(self, table) -> tuple:
        """AI解析失敗時のフォールバック"""
        header_row = 0
        product_col = None
        price_col = None
        
        for col_idx in range(table.column_count):
            header_text = self._get_cell_content(table, header_row, col_idx)
            if not header_text:
                continue
            
            header_lower = header_text.lower()
            
            if any(keyword in header_lower for keyword in ['商品', '品名', '製品', '品番', 'product']):
                product_col = col_idx
            
            # 改定後の仕入価格を優先的に特定
            if any(keyword in header_lower for keyword in ['改定後', '新価格', '仕入価格', '変更後']):
                price_col = col_idx
            elif price_col is None and any(keyword in header_lower for keyword in ['価格', '単価', '金額', 'price', '円']):
                # 現在価格や定価でない場合のみ
                if not any(exclude in header_lower for exclude in ['現在', '旧', '定価', '従来']):
                    price_col = col_idx
        
        return header_row, product_col, price_col
    
    def _is_product_price_table(self, table_data: List[List[str]]) -> bool:
        """商品価格表かどうかをGPTで判定"""
        if self.openai_client is None:
            return True  # AIが使えない場合は全て処理
        
        try:
            # 最初の20行または全行を取得
            sample_data = table_data[:min(20, len(table_data))]
            
            prompt = f"""
以下の表データを見て、これが「商品仕入価格の変更通知書」の商品価格表かどうかを判定してください。

表データ:
{sample_data}

判定基準:
- 商品価格表: 商品名と価格が記載された表
- 除外対象: 見積表、送料表、カタログ一覧、添付書類一覧、会社情報など

trueまたはfalseで答えてください。
"""
            
            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "あなたは商品価格表の判定専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower()
            return result == "true"
            
        except Exception as e:
            print(f"商品表判定エラー: {e}")
            return True  # エラー時は全て処理
    
    def _get_cell_content(self, table, row_idx: int, col_idx: int) -> Optional[str]:
        """指定セルの内容を取得"""
        for cell in table.cells:
            if cell.row_index == row_idx and cell.column_index == col_idx:
                return cell.content
        return None

# サービスインスタンス
document_intelligence_service = DocumentIntelligenceService()