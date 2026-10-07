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
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Django設定
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.append(project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "digital_pricelist_system.settings")
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
                    http_client = httpx.Client(
                        proxies={"http": proxy_url, "https": proxy_url}
                    )

                client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version="2024-08-01-preview",
                    http_client=http_client,
                )
            else:
                logger.info("プロキシなしで接続")
                client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version="2024-08-01-preview",
                )

            logger.info("✓ Azure OpenAI クライアント初期化成功")
            return client

        except Exception as e:
            logger.error(f"✗ Azure OpenAI 初期化エラー: {e}")
            return None

    def is_price_table(self, table_data: List[List[str]]) -> bool:
        """テーブルが価格表かどうかを判定"""
        if self.openai_client is None:
            return False

        try:
            sample_data = table_data[: min(5, len(table_data))]

            schema = {
                "type": "object",
                "properties": {
                    "is_price_table": {
                        "type": "boolean",
                        "description": "この表が商品価格表かどうか",
                    },
                    "reason": {"type": "string", "description": "判定理由"},
                },
                "required": ["is_price_table", "reason"],
                "additionalProperties": False,
            }

            prompt = f"""
以下の表データが商品価格表かどうかを判定してください。

表データ:
{sample_data}

商品価格表の特徴:
- 商品名、型式、価格などの列がある
- 複数の商品が行として並んでいる
- 価格情報（仕切価格、小売価格など）が含まれる

価格表ではない例:
- 件名と内容のみの表
- 連絡先情報の表
- 有効期限などの単純な情報表
- 2列で項目名と値のペアの表
"""

            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは表の種類を判定する専門家です。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "table_classification",
                        "schema": schema,
                        "strict": True,
                    },
                },
            )

            result = json.loads(response.choices[0].message.content)
            logger.info(
                f"  価格表判定: {result['is_price_table']} - {result['reason']}"
            )
            return result["is_price_table"]

        except Exception as e:
            logger.error(f"価格表判定エラー: {e}")
            return False

    def analyze_table_structure(self, table_data: List[List[str]]) -> tuple:
        """表構造をAIで解析"""
        if self.openai_client is None:
            return None, None, None, None, None, None, None, None, None

        try:
            sample_data = table_data[: min(10, len(table_data))]

            schema = {
                "type": "object",
                "properties": {
                    "header_row": {
                        "type": "integer",
                        "description": "ヘッダー行のインデックス(0から開始)",
                    },
                    "product_column": {
                        "type": "integer",
                        "description": "商品名列のインデックス(0から開始)",
                    },
                    "price_column": {
                        "type": "integer",
                        "description": "仕切価格列のインデックス(0から開始)",
                    },
                    "retail_price_column": {
                        "type": ["integer", "null"],
                        "description": "標準小売価格列のインデックス(0から開始)、ない場合はnull",
                    },
                    "kenren_price_column": {
                        "type": ["integer", "null"],
                        "description": "県連価格列のインデックス(0から開始)、ない場合はnull",
                    },
                    "shipping_fee_column": {
                        "type": ["integer", "null"],
                        "description": "送料列のインデックス(0から開始)、ない場合はnull",
                    },
                    "gross_margin_column": {
                        "type": ["integer", "null"],
                        "description": "粗利率列のインデックス(0から開始)、ない場合はnull",
                    },
                    "model_column": {
                        "type": ["integer", "null"],
                        "description": "型式列のインデックス(0から開始)、ない場合はnull",
                    },
                    "spec_column": {
                        "type": ["integer", "null"],
                        "description": "規格列のインデックス(0から開始)、ない場合はnull",
                    },
                },
                "required": [
                    "header_row",
                    "product_column",
                    "price_column",
                    "retail_price_column",
                    "kenren_price_column",
                    "shipping_fee_column",
                    "gross_margin_column",
                    "model_column",
                    "spec_column",
                ],
                "additionalProperties": False,
            }

            prompt = f"""
この商品価格表のヘッダー行と各列を特定してください。

表データ:
{sample_data}

各列の特徴:
- 商品名列: 「商品」「品名」「製品」などを含む列
- 仕切価格列: 「仕切価格」「新価格」「改定後」などを含む列
- 標準小売価格列: 「標準小売価格」「小売価格」「定価」などを含む列（ない場合はnull）
- 県連価格列: 「県連価格」「県連」などを含む列（ない場合はnull）
- 送料列: 「送料」「運賃」などを含む列（ない場合はnull）
- 粗利率列: 「粗利率」「利益率」などを含む列（ない場合はnull）
- 型式列: 「コード」「型式」などを含む列（ない場合はnull）
- 規格列: 「仕様」「規格」などを含む列（ない場合はnull）
"""

            response = self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは商品仕入価格変更通知書の解析専門家です。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "table_structure_analysis",
                        "schema": schema,
                        "strict": True,
                    },
                },
            )

            result = json.loads(response.choices[0].message.content)
            return (
                result["header_row"],
                result["product_column"],
                result["price_column"],
                result["retail_price_column"],
                result["kenren_price_column"],
                result["shipping_fee_column"],
                result["gross_margin_column"],
                result["model_column"],
                result["spec_column"],
            )

        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
            return None, None, None, None, None, None, None, None, None

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
                        "description": "通知の送信元の会社名のみ（㈱、株式会社、部署名、特品部などは除外）",
                    },
                    "reason": {
                        "type": ["string", "null"],
                        "description": "価格変更の理由を20文字以内で『～のため』で終わる短文に要約",
                    },
                },
                "required": ["sender", "reason"],
                "additionalProperties": False,
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
                    {
                        "role": "system",
                        "content": "あなたは文書解析の専門家です。正確に情報を抽出してください。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "document_metadata",
                        "schema": schema,
                        "strict": True,
                    },
                },
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
                                "name": {"type": "string", "description": "商品名"},
                                "price": {
                                    "type": "string",
                                    "description": "仕切価格（数字のみ）",
                                },
                                "retail_price": {
                                    "type": ["string", "null"],
                                    "description": "標準小売価格（数字のみ、ない場合はnull）",
                                },
                                "kenren_price": {
                                    "type": ["string", "null"],
                                    "description": "県連価格（数字のみ、ない場合はnull）",
                                },
                                "shipping_fee": {
                                    "type": ["string", "null"],
                                    "description": "送料（数字のみ、ない場合はnull）",
                                },
                                "gross_margin": {
                                    "type": ["string", "null"],
                                    "description": "粗利率（数字のみ、ない場合はnull）",
                                },
                                "model": {
                                    "type": ["string", "null"],
                                    "description": "型式・コード（ある場合のみ）",
                                },
                                "spec": {
                                    "type": ["string", "null"],
                                    "description": "規格・仕様（ある場合のみ）",
                                },
                            },
                            "required": [
                                "name",
                                "price",
                                "retail_price",
                                "kenren_price",
                                "shipping_fee",
                                "gross_margin",
                                "model",
                                "spec",
                            ],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["products"],
                "additionalProperties": False,
            }

            prompt = f"""
以下の文書から商品価格情報を抽出してください。

文書内容:
{text[:4000]}...

抽出条件:
- 商品名が明記されているもの（価格がなくても可）
- 仕切価格は改定後・新価格・変更後の価格を優先
- 標準小売価格・県連価格・送料・粗利率がある場合は抽出（ない場合はnull）
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
                    {
                        "role": "system",
                        "content": "あなたは商品価格抽出の専門家です。文章から正確に商品名と価格を抽出してください。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "text_product_extraction",
                        "schema": schema,
                        "strict": True,
                    },
                },
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

    with open(input_path, "rb") as f:
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
        table_matrix = [
            ["" for _ in range(table.column_count)] for _ in range(table.row_count)
        ]

        for cell in table.cells:
            table_matrix[cell.row_index][cell.column_index] = cell.content or ""

        # ヘッダー行の内容を表示
        if table.row_count > 0:
            header_content = table_matrix[0] if table.row_count > 0 else []
            logger.info(f"  検出ヘッダー行: {header_content}")

        # 価格表かどうかを先に判定
        if not analyzer.is_price_table(table_matrix):
            logger.info("  -> 価格表ではないためスキップ")
            continue

        # AI解析実行（価格表と確認済み）
        try:
            analysis_result = analyzer.analyze_table_structure(table_matrix)
            if analysis_result[0] is None:
                continue

            (
                header_row,
                product_col,
                price_col,
                retail_price_col,
                kenren_price_col,
                shipping_fee_col,
                gross_margin_col,
                model_col,
                spec_col,
            ) = analysis_result

            # ヘッダー行とカラム認識結果を詳細表示
            logger.info(f"  AI認識結果:")
            logger.info(f"    ヘッダー行インデックス: {header_row}")
            if header_row < len(table_matrix):
                logger.info(f"    ヘッダー行内容: {table_matrix[header_row]}")

            # 各カラムの認識結果を表示
            if (
                product_col is not None
                and header_row < len(table_matrix)
                and product_col < len(table_matrix[header_row])
            ):
                logger.info(
                    f"    品名カラム[{product_col}]: '{table_matrix[header_row][product_col]}'"
                )
            if (
                price_col is not None
                and header_row < len(table_matrix)
                and price_col < len(table_matrix[header_row])
            ):
                logger.info(
                    f"    仕切価格カラム[{price_col}]: '{table_matrix[header_row][price_col]}'"
                )
            if (
                retail_price_col is not None
                and header_row < len(table_matrix)
                and retail_price_col < len(table_matrix[header_row])
            ):
                logger.info(
                    f"    標準小売価格カラム[{retail_price_col}]: '{table_matrix[header_row][retail_price_col]}'"
                )

            # --- 以下の今回追加した列のログも追記 -----------------
            if (
                kenren_price_col is not None
                and header_row < len(table_matrix)
                and kenren_price_col < len(table_matrix[header_row])
            ):
                logger.info(
                    f"    県連価格カラム[{kenren_price_col}]: '{table_matrix[header_row][kenren_price_col]}'"
                )
            if (
                shipping_fee_col is not None
                and header_row < len(table_matrix)
                and shipping_fee_col < len(table_matrix[header_row])
            ):
                logger.info(
                    f"    送料カラム[{shipping_fee_col}]: '{table_matrix[header_row][shipping_fee_col]}'"
                )
            if (
                gross_margin_col is not None
                and header_row < len(table_matrix)
                and gross_margin_col < len(table_matrix[header_row])
            ):
                logger.info(
                    f"    粗利率カラム[{gross_margin_col}]: '{table_matrix[header_row][gross_margin_col]}'"
                )
            # ----------------------------------------------------

            if (
                model_col is not None
                and header_row < len(table_matrix)
                and model_col < len(table_matrix[header_row])
            ):
                logger.info(
                    f"    型式カラム[{model_col}]: '{table_matrix[header_row][model_col]}'"
                )
            if (
                spec_col is not None
                and header_row < len(table_matrix)
                and spec_col < len(table_matrix[header_row])
            ):
                logger.info(
                    f"    規格カラム[{spec_col}]: '{table_matrix[header_row][spec_col]}'"
                )

            if product_col is None or price_col is None:
                logger.warning("  -> 商品名または価格列が見つかりません（スキップ）")
                continue

            # ヘッダー行以降のデータ行を直接処理
            for row_idx in range(header_row + 1, table.row_count):
                product_name = (
                    table_matrix[row_idx][product_col]
                    if product_col < len(table_matrix[row_idx])
                    else ""
                )
                price_value = (
                    table_matrix[row_idx][price_col]
                    if price_col < len(table_matrix[row_idx])
                    else ""
                )
                retail_price_value = (
                    table_matrix[row_idx][retail_price_col]
                    if retail_price_col is not None
                    and retail_price_col < len(table_matrix[row_idx])
                    else ""
                )
                kenren_price_value = (
                    table_matrix[row_idx][kenren_price_col]
                    if kenren_price_col is not None
                    and kenren_price_col < len(table_matrix[row_idx])
                    else ""
                )
                shipping_fee_value = (
                    table_matrix[row_idx][shipping_fee_col]
                    if shipping_fee_col is not None
                    and shipping_fee_col < len(table_matrix[row_idx])
                    else ""
                )
                gross_margin_value = (
                    table_matrix[row_idx][gross_margin_col]
                    if gross_margin_col is not None
                    and gross_margin_col < len(table_matrix[row_idx])
                    else ""
                )
                model_value = (
                    table_matrix[row_idx][model_col]
                    if model_col is not None and model_col < len(table_matrix[row_idx])
                    else ""
                )
                spec_value = (
                    table_matrix[row_idx][spec_col]
                    if spec_col is not None and spec_col < len(table_matrix[row_idx])
                    else ""
                )

                if product_name.strip() and price_value.strip():
                    clean_price = "".join(filter(str.isdigit, price_value))
                    clean_retail_price = (
                        "".join(filter(str.isdigit, retail_price_value))
                        if retail_price_value.strip()
                        else None
                    )
                    clean_kenren_price = (
                        "".join(filter(str.isdigit, kenren_price_value))
                        if kenren_price_value.strip()
                        else None
                    )
                    clean_shipping_fee = (
                        "".join(filter(str.isdigit, shipping_fee_value))
                        if shipping_fee_value.strip()
                        else None
                    )
                    clean_gross_margin = (
                        "".join(filter(str.isdigit, gross_margin_value))
                        if gross_margin_value.strip()
                        else None
                    )

                    if clean_price:
                        product_data = {
                            "table_id": table_id,
                            "name": product_name.strip(),
                            "price": clean_price,
                        }
                        if clean_retail_price:
                            product_data["retail_price"] = clean_retail_price
                        if clean_kenren_price:
                            product_data["kenren_price"] = clean_kenren_price
                        if clean_shipping_fee:
                            product_data["shipping_fee"] = clean_shipping_fee
                        if clean_gross_margin:
                            product_data["gross_margin"] = clean_gross_margin
                        if model_value:
                            product_data["model"] = model_value.strip()
                        if spec_value:
                            product_data["spec"] = spec_value.strip()

                        extracted_products.append(product_data)

                        debug_info = (
                            f"  -> 抽出: {product_name.strip()} = 仕切{clean_price}円"
                        )
                        if clean_retail_price:
                            debug_info += f", 小売{clean_retail_price}円"
                        if clean_kenren_price:
                            debug_info += f", 県連{clean_kenren_price}円"
                        if clean_shipping_fee:
                            debug_info += f", 送料{clean_shipping_fee}円"
                        if clean_gross_margin:
                            debug_info += f", 粗利率{clean_gross_margin}"
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

        if all_text.strip():
            try:
                text_products = analyzer.extract_products_from_text(all_text)
                if text_products:
                    for product in text_products:
                        product["table_id"] = "text"
                        extracted_products.append(product)
            except Exception as e:
                logger.error(f"段落抽出エラー: {e}")

    # 結果保存
    result_data = {
        "source_file": input_path,
        "document_metadata": document_metadata,
        "processed_tables": len(result.tables),
        "extracted_products_count": len(extracted_products),
        "products": extracted_products,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    logger.info(f"最終結果")
    logger.info(f"抽出商品: {len(extracted_products)} 件")
    for i, product in enumerate(extracted_products, 1):
        logger.info(f"{i:2d}. 商品名: {product['name']}")
        logger.info(f"    仕切価格: {product['price']} 円")
        if "retail_price" in product:
            logger.info(f"    標準小売価格: {product['retail_price']} 円")
        if "kenren_price" in product:
            logger.info(f"    県連価格: {product['kenren_price']} 円")
        if "shipping_fee" in product:
            logger.info(f"    送料: {product['shipping_fee']} 円")
        if "gross_margin" in product:
            logger.info(f"    粗利率: {product['gross_margin']}")
        if "model" in product:
            logger.info(f"    型式: {product['model']}")
        if "spec" in product:
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
