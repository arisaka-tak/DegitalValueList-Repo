import unicodedata

def normalize_product_name(text):
    """商品名正規化関数"""
    if not text:
        return text
    
    result = []
    for char in text:
        # 全角英数字を半角に変換
        if '！' <= char <= '～':
            result.append(chr(ord(char) - 0xFEE0))
        # 半角カタカナを全角に変換
        elif 'ｦ' <= char <= 'ﾟ':
            result.append(unicodedata.normalize('NFKC', char))
        # 全角記号を半角に変換（ひらがな、カタカナ、英字、数字以外）
        elif not ('あ' <= char <= 'ん' or 'ア' <= char <= 'ン' or 'A' <= char <= 'Z' or 'a' <= char <= 'z' or '0' <= char <= '9'):
            # 全角記号の場合は半角に変換を試行
            normalized = unicodedata.normalize('NFKC', char)
            if len(normalized) == 1 and ord(normalized) < 128:  # ASCII範囲の半角文字
                result.append(normalized)
            else:
                result.append(char)  # 変換できない場合はそのまま
        else:
            result.append(char)
    
    return ''.join(result)