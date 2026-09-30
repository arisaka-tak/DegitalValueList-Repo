"""
共通設定管理モジュール
Django_run.py と batch_ai_extract.py で共通使用する設定パスを定義
"""

from pathlib import Path

# 設定ファイルパス（ハードコード）
# CONFIG_PATH = Path(r"\\128.167.100.10\資材・大家畜事業部\04資材部\★デジタル価格表作成プログラム\config.ini")
CONFIG_PATH = Path(
    r"D:\Task\02_全農畜産サービス\03_デジタル価格表\DegitalValueList-Repo\config.ini"
)
# CONFIG_PATH = Path(r"c:\Project\ZCS_DegitalValueList\c    onfig.ini")
# r"\\zbsfs.local.z-bs.co.jp\920情報共通\各部共通\部間共有【ＩＴ統括-グル関シ部】\畜産サービス\08_【デジタル価格表作成業務効率化検討】\DegitalValueList_Console\config.ini"
