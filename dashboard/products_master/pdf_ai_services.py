"""
PDF処理とAzure OpenAI APIを使用したエンティティ抽出サービス
"""
import json
import logging
from typing import Dict, List, Optional, Tuple
import PyPDF2
from openai import AzureOpenAI
from django.core.files.uploadedfile import UploadedFile
from .azure_openai_config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    ENTITY_EXTRACTION_PROMPT
)

logger = logging.getLogger(__name__)

class PDFProcessingError(Exception):
    """PDF処理エラー"""
    pass

class AIExtractionError(Exception):
    """AI抽出エラー"""
    pass

class PDFAIService:
    """PDF処理とAI抽出を行うサービスクラス"""
    
    def __init__(self):
        # Azure OpenAI設定が有効な場合のみクライアントを初期化
        if (AZURE_OPENAI_ENDPOINT != 'https://your-resource.openai.azure.com/' and 
            AZURE_OPENAI_API_KEY != 'your-api-key'):
            self.client = AzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION
            )
        else:
            self.client = None
    
    def extract_text_from_pdf(self, pdf_file: UploadedFile) -> str:
        """PDFファイルからテキストを抽出"""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_content = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text() + "\n"
            
            if not text_content.strip():
                raise PDFProcessingError("PDFからテキストを抽出できませんでした")
            
            logger.info(f"PDF処理完了: {len(text_content)}文字のテキストを抽出")
            return text_content
            
        except Exception as e:
            logger.error(f"PDF処理エラー: {str(e)}")
            raise PDFProcessingError(f"PDF処理中にエラーが発生しました: {str(e)}")
    
    def extract_entities_with_vision(self, pdf_file: UploadedFile) -> List[Dict[str, str]]:
        """visionモデルでPDFから直接エンティティを抽出"""
        if not self.client:
            # テスト用ダミーデータを返す
            logger.info("テストモード: ダミーデータを返します")
            return [
                {"name": "牛用飼料A", "price": "15000"},
                {"name": "豚用ビタミン剤", "price": "8500"},
                {"name": "鶏用配合飼料", "price": "12000"},
                {"name": "牛用ミネラル補給剤", "price": "22000"},
                {"name": "豚用成長促進剤", "price": "18500"}
            ]
        
        # 実際のvisionモデル処理（将来実装）
        # TODO: PDFをbase64エンコードしてvisionモデルに送信
        raise AIExtractionError("visionモデル処理は未実装です")
    
    def extract_entities_with_ai(self, pdf_text: str) -> List[Dict[str, str]]:
        """テキストベースのAI抽出（旧方式・非推奨）"""
        
        try:
            prompt = ENTITY_EXTRACTION_PROMPT.format(pdf_text=pdf_text[:4000])  # トークン制限対応
            
            response = self.client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "あなたは商品情報抽出の専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            logger.info(f"AI応答: {response_text[:200]}...")
            
            # JSON解析
            try:
                result = json.loads(response_text)
                products = result.get('products', [])
                
                if not products:
                    raise AIExtractionError("商品情報が抽出されませんでした")
                
                logger.info(f"AI抽出完了: {len(products)}件の商品を抽出")
                return products
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析エラー: {str(e)}")
                raise AIExtractionError(f"AI応答の解析に失敗しました: {str(e)}")
            
        except Exception as e:
            logger.error(f"AI抽出エラー: {str(e)}")
            raise AIExtractionError(f"AI抽出中にエラーが発生しました: {str(e)}")
    
    def process_pdf_to_entities(self, pdf_file: UploadedFile) -> Tuple[List[Dict[str, str]], str]:
        """PDFファイルを処理してエンティティを抽出（visionモデル用）"""
        try:
            # visionモデルに直接PDFを渡すためテキスト抽出はスキップ
            entities = self.extract_entities_with_vision(pdf_file)
            
            # データ検証・正規化
            validated_entities = self._validate_and_normalize_entities(entities)
            
            return validated_entities, "PDFファイル（visionモデル処理）"
            
        except AIExtractionError as e:
            raise e
        except Exception as e:
            logger.error(f"予期しないエラー: {str(e)}")
            raise AIExtractionError(f"処理中に予期しないエラーが発生しました: {str(e)}")
    
    def _validate_and_normalize_entities(self, entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """抽出されたエンティティの検証と正規化"""
        validated = []
        
        for entity in entities:
            name = entity.get('name', '').strip()
            price = entity.get('price', '').strip()
            
            # 基本検証
            if not name or not price:
                continue
            
            # 価格の正規化（数値のみ抽出）
            normalized_price = ''.join(filter(str.isdigit, price))
            if not normalized_price:
                continue
            
            validated.append({
                'name': name,
                'price': normalized_price
            })
        
        return validated

# サービスインスタンス
pdf_ai_service = PDFAIService()