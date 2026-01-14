"""
粗利率計算の共通関数（Python版）
"""
from decimal import Decimal
import math

def calculate_gross_margin_rate(wholesale_price, kenren_price):
    """
    粗利率を計算（仕切価格÷県連価格）
    
    Args:
        wholesale_price (float|int|Decimal): 仕切価格
        kenren_price (float|int|Decimal): 県連価格
    
    Returns:
        Decimal|None: 粗利率（小数点第2位まで切り捨て）
    """
    try:
        wholesale = float(wholesale_price)
        kenren = float(kenren_price)
        
        if kenren > 0:
            margin_rate = wholesale / kenren
            # 小数点第2位まで、3位以下切り捨て
            truncated_rate = math.floor(margin_rate * 100) / 100
            return Decimal(str(truncated_rate))
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return None

def format_gross_margin_rate(margin_rate):
    """
    粗利率を％表示に変換（(1-粗利率)*100）
    
    Args:
        margin_rate (float|Decimal): 粗利率（仕切価格÷県連価格）
    
    Returns:
        str: ％表示（例：10.0%）
    """
    try:
        if margin_rate is not None:
            rate = float(margin_rate)
            # 粗利率 = (1 - 仕切価格÷県連価格) * 100
            profit_rate = (1 - rate) * 100
            return f"{profit_rate:.1f}%"
    except (ValueError, TypeError):
        pass
    return '-'

def calculate_kenren_price(wholesale_price, margin_rate):
    """
    県連価格を計算（仕切価格÷粗利率）
    
    Args:
        wholesale_price (float|int|Decimal): 仕切価格
        margin_rate (float|Decimal): 粗利率
    
    Returns:
        int|None: 県連価格（10円単位四捨五入）
    """
    try:
        wholesale = float(wholesale_price)
        margin = float(margin_rate)
        
        if margin > 0:
            calculated = wholesale / margin
            # 10円単位で四捨五入
            return int(round(calculated / 10) * 10)
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return None