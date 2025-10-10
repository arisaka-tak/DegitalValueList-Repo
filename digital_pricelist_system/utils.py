"""
システム共通ユーティリティ関数
"""
import os
import socket
import getpass

def get_current_user():
    """
    現在のOSユーザとホスト名を取得
    Returns:
        str: username@hostname形式の文字列
    """
    try:
        username = getpass.getuser()
        hostname = socket.gethostname()
        return f"{username}@{hostname}"
    except Exception as e:
        print(f"ユーザ情報取得エラー: {e}")
        return "unknown@unknown"

def parse_user_info(user_string):
    """
    username@hostname形式の文字列を分解
    Args:
        user_string (str): username@hostname形式の文字列
    Returns:
        tuple: (username, hostname)
    """
    if '@' in user_string:
        username, hostname = user_string.split('@', 1)
        return username, hostname
    else:
        return user_string, "unknown"