"""
AI処理専用スクリプト
Document Intelligence結果JSONファイルからAI解析のみ実行
"""
import os
import sys
import json
import pickle
import django
from typing import List, Dict, Optional

# Django設定
# pdf_processing/process_ai_only.py から プロジェクトルートへのパス
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from openai import AzureOpenAI
import httpx

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
            # プロキシ設定を取得
            proxy_url = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
            
            if proxy_url:
                http_client = httpx.Client(proxies=proxy_url)
                client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version="2024-08-01-preview",
                    http_client=http_client
                )
            else:
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
    
    def is_product_price_table(self, table_data: List[List[str]]) -> bool:
        """商品価格表かどうかをGPTで判定"""
        if self.openai_client is None:
            return True
        
        try:
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
                temperature=0,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower()
            return result == "true"
            
        except Exception as e:
            print(f"商品表判定エラー: {e}")
            return True
    
    def analyze_table_structure(self, table_data: List[List[str]]) -> tuple:
        """表構造をAIで解析"""
        if self.openai_client is None:
            return None, None, None, None, None
        
        try:
            # 商品価格表判定
            if not self.is_product_price_table(table_data):
                print("  -> 商品価格表ではないと判定")
                return None, None, None, None, None
            
            # 表全体を解析（最初の10行または全体）
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
- この表には複数の商品カテゴリが含まれている可能性があります
- 最初のヘッダー行（行0または行4など）を特定してください
- 商品名列: 「商品」「品名」「製品」などを含む列
- 価格列: 「仕切価格」「新価格」「改定後」などを含む列
- 型式列: 「コード」「型式」などを含む列（ない場合はnull）
- 規格列: 「仕様」「規格」などを含む列（ない場合はnull）
"""
            
            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "あなたは商品仕入価格変更通知書の解析専門家です。改定後の仕入価格のみを正確に特定してください。"},
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
            raise Exception(f"Azure OpenAI解析失敗: {e}")
    
    def detect_table_sections(self, table_data: List[List[str]], row_types: List[str]) -> List[dict]:
        """表内のセクションを検出し、各セクションの構造タイプを判定"""
        sections = []
        current_section = None
        
        for i, (row, row_type) in enumerate(zip(table_data, row_types)):
            if row_type == "header":
                # 新しいセクションの開始
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    "header_row": i,
                    "header_content": row,
                    "data_rows": [],
                    "structure_type": None
                }
            elif row_type == "data" and current_section:
                current_section["data_rows"].append({"row_index": i, "content": row})
        
        # 最後のセクションを追加
        if current_section:
            sections.append(current_section)
        
        # 各セクションの構造タイプを判定
        for section in sections:
            section["structure_type"] = self._detect_structure_type(section)
        
        return sections
    
    def _detect_structure_type(self, section: dict) -> str:
        """セクションの構造タイプをAIで判定"""
        if not section["data_rows"] or self.openai_client is None:
            return "unknown"
        
        try:
            # サンプルデータを作成
            header_content = section["header_content"]
            sample_data_rows = section["data_rows"][:3]  # 最初の3行のみ
            
            schema = {
                "type": "object",
                "properties": {
                    "structure_type": {
                        "type": "string",
                        "enum": ["product_in_row", "product_in_header"],
                        "description": "表の構造タイプ"
                    }
                },
                "required": ["structure_type"],
                "additionalProperties": False
            }
            
            prompt = f"""
以下の表セクションの構造タイプを判定してください。

ヘッダー行:
{header_content}

データ行（サンプル）:
{[row['content'] for row in sample_data_rows]}

判定基準:
- product_in_row: データ行に商品名と価格があるパターン
  特徴: ヘッダーに列名があり、データ行に具体的な商品名と価格が記載されている

- product_in_header: ヘッダーに商品名、データ行に仕様や型式があるパターン
  特徴: ヘッダーに商品名やカテゴリ名があり、データ行には型式やサイズなどの仕様情報が記載されている

注意: ヘッダーが複数行にわたる場合（縦結合ヘッダー）は発生する可能性があります。
"""
            
            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "あなたは表構造解析の専門家です。表の構造パターンを正確に判定してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structure_type_detection",
                        "schema": schema,
                        "strict": True
                    }
                }
            )
            
            result = json.loads(response.choices[0].message.content)
            return result["structure_type"]
            
        except Exception as e:
            print(f"構造タイプ判定エラー: {e}")
            # フォールバック: プログラムロジックで判定
            has_price_in_data = False
            for data_row in section["data_rows"]:
                for cell in data_row["content"]:
                    if any(c.isdigit() for c in cell) and ("," in cell or len([c for c in cell if c.isdigit()]) > 3):
                        has_price_in_data = True
                        break
            return "product_in_row" if has_price_in_data else "product_in_header"
    
    def classify_table_rows(self, table_data: List[List[str]]) -> List[str]:
        """各行がヘッダーかデータかをAIで判定（20行ずつ処理）"""
        if self.openai_client is None:
            return ["data"] * len(table_data)
        
        all_row_types = []
        chunk_size = 20
        
        for start_idx in range(0, len(table_data), chunk_size):
            end_idx = min(start_idx + chunk_size, len(table_data))
            chunk_data = table_data[start_idx:end_idx]
            
            try:
                schema = {
                    "type": "object",
                    "properties": {
                        "row_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["header", "data", "empty"]
                            },
                            "description": "各行の種類を順番に配列で返す"
                        }
                    },
                    "required": ["row_types"],
                    "additionalProperties": False
                }
                
                prompt = f"""
