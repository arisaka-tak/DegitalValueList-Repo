"""
AI処理専用スクリプト（シンプル版）
Document Intelligence結果JSONファイルからAI解析のみ実行
"""
import os
import sys
import json
import pickle
import django
from typing import List, Dict, Optional

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
                print(f"プロキシを使用: {proxy_url}")
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
                print("プロキシなしで接続")
                client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version="2024-08-01-preview"
                )
            
            print("✓ Azure OpenAI クライアント初期化成功")
            return client
            
        except Exception as e:
            print(f"✗ Azure OpenAI 初期化エラー: {e}")
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
            print(f"AI解析エラー: {e}")
            return None, None, None, None, None

def process_tables_with_ai(input_path: str = None, output_path: str = None):
    """Document Intelligence結果をAIで処理"""
    if input_path is None:
        input_path = os.path.join(os.path.dirname(__file__), "di_result.pkl")
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "ai_results.json")
    
    if not os.path.exists(input_path):
        print(f"入力ファイルが見つかりません: {input_path}")
        return
    
    print("AI処理開始...")
    
    with open(input_path, 'rb') as f:
        result = pickle.load(f)
    
    print(f"処理対象: {len(result.tables)}個の表")
    
    analyzer = AITableAnalyzer()
    extracted_products = []
    
    for i, table in enumerate(result.tables):
        table_id = i + 1
        print(f"\n=== 表 {table_id}: {table.row_count}行 x {table.column_count}列 ===")
        
        # 表データを2次元配列に変換
        table_matrix = [["" for _ in range(table.column_count)] 
                       for _ in range(table.row_count)]
        
        for cell in table.cells:
            table_matrix[cell.row_index][cell.column_index] = cell.content or ""
        
        # 表内容表示
        for row_idx in range(min(table.row_count, 10)):
            print(f"  行{row_idx}: {table_matrix[row_idx]}")
        
        # AI解析実行
        try:
            analysis_result = analyzer.analyze_table_structure(table_matrix)
            if analysis_result[0] is None:
                continue
            
            header_row, product_col, price_col, model_col, spec_col = analysis_result
            
            print(f"  ヘッダー行: {header_row}")
            print(f"  商品名列: {product_col}")
            print(f"  価格列: {price_col}")
            print(f"  型式列: {model_col}")
            print(f"  規格列: {spec_col}")
            
            if product_col is None or price_col is None:
                print("  -> 商品名または価格列が見つかりません")
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
                        print(debug_info)
        
        except Exception as e:
            print(f"  -> エラー: {e}")
            continue
    
    # 結果保存
    result_data = {
        'source_file': input_path,
        'processed_tables': len(result.tables),
        'extracted_products_count': len(extracted_products),
        'products': extracted_products
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 最終結果 ===")
    print(f"抽出商品: {len(extracted_products)} 件")
    for i, product in enumerate(extracted_products, 1):
        print(f"{i:2d}. 商品名: {product['name']}")
        print(f"    価格: {product['price']} 円")
        if 'model' in product:
            print(f"    型式: {product['model']}")
        if 'spec' in product:
            print(f"    規格: {product['spec']}")
        print(f"    (表{product['table_id']}から抽出)")
        print()
    
    print(f"✓ 処理完了: 結果を {output_path} に保存しました")
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