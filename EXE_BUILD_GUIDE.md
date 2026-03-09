# EXEファイル作成ガイド

リリース時に作成する3つのEXEファイルのビルド手順書

---

## 📦 作成するEXEファイル一覧

| EXEファイル名 | 用途 | 更新頻度 | ビルド方法 |
|-------------|------|---------|-----------|
| **DigitalValueList.exe** | メインプログラム（Djangoサーバー） | 毎回 | DigitalValueList.spec |
| **BatchAIExtract.exe** | AI価格抽出バッチツール | 必要時 | BatchAIExtract.spec |
| **デジタル価格表作成プログラム.exe** | バージョンチェッカー（自動更新） | 初回のみ | version_checker.py |

---

## 🔧 事前準備

### 1. 開発環境の確認

```powershell
# 仮想環境の有効化
.venv\Scripts\activate

# Pythonバージョン確認
python --version
# 期待値: Python 3.13.7

# PyInstallerのインストール確認
pip show pyinstaller
# 期待値: Version: 6.19.0
```

### 2. バージョン番号の更新

`version.txt` を編集:

```
v{YYYYMMDD}{NNN}
```

**例:**
- 2025年3月6日の1回目: `v202503060001`
- 2025年3月6日の2回目: `v202503060002`

**ファイルパス:** `ZCS_DegitalValueList/version.txt`

---

## 🏗️ ビルド手順

### EXE 1: DigitalValueList.exe（メインプログラム）

**概要:** Djangoサーバーを起動するメインプログラム

**ビルドコマンド:**
```powershell
pyinstaller DigitalValueList.spec
```

**出力先:**
```
dist/DigitalValueList.exe
```

**含まれるファイル:**
- Django_run.py（エントリーポイント）
- templates/（HTMLテンプレート）
- static/（CSS/JS）
- dashboard/（アプリケーション）
- digital_pricelist_system/（設定）
- manage.py
- degital_value_list.xlsx

**ビルド時間:** 約3〜5分

**確認方法:**
```powershell
# ファイルサイズ確認（目安: 100〜150MB）
dir dist\DigitalValueList.exe

# 起動テスト（開発環境）
dist\DigitalValueList.exe
```

**注意事項:**
- `console=False` のためウィンドウなしで起動
- ブラウザが自動で開く
- ログは `logs/` フォルダに出力

---

### EXE 2: BatchAIExtract.exe（AI抽出バッチ）

**概要:** PDF価格表からAI抽出を行うバッチツール

**ビルドコマンド:**
```powershell
pyinstaller BatchAIExtract.spec
```

**出力先:**
```
dist/BatchAIExtract.exe
```

**含まれるファイル:**
- batch_ai_extract.py（エントリーポイント）
- 必要な依存ライブラリのみ

**ビルド時間:** 約2〜3分

**確認方法:**
```powershell
# ファイルサイズ確認（目安: 50〜80MB）
dir dist\BatchAIExtract.exe

# 起動テスト（コンソール表示）
dist\BatchAIExtract.exe --help
```

**重要な仕様:**
- **DBファイルはEXEに含まれない**
- 実行時に `config.ini` からDBパスを読み込む
- 本番環境のDBに必要なテーブルが存在する必要がある
- `console=True` のためコンソールウィンドウが表示される

**実行時の前提条件:**
```
同じフォルダに以下が必要:
├── BatchAIExtract.exe
├── config.ini          ← DBパスを指定
└── db.sqlite3          ← 本番DB（マイグレーション済み）
```

---

### EXE 3: デジタル価格表作成プログラム.exe（バージョンチェッカー）

**概要:** サーバーから最新版をダウンロードして起動するランチャー

**ビルドコマンド:**
```powershell
pyinstaller --onefile --console --name デジタル価格表作成プログラム version_checker.py
```

**または専用スクリプトを使用:**
```powershell
python pj_doc\build_version_checker.py
```

**出力先:**
```
dist/デジタル価格表作成プログラム.exe
```

**含まれるファイル:**
- version_checker.py（エントリーポイント）
- 標準ライブラリのみ（軽量）

**ビルド時間:** 約1〜2分

**確認方法:**
```powershell
# ファイルサイズ確認（目安: 5〜10MB）
dir dist\デジタル価格表作成プログラム.exe

# 起動テスト
dist\デジタル価格表作成プログラム.exe
```

**動作フロー:**
1. サーバーの `version.txt` とローカルの `version.txt` を比較
2. サーバー側が新しい場合、`DigitalValueList.exe` をダウンロード
3. `C:\ZBS\DVL\DigitalValueList.exe` を起動

**注意事項:**
- **初回リリース後は通常更新不要**
- バージョンチェックロジックを変更した場合のみ再ビルド
- ユーザーはこのEXEのみを起動する

---

## 📋 ビルド手順チェックリスト

### ビルド前
- [ ] 仮想環境を有効化
- [ ] `version.txt` を更新
- [ ] コード修正が完了
- [ ] ローカルテスト完了

### ビルド実行
```powershell
# 1. メインプログラム
pyinstaller DigitalValueList.spec

# 2. AI抽出バッチ
pyinstaller BatchAIExtract.spec

# 3. バージョンチェッカー（初回のみ）
pyinstaller --onefile --console --name デジタル価格表作成プログラム version_checker.py
```