以下の表データの各行が「ヘッダー」「データ」「空行」のどれかを判定してください。

表データ（行{start_idx}から行{end_idx-1}まで）:
{chunk_data}

判定基準:
- header: 列名、カテゴリ名、またはその補足説明が含まれる行
- data: 商品情報や価格データが含まれる行
- empty: 空欄または空白の行

注意: 
- 価格がある場合はdataです
- 括弧で囲まれた補足説明もheaderです
"""
                
                response = self.openai_client.chat.completions.create(
                    model=AZURE_OPENAI_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": "あなたは表構造解析の専門家です。各行を正確に分類してください。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "row_classification",
                            "schema": schema,
                            "strict": True
                        }
                    }
                )
                
                result = json.loads(response.choices[0].message.content)
                chunk_types = result["row_types"]
                all_row_types.extend(chunk_types)
                
            except Exception as e:
                print(f"行分類エラー (行{start_idx}-{end_idx-1}): {e}")
                # エラー時はデフォルトでdataとして扱う
                all_row_types.extend(["data"] * len(chunk_data))
        
        return all_row_types
    
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
            print(f"文書メタデータ抽出エラー: {e}")
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
            print(f"文章商品抽出エラー: {e}")
            return []

def process_tables_with_ai(input_path: str = None, output_path: str = None):
    """Document Intelligence結果をAIで処理"""
    if input_path is None:
        input_path = os.path.join(os.path.dirname(__file__), "di_result.pkl")
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "ai_results.json")
    """Document Intelligence結果をAIで処理"""
    
    if not os.path.exists(input_path):
        print(f"入力ファイルが見つかりません: {input_path}")
        print("先に extract_di_only.py を実行してください。")
        return
    
    print("AI処理開始...")
    print(f"入力ファイル: {input_path}")
    print(f"出力ファイル: {output_path}")
    
    # pickleファイル読み込み
    with open(input_path, 'rb') as f:
        result = pickle.load(f)
    
    print(f"処理対象: {len(result.tables)}個の表")
    print(f"パラグラフ数: {len(result.paragraphs)}個")
    
    analyzer = AITableAnalyzer()
    
    # 文書全体からメタデータを抽出
    print("\n=== 文書メタデータ抽出 ===")
    all_text = " ".join([p.content for p in result.paragraphs if p.content])
    document_metadata = analyzer.extract_document_metadata(all_text)
    
    print(f"通知の送信元: {document_metadata.get('sender', '未検出')}")
    print(f"価格変更理由: {document_metadata.get('reason', '未検出')}")
    
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
            
            # 型式列と規格列が商品名列と同じ場合は無効化
            if model_col == product_col:
                model_col = None
            if spec_col == product_col:
                spec_col = None
            
            # 各行の種類を判定して表示
            print("  行別判定(AI - 20行ずつ):")
            row_types = analyzer.classify_table_rows(table_matrix)
            for row_idx in range(table.row_count):
                row_type = row_types[row_idx] if row_idx < len(row_types) else "data"
                type_name = {"header": "ヘッダー", "data": "データ", "empty": "空行"}.get(row_type, "データ")
                print(f"    行{row_idx}: {type_name} - {table_matrix[row_idx][:3]}...")
            
            # セクション別に処理
            sections = analyzer.detect_table_sections(table_matrix, row_types)
            print(f"  検出されたセクション: {len(sections)}個")
            
            for section_idx, section in enumerate(sections):
                print(f"  セクション{section_idx + 1}: 行{section['header_row']} - 構造タイプ: {section['structure_type']}")
                
                if section['structure_type'] == 'product_in_row':
                    # 明細行に商品名と価格があるパターン
                    for data_row in section['data_rows']:
                        row_idx = data_row['row_index']
                        product_name = table_matrix[row_idx][product_col] if product_col < len(table_matrix[row_idx]) else ""
                        price_value = table_matrix[row_idx][price_col] if price_col < len(table_matrix[row_idx]) else ""
                        model_value = table_matrix[row_idx][model_col] if model_col is not None and model_col < len(table_matrix[row_idx]) else ""
                        spec_value = table_matrix[row_idx][spec_col] if spec_col is not None and spec_col < len(table_matrix[row_idx]) else ""
                        
                        if product_name.strip() and price_value.strip():
                            # 販売終了を示す文言をチェック
                            discontinue_keywords = ['終売', '販売終了', '廃番', '取扱終了', '生産終了', '製造終了']
                            is_discontinued = any(keyword in price_value for keyword in discontinue_keywords)
                            
                            if is_discontinued:
                                clean_price = '0'
                            else:
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
                                
                                debug_info = f"  -> 抽出(明細型): {product_name.strip()} = {clean_price}円"
                                if model_value:
                                    debug_info += f", 型式: {model_value.strip()}"
                                if spec_value:
                                    debug_info += f", 規格: {spec_value.strip()}"
                                print(debug_info)
                
                elif section['structure_type'] == 'product_in_header':
                    # ヘッダーに商品名、明細に仕様があるパターン
                    header_content = section['header_content']
                    base_product_name = header_content[0] if header_content else ""
                    
                    # 複数ヘッダーの場合、続くヘッダー行を結合
                    combined_header = base_product_name
                    if section_idx + 1 < len(sections):
                        next_section = sections[section_idx + 1]
                        if (next_section['structure_type'] == 'unknown' and 
                            next_section['header_row'] == section['header_row'] + 1):
                            # 続くヘッダーを結合
                            next_header = next_section['header_content'][0] if next_section['header_content'] else ""
                            if next_header.strip():
                                combined_header = f"{base_product_name} {next_header}".strip()
                    
                    for data_row in section['data_rows']:
                        row_idx = data_row['row_index']
                        spec_name = table_matrix[row_idx][product_col] if product_col < len(table_matrix[row_idx]) else ""
                        price_value = table_matrix[row_idx][price_col] if price_col < len(table_matrix[row_idx]) else ""
                        
                        if spec_name.strip() and price_value.strip():
                            # 販売終了を示す文言をチェック
                            discontinue_keywords = ['終売', '販売終了', '廃番', '取扱終了', '生産終了', '製造終了']
                            is_discontinued = any(keyword in price_value for keyword in discontinue_keywords)
                            
                            if is_discontinued:
                                clean_price = '0'
                            else:
                                clean_price = ''.join(filter(str.isdigit, price_value))
                            
                            if clean_price:
                                # 結合ヘッダー + 仕様名で商品名を構成
                                full_product_name = f"{combined_header} {spec_name}".strip()
                                
                                product_data = {
                                    'table_id': table_id,
                                    'name': full_product_name,
                                    'price': clean_price,
                                    'base_product': combined_header,
                                    'spec': spec_name
                                }
                                
                                extracted_products.append(product_data)
                                
                                print(f"  -> 抽出(ヘッダー型): {full_product_name} = {clean_price}円")
        
        except Exception as e:
            print(f"  -> エラー: {e}")
            continue
    
    # フォールバック処理: テーブルから商品が抽出できない場合、文章から抽出を試行
    print(f"\n=== フォールバック処理判定 ===")
    print(f"抽出済み商品数: {len(extracted_products)}")
    print(f"パラグラフテキスト長: {len(all_text)}")
    print(f"フォールバック実行条件: {len(extracted_products) == 0 and all_text.strip()}")
    
    if len(extracted_products) == 0 and all_text.strip():
        print("\n=== フォールバック: 文章からの商品抽出開始 ===")
        print(f"\n--- パラグラフ全体内容 ({len(all_text)}文字) ---")
        print(all_text[:2000])  # 最初の2000文字を表示
        if len(all_text) > 2000:
            print("...（以下省略）")
        print("--- パラグラフ内容終了 ---\n")
        
        try:
            text_products = analyzer.extract_products_from_text(all_text)
            print(f"AI抽出結果: {len(text_products) if text_products else 0}件")
            if text_products:
                for product in text_products:
                    product['table_id'] = 'text'  # 文章由来であることを示す
                    extracted_products.append(product)
                    print(f"  -> 抽出(文章): {product['name']} = {product['price']}円")
                print(f"文章から {len(text_products)} 件の商品を抽出しました")
            else:
                print("文章からも商品情報を抽出できませんでした")
        except Exception as e:
            print(f"文章抽出エラー: {e}")
    else:
        print("フォールバック処理はスキップされました")
    
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
    
    # 結果表示
    print(f"\n=== 最終結果 ===")
    print(f"文書情報:")
    print(f"  送信元: {document_metadata.get('sender', '未検出')}")
    print(f"  変更理由: {document_metadata.get('reason', '未検出')}")
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
    
    if len(extracted_products) == 0:
        print("商品データが抽出されませんでした。")
    
    print(f"✓ 処理完了: 結果を {output_path} に保存しました")
    return result_data

def main(input_file=None, output_file=None):
    """メイン関数"""
    # コマンドラインからの実行時のみ sys.argv を使用
    if input_file is None:
        if __name__ == "__main__" and len(sys.argv) > 1:
            input_file = sys.argv[1]
        else:
            input_file = os.path.join(os.path.dirname(__file__), "di_result.pkl")
    
    if output_file is None:
        if __name__ == "__main__" and len(sys.argv) > 2:
            output_file = sys.argv[2]
        else:
            output_file = os.path.join(os.path.dirname(__file__), "ai_results.json")
    
    return process_tables_with_ai(input_file, output_file)

if __name__ == "__main__":
    main()