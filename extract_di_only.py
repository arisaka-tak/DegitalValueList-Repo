"""
Document Intelligence 抽出専用スクリプト
PDFから表データを抽出してJSONファイルに保存
"""
import os
import sys
import pickle
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

import traceback

# Document Intelligence設定
DOCUMENT_INTELLIGENCE_ENDPOINT = "https://digital-valuelist-prd.cognitiveservices.azure.com/"
DOCUMENT_INTELLIGENCE_API_KEY = "397a72600d7e45f6b2462d5b99edc38a"

def extract_from_pdf(pdf_path: str, output_path: str = "di_result.pkl"):
    """PDFからDocument Intelligence結果を抽出してpickleファイルに保存"""
    
    if not os.path.exists(pdf_path):
        print(f"PDFファイルが見つかりません: {pdf_path}")
        return
    
    print("Document Intelligence 抽出開始...")
    print(f"入力ファイル: {pdf_path}")
    print(f"出力ファイル: {output_path}")
    
    try:
        # Document Intelligence クライアント初期化
        client = DocumentIntelligenceClient(
            endpoint=DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(DOCUMENT_INTELLIGENCE_API_KEY)
        )
        
        # PDF解析実行
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        print(f"ファイルサイズ: {len(pdf_content)} bytes")
        
        poller = client.begin_analyze_document("prebuilt-layout", pdf_content)
        result = poller.result()
        
        print(f"検出された表数: {len(result.tables)}")
        print(f"検出された段落数: {len(result.paragraphs)}")
        print(f"検出されたページ数: {len(result.pages)}")
        
        # resultオブジェクトをそのままpickleで保存
        with open(output_path, 'wb') as f:
            pickle.dump(result, f)
        
        print(f"✓ 抽出完了: {output_path} に保存しました")
        print(f"  - 表: {len(result.tables)}個")
        print(f"  - 段落: {len(result.paragraphs)}個")
        print(f"  - ページ: {len(result.pages)}個")
        
        # 簡易プレビュー表示
        for i, table in enumerate(result.tables):
            print(f"表 {i+1}: {table.row_count}行 x {table.column_count}列")
        
        print(f"\n最初の5段落:")
        for i, paragraph in enumerate(result.paragraphs[:5]):
            content_preview = paragraph.content[:100] + "..." if len(paragraph.content) > 100 else paragraph.content
            print(f"  {i+1}: {content_preview}")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

        traceback.print_exc()

if __name__ == "__main__":
    # コマンドライン引数でPDFパスを指定可能
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "C:\Project\ZCS_DegitalValueList\イ　イノセント・廃番について.pdf"
    
    # 出力ファイル名も指定可能
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        output_path = "di_result.pkl"
    
    extract_from_pdf(pdf_path, output_path)