### ビルド後確認
- [ ] `dist/DigitalValueList.exe` が存在
- [ ] `dist/BatchAIExtract.exe` が存在
- [ ] `dist/デジタル価格表作成プログラム.exe` が存在（初回のみ）
- [ ] 各EXEのファイルサイズが正常
- [ ] 各EXEが起動する

---

## 🚀 サーバーへの配置

### 配置先パス
```
\\128.167.100.10\資材・大家畜事業部\04資材部\★デジタル価格表作成プログラム\
```

### 配置ファイル

| ファイル | 配置頻度 | 備考 |
|---------|---------|------|
| DigitalValueList.exe | 毎回 | メインプログラム |
| version.txt | 毎回 | バージョン番号 |
| デジタル価格表作成プログラム.exe | 初回のみ | ランチャー |
| BatchAIExtract.exe | 必要時 | AI抽出ツール |

### 配置手順

```powershell
# 1. サーバーフォルダを開く
explorer "\\128.167.100.10\資材・大家畜事業部\04資材部\★デジタル価格表作成プログラム"

# 2. 以下のファイルをコピー
# dist\DigitalValueList.exe → サーバー
# version.txt → サーバー

# 3. 既存ファイルを上書き
```

### 配置後の確認
- [ ] DigitalValueList.exe のタイムスタンプが最新
- [ ] version.txt の内容が更新されている
- [ ] ファイルが破損していない

---

## 🧪 動作確認

### 1. 開発環境でのテスト

```powershell
# メインプログラム起動テスト
dist\DigitalValueList.exe
# → ブラウザが開き、システムが起動すること

# AI抽出バッチテスト
dist\BatchAIExtract.exe
# → コンソールが表示され、ヘルプが表示されること

# バージョンチェッカーテスト
dist\デジタル価格表作成プログラム.exe
# → バージョン比較が実行されること
```

### 2. 本番環境での確認

**新規インストールテスト:**
1. テスト用PCで `C:\ZBS\DVL\` フォルダを削除
2. サーバーから `デジタル価格表作成プログラム.exe` を起動
3. 自動ダウンロードが実行される
4. メインプログラムが起動する

**更新テスト:**
1. 既存環境で `デジタル価格表作成プログラム.exe` を起動
2. 「新しいバージョンが利用可能です」と表示される
3. 自動更新が実行される
4. 新バージョンで起動する

---

## ⚠️ トラブルシューティング

### ビルドエラー

**エラー:** `ModuleNotFoundError: No module named 'django'`
```powershell
# 解決策: 仮想環境を有効化
.venv\Scripts\activate
pip install django django-bootstrap5
```

**エラー:** `Spec file not found`
```powershell
# 解決策: プロジェクトルートで実行
cd c:\Users\kodama-sho\Source\Repos\ZCS_DegitalValueList
pyinstaller DigitalValueList.spec
```

**エラー:** `Permission denied`
```powershell
# 解決策: 既存のEXEを終了
taskkill /f /im DigitalValueList.exe
taskkill /f /im BatchAIExtract.exe
```

### 実行エラー

**エラー:** 「config.iniが見つかりません」
- `config.ini` がEXEと同じフォルダにあるか確認
- パスが正しいか確認

**エラー:** 「DBファイルが見つかりません」
- `config.ini` の `[DATABASE] path` を確認
- DBファイルが存在するか確認
- マイグレーションが適用されているか確認

**エラー:** 「ポートが使用中です」
```powershell
# 解決策: 既存プロセスを終了
taskkill /f /im DigitalValueList.exe
```

---

## 📁 ファイル構成

### サーバー構成
```
\\128.167.100.10\...\
├── デジタル価格表作成プログラム.exe  ← ユーザーが起動
├── DigitalValueList.exe              ← 自動更新される
├── BatchAIExtract.exe                ← AI抽出ツール
├── version.txt                        ← バージョン番号
├── config.ini                         ← 設定ファイル
└── db.sqlite3                         ← 本番DB
```

### ユーザーPC構成
```
C:\ZBS\DVL\
├── DigitalValueList.exe  ← サーバーからコピー
├── version.txt            ← サーバーからコピー
└── logs\                  ← 実行時に自動作成
```

---

## 🔄 更新フロー

```
1. 開発者がコード修正
   ↓
2. version.txt を更新
   ↓
3. 3つのEXEをビルド
   ↓
4. サーバーに配置
   ↓
5. ユーザーが「デジタル価格表作成プログラム.exe」を起動
   ↓
6. 自動でバージョンチェック
   ↓
7. 新しい場合は自動ダウンロード
   ↓
8. 最新版が起動
```

---

## 📝 補足情報

### specファイルの役割

**DigitalValueList.spec:**
- Django関連ファイルをすべて含める
- `console=False` でウィンドウなし起動
- テンプレート、静的ファイル、アプリケーションを含む

**BatchAIExtract.spec:**
- 最小限の依存関係のみ
- `console=True` でコンソール表示
- DBファイルは含めない（config.iniで指定）

**version_checker.py:**
- 標準ライブラリのみ使用
- 軽量（5〜10MB）
- バージョン比較とファイルコピーのみ

### ビルド時間の目安

| EXE | ビルド時間 | ファイルサイズ |
|-----|-----------|--------------|
| DigitalValueList.exe | 3〜5分 | 100〜150MB |
| BatchAIExtract.exe | 2〜3分 | 50〜80MB |
| デジタル価格表作成プログラム.exe | 1〜2分 | 5〜10MB |

---

**最終更新日:** 2025/03/06  
**作成者:** Amazon Q  
**バージョン:** 1.0
