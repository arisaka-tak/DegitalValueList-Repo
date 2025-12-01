"""
FAXスキャン画像PDF専用AI抽出サービス
Azure Document Intelligence + GPT-4 Vision対応
"""
import base64
import io
import json
from typing import Dict, List, Optional, Tuple
from PIL import Image
import fitz  # PyMuPDF
from openai import AzureOpenAI
from django.core.files.uploadedfile import UploadedFile
from .azure_openai_config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION
)

class FaxScanAIService:
    """FAXスキャン画像PDF専用AI抽出サービス"""
    
    def __init__(self):
        self.openai_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION
        )
    
    def extract_from_fax_scan(self, pdf_file: UploadedFile, method: str = "vision") -> List[Dict[str, str]]:
        """FAXスキャン画像から商品情報を抽出"""
        if method == "vision":
            return self._extract_with_vision_only(pdf_file)
        elif method == "document_intelligence":
            return self._extract_with_document_intelligence(pdf_file)
        elif method == "hybrid":
            return self._extract_with_hybrid(pdf_file)
        else:
            raise ValueError("method must be 'vision', 'document_intelligence', or 'hybrid'")
    
    def _extract_with_vision_only(self, pdf_file: UploadedFile) -> List[Dict[str, str]]:
        """GPT-4 Vision APIのみで抽出（シンプル・高精度）"""
        try:
            images = self._convert_pdf_to_images(pdf_file)
            all_entities = []
            
            for i, image in enumerate(images):
                base64_image = self._image_to_base64(image)
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """この画像は価格改定に関する文書です。商品名と価格情報を抽出してJSON形式で出力してください。

出力形式：
{
  "products": [
    {"name": "商品名", "price": "新価格数値"}
  ]
}

抽出ルール：
- 【テーブル形式】表の行から商品名・価格を抽出
- 【お手紙形式】箇条書きや文中の「商品名：価格」を抽出
- 【価格変更】「旧価格→新価格」の場合は新価格を採用
- 価格は数値のみ（カンマ・円マーク・矢印除去）
- 不鮮明・判読困難な情報は除外
- ヘッダー・挨拶文は除外
- 商品名は正確に（型式・規格含む）"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }],
                    max_tokens=3000,
                    temperature=0.0  # 一貫性重視
                )
                
                response_text = response.choices[0].message.content
                try:
                    result = json.loads(response_text)
                    page_entities = result.get('products', [])
                    all_entities.extend(page_entities)
                except json.JSONDecodeError as e:
                    print(f"Page {i+1} JSON解析エラー: {e}")
                    continue
            
            return self._clean_and_deduplicate(all_entities)
            
        except Exception as e:
            raise Exception(f"Vision API抽出エラー: {str(e)}")
    
    def _extract_with_document_intelligence(self, pdf_file: UploadedFile) -> List[Dict[str, str]]:
        """Azure Document Intelligence使用（要追加実装）"""
        # Document Intelligence APIの実装
        # 現在は未実装のためVision APIにフォールバック
        return self._extract_with_vision_only(pdf_file)
    
    def _extract_with_hybrid(self, pdf_file: UploadedFile) -> List[Dict[str, str]]:
        """ハイブリッド方式（Document Intelligence + GPT-4）"""
        # 現在は未実装のためVision APIにフォールバック
        return self._extract_with_vision_only(pdf_file)
    
    def _convert_pdf_to_images(self, pdf_file: UploadedFile) -> List[Image.Image]:
        """PDFを高解像度画像に変換"""
        pdf_file.seek(0)
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        images = []
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # FAXスキャン用高解像度（400 DPI）
            mat = fitz.Matrix(400/72, 400/72)
            pix = page.get_pixmap(matrix=mat)
            
            # PIL Imageに変換
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            
            # 画像前処理（コントラスト向上）
            image = self._enhance_image_for_ocr(image)
            images.append(image)
        
        pdf_document.close()
        return images
    
    def _enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """OCR精度向上のための画像前処理"""
        from PIL import ImageEnhance
        
        # コントラスト強化
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # シャープネス強化
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        return image
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """画像をBase64エンコード"""
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95)  # 高品質
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    def _clean_and_deduplicate(self, entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """データクリーニングと重複除去"""
        seen = set()
        cleaned_entities = []
        
        for entity in entities:
            name = entity.get('name', '').strip()
            price = entity.get('price', '').strip()
            
            if not name or not price:
                continue
            
            # 価格の正規化（矢印・カンマ・円マーク除去）
            # 「4,000円→ 4,200円」の場合は最後の数値を取得
            import re
            price_numbers = re.findall(r'[0-9,]+', price)
            if price_numbers:
                # 最後の数値（新価格）を使用
                clean_price = ''.join(filter(str.isdigit, price_numbers[-1]))
            else:
                clean_price = ''.join(filter(str.isdigit, price))
            
            if not clean_price:
                continue
            
            # 商品名の正規化
            normalized_name = ''.join(name.split()).lower()
            key = (normalized_name, clean_price)
            
            if key not in seen:
                seen.add(key)
                cleaned_entities.append({
                    'name': name,
                    'price': clean_price
                })
        
        return cleaned_entities

# サービスインスタンス
fax_scan_ai_service = FaxScanAIService()