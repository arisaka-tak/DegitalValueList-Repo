from django import template
from decimal import Decimal
import json

register = template.Library()

@register.filter
def calc_kenren_price(wholesale_price, gross_margin_rate):
    """仕切価格と粗利率から県連価格を計算（新計算方式のみ）"""
    try:
        if wholesale_price and gross_margin_rate:
            try:
                wholesale = float(str(wholesale_price).replace(',', ''))
            except (ValueError, AttributeError):
                return None
            
            margin = float(str(gross_margin_rate))
            if margin > 0:
                # 共通関数で県連価格を計算
                calculated = wholesale / margin
                # 10円単位で四捨五入
                return int(round(calculated / 10) * 10)
    except (ValueError, TypeError, Exception):
        pass
    return None

@register.filter
def format_revision_amount(value):
    """改定額をカンマ区切りでフォーマット"""
    try:
        if value is None or value == '':
            return '-'
        # 数値の場合
        if isinstance(value, (int, float, Decimal)):
            return f"{int(value):,}"
        # 文字列の場合、数値に変換を試行
        try:
            num_value = float(value)
            return f"{int(num_value):,}"
        except (ValueError, TypeError):
            # 数値でない場合はそのまま返す
            return str(value)
    except:
        return str(value) if value else '-'

@register.filter
def format_price(value):
    """価格をカンマ区切りでフォーマット"""
    try:
        if value is None or value == '':
            return '-'
        # 数値の場合
        if isinstance(value, (int, float, Decimal)):
            return f"{int(value):,}"
        # 文字列の場合、数値に変換を試行
        try:
            num_value = float(value)
            return f"{int(num_value):,}"
        except (ValueError, TypeError):
            # 数値でない場合はそのまま返す
            return str(value)
    except:
        return str(value) if value else '-'

@register.filter
def approval_to_json(approval):
    """承認データをJSON形式に変換"""
    try:
        # 畜種、分類、メーカーのIDを取得
        livestock_type_id = ''
        category_id = ''
        manufacturer_id = ''
        
        # 承認データはIDで保存されているのでそのまま使用
        livestock_type_id = approval.livestock_type or ''
        category_id = approval.category or ''
        manufacturer_id = approval.manufacturer or ''
        
        data = {
            'product_number': approval.product_number if hasattr(approval, 'product_number') else None,
            'product_code': approval.product_code or '',
            'livestock_type': livestock_type_id,
            'category': category_id,
            'manufacturer': manufacturer_id,
            'product_name': approval.product_name or '',
            'model_number': approval.model_number or '',
            'specification': approval.specification or '',
            'shipping_unit': approval.shipping_unit or '',
            'shipping_fee': approval.shipping_fee or '',
            'remarks': approval.remarks or '',
        }
        return json.dumps(data)
    except:
        return '{}'

@register.filter
def format_gross_margin_rate(value):
    """粗利率を％表記に変換（新計算方式のみ）"""
    try:
        if value is None or value == '':
            return '-'
        
        margin_rate = float(str(value))
        # 新計算方式：(1 - 粗利率) * 100
        profit_rate = (1 - margin_rate) * 100
        
        return f"{profit_rate:.1f}%"
    except (ValueError, TypeError, Exception):
        return str(value) if value else '-'

@register.filter
def approval_histories_to_json(price_histories):
    """承認価格履歴をJSON形式に変換"""
    try:
        data = []
        for history in price_histories:
            # 県連価格の表示値を計算
            kenren_price_display = history.kenren_price
            if not kenren_price_display:
                calc_price = calc_kenren_price(history.wholesale_price, history.gross_margin_rate)
                if calc_price:
                    kenren_price_display = format_price(calc_price)
                else:
                    kenren_price_display = '都度見積'
            
            data.append({
                'id': history.pk,
                'period_year': history.period_year,
                'effective_year_month': history.effective_year_month,
                'wholesale_price': history.wholesale_price,
                'kenren_price': history.kenren_price,
                'kenren_price_display': kenren_price_display,
                'retail_price': history.retail_price,
                'gross_margin_rate': str(history.gross_margin_rate) if history.gross_margin_rate is not None else None,
                'revision_reason': history.revision_reason or '',
                'memo': history.memo or '',
                'is_delete_request': getattr(history, 'is_delete_request', False),
                'diff_flags': getattr(history, 'diff_flags', {}),
                'is_editable': history.is_editable()  # 実際の編集可能性を使用
            })
        return json.dumps(data)
    except:
        return '[]'