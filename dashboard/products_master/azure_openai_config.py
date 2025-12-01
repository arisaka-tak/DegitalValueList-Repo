"""
Azure OpenAI API設定
"""
import os
from django.conf import settings

# Azure OpenAI API設定
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', 'https://your-resource.openai.azure.com/')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', 'your-api-key')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')

# プロンプト設定
ENTITY_EXTRACTION_PROMPT = """
以下のPDFテキストから商品名と価格情報を抽出してください。
JSON形式で以下の構造で出力してください：

{
  "products": [
    {
      "name": "商品名",
      "price": "価格（数値のみ）"
    }
  ]
}

注意事項：
- 商品名は正確に抽出してください（「CF F1 10 00」のような英数字の組み合わせも商品名として扱う）
- 価格は数値のみ（カンマや円マークは除く）
- 不明確な情報は除外してください
- 重複する商品は1つにまとめてください
- 品名欄に記載されている全ての値を商品名として認識してください

PDFテキスト：
{pdf_text}
"""