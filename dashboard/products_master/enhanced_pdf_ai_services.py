"""
改良版PDF処理とAI抽出サービス
GPT-4 Vision API + Document Intelligence対応
"""
import base64
import io
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

class EnhancedPDFAIService:
    """改良版PDF処理・AI抽出サービス"""
    
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION
        )
    
    def extract_with_vision_api(self, pdf_file: UploadedFile) -> List[Dict[str, str]]:
        """GPT-4 Vision APIを使用した高精度抽出"""
        try:
            # PDFを画像に変換
            images = self._convert_pdf_to_images(pdf_file)
            
            all_entities = []
            
            for i, image in enumerate(images):
                # 画像をBase64エンコード
                base64_image = self._image_to_base64(image)
                
                # Vision APIで解析
                response = self.client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """この価格表画像から商品名と価格を抽出してJSON形式で出力してください。
                                    
                                    出力形式：
                                    {
                                      "products": [
                                        {"name": "商品名", "price": "価格（数値のみ）"}
                                      ]
                                    }
                                    
                                    注意：
                                    - 表の構造を正確に読み取ってください
                                    - 価格は数値のみ（カンマ・円マーク除去）
                                    - 不明確な情報は除外してください"""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.1
                )
                
                # レスポンス解析
                response_text = response.choices[0].message.content
                try:
                    import json
                    result = json.loads(response_text)
                    page_entities = result.get('products', [])
                    all_entities.extend(page_entities)
                except json.JSONDecodeError:
                    print(f"Page {i+1}: JSON解析エラー")
                    continue
            
            return self._deduplicate_entities(all_entities)
            
        except Exception as e:
            raise Exception(f"Vision API処理エラー: {str(e)}")
    
    def _convert_pdf_to_images(self, pdf_file: UploadedFile) -> List[Image.Image]:
        """PDFを画像リストに変換"""
        pdf_file.seek(0)
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        images = []
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # 高解像度で画像化（300 DPI）
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            
            # PIL Imageに変換
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            images.append(image)
        
        pdf_document.close()
        return images
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """画像をBase64エンコード"""
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    def _deduplicate_entities(self, entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """重複エンティティの除去"""
        seen = set()
        unique_entities = []
        
        for entity in entities:
            name = entity.get('name', '').strip()
            price = entity.get('price', '').strip()
            
            if not name or not price:
                continue
            
            # 商品名の正規化（空白・記号統一）
            normalized_name = ''.join(name.split()).lower()
            key = (normalized_name, price)
            
            if key not in seen:
                seen.add(key)
                unique_entities.append({
                    'name': name,
                    'price': ''.join(filter(str.isdigit, price))  # 数値のみ抽出
                })
        
        return unique_entities

# サービスインスタンス
enhanced_pdf_ai_service = EnhancedPDFAIService()