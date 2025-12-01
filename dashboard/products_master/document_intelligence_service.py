"""
Azure Document Intelligence サービス
FAXスキャン画像の構造化データ抽出
"""
import os
from typing import Dict, List, Optional
from django.core.files.uploadedfile import UploadedFile

# Document Intelligence用の設定
DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv('DOCUMENT_INTELLIGENCE_ENDPOINT', '')
DOCUMENT_INTELLIGENCE_API_KEY = os.getenv('DOCUMENT_INTELLIGENCE_API_KEY', '')

class DocumentIntelligenceService:
    """Azure Document Intelligence サービス"""
    
    def __init__(self):
        self.endpoint = DOCUMENT_INTELLIGENCE_ENDPOINT
        self.api_key = DOCUMENT_INTELLIGENCE_API_KEY
        
        if not self.endpoint or not self.api_key:
            print("Warning: Document Intelligence credentials not configured")
    
    def extract_table_data(self, pdf_file: UploadedFile) -> List[Dict[str, str]]:
        """Document Intelligenceで表データを抽出"""
        try:
            # Azure Document Intelligence クライアント初期化
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            
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
                # 表のヘッダー行を特定
                header_row = self._identify_header_row(table)
                product_col, price_col = self._identify_columns(table, header_row)
                
                if product_col is None or price_col is None:
                    continue
                
                # データ行を処理
                for row_idx in range(header_row + 1, table.row_count):
                    product_name = self._get_cell_content(table, row_idx, product_col)
                    price_value = self._get_cell_content(table, row_idx, price_col)
                    
                    if product_name and price_value:
                        # 価格の数値抽出
                        clean_price = ''.join(filter(str.isdigit, price_value))
                        if clean_price:
                            extracted_products.append({
                                'name': product_name.strip(),
                                'price': clean_price
                            })
            
            return extracted_products
            
        except ImportError:
            raise Exception("azure-ai-documentintelligence パッケージがインストールされていません")
        except Exception as e:
            raise Exception(f"Document Intelligence処理エラー: {str(e)}")
    
    def _identify_header_row(self, table) -> int:
        """ヘッダー行を特定"""
        # 最初の行をヘッダーと仮定
        return 0
    
    def _identify_columns(self, table, header_row: int) -> tuple:
        """商品名列と価格列を特定"""
        product_col = None
        price_col = None
        
        for col_idx in range(table.column_count):
            header_text = self._get_cell_content(table, header_row, col_idx)
            if not header_text:
                continue
            
            header_lower = header_text.lower()
            
            # 商品名列の特定
            if any(keyword in header_lower for keyword in ['商品', '品名', '製品', 'product']):
                product_col = col_idx
            
            # 価格列の特定
            if any(keyword in header_lower for keyword in ['価格', '単価', '金額', 'price', '円']):
                price_col = col_idx
        
        return product_col, price_col
    
    def _get_cell_content(self, table, row_idx: int, col_idx: int) -> Optional[str]:
        """指定セルの内容を取得"""
        for cell in table.cells:
            if cell.row_index == row_idx and cell.column_index == col_idx:
                return cell.content
        return None

# サービスインスタンス
document_intelligence_service = DocumentIntelligenceService()