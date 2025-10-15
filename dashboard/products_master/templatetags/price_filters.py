from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def calc_kenren_price(wholesale_price, gross_margin_rate):
    """仕切価格と粗利率から県連価格を計算"""
    try:
        if wholesale_price and gross_margin_rate:
            # 数値でない場合（都度見積等）はNoneを返す
            try:
                wholesale = float(str(wholesale_price).replace(',', ''))
            except (ValueError, AttributeError):
                return None
            
            margin = float(str(gross_margin_rate))
            return int(wholesale * margin)
    except (ValueError, TypeError, Exception):
        pass
    return None

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