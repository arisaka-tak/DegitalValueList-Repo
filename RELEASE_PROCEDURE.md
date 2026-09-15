# デジタル価格表システム リリース手順書

## 📋 目次
1. [事前準備](#事前準備)
2. [ビルド手順](#ビルド手順)
3. [リリース手順](#リリース手順)
4. [動作確認](#動作確認)
5. [トラブルシューティング](#トラブルシューティング)

---

## 事前準備

### 必要な環境
- Python 3.13.7
- PyInstaller 6.19.0
- 仮想環境 (.venv)
- 必要なパッケージ: Django, django-bootstrap5 ※要確認（他のパッケージ）

### 事前チェックリスト
- [ ] コード修正が完了している
- [ ] ローカル環境でテスト済み
- [ ] Git にコミット済み ※要確認（バージョン管理方法）
- [ ] サーバーへのアクセス権限がある

---

## ビルド手順

### 1. バージョン番号の更新

`version.txt` を編集:
```
v{YYYYMMDD}{NNN}
```

**例:**
- 2025年1月15日の1回目: `v202501150001`
- 2025年1月15日の2回目: `v202501150002`

**ファイルパス:**
```
ZCS_DegitalValueList/version.txt
```

### 2. 仮想環境の有効化

```powershell
# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 2.5. データベース確認

**重要:** BatchAIExtract.exeは**config.iniで指定されたDBファイル**を使用します。

```powershell
# 本番環境のDBに必要なテーブルが存在することを確認
# config.iniの[DATABASE]pathで指定されたDBファイルを確認
```

**注意:** 
- BatchAIExtract.exeはDBファイルを含まない
- 実行時にconfig.iniからDBパスを読み込む
- 本番環境のDBにマイグレーションが適用されている必要がある

### 3. EXEファイルのビルド

以下の3つのEXEファイルを作成:

#### 3-1. DigitalValueList.exe（本体プログラム）
```powershell
pyinstaller DigitalValueList.spec
```

**出力先:** `dist/DigitalValueList.exe`

#### 3-2. BatchAIExtract.exe（AI抽出ツール）

```powershell
pyinstaller BatchAIExtract.spec
```

**出力先:** `dist/BatchAIExtract.exe`

**重要:** 
- DBファイルはEXEに含まれません
- 実行時にconfig.iniからDBパスを読み込みます
- 本番環境のDBにマイグレーションが適用されている必要があります

#### 3-3. デジタル価格表作成プログラム.exe（バージョンチェッカー）
```powershell
pyinstaller version_checker.py --onefile --name デジタル価格表作成プログラム
```

**出力先:** `dist/デジタル価格表作成プログラム.exe`

### 4. ビルド結果の確認

```powershell
dir dist
```

以下のファイルが存在することを確認:
- [ ] DigitalValueList.exe
- [ ] BatchAIExtract.exe
- [ ] デジタル価格表作成プログラム.exe

---

## リリース手順

### 1. サーバーへの配置

**配置先パス:**
```
\\128.167.100.10\資材・大家畜事業部\04資材部\★デジタル価格表作成プログラム\
```

### 2. ファイルのコピー

以下のファイルをサーバーにコピー:

| ファイル | 更新頻度 | 備考 |
|---------|---------|------|
| DigitalValueList.exe | 毎回 | 本体プログラム |
| version.txt | 毎回 | バージョン番号 |
| デジタル価格表作成プログラム.exe | 初回のみ | バージョンチェッカー（通常は更新不要） |
| BatchAIExtract.exe | 必要時 | AI抽出ツール ※要確認（配置の必要性） |

### 3. 配置手順

```powershell
# 1. サーバーフォルダを開く
explorer "\\128.167.100.10\資材・大家畜事業部\04資材部\★デジタル価格表作成プログラム"

# 2. 以下のファイルをコピー
# - dist\DigitalValueList.exe → サーバー
# - version.txt → サーバー

# 3. 既存ファイルを上書き確認
```

### 4. 配置後の確認

サーバー上で以下を確認:
- [ ] DigitalValueList.exe のタイムスタンプが最新
- [ ] version.txt の内容が更新されている
- [ ] ファイルサイズが正常 ※要確認（想定サイズ）

---

## 動作確認

### 1. 開発環境でのテスト

```powershell
# テスト用バージョンチェッカーを実行
python version_checker_dev.py
```

**確認項目:**
- [ ] バージョン比較が正常に動作
- [ ] EXEのコピーが成功
- [ ] プログラムが起動する

### 2. 本番環境での確認 ※要確認（テスト環境の有無）

**テスト用PC:**
- [ ] `C:\ZBS\DVL\` フォルダを削除（クリーンインストールテスト）
- [ ] デジタル価格表作成プログラム.exe を起動
- [ ] 自動更新が実行される
- [ ] DigitalValueList.exe が起動する
- [ ] ブラウザが自動で開く
- [ ] システムが正常に動作する

### 3. 既存ユーザーでの確認

**既存インストール環境:**
- [ ] デジタル価格表作成プログラム.exe を起動
- [ ] 「新しいバージョンが利用可能です」と表示される
- [ ] 自動更新が実行される
- [ ] 新しいバージョンで起動する

---

## トラブルシューティング

### ビルドエラー

**エラー:** `Spec file not found`
```powershell
# 解決策: 正しいspecファイル名を使用
pyinstaller DigitalValueList.spec  # Django_run.spec ではない
```

**エラー:** `Module not found`
```powershell
# 解決策: 必要なパッケージをインストール
pip install django django-bootstrap5
```

### 配置エラー

**エラー:** サーバーにアクセスできない
- ネットワーク接続を確認
- アクセス権限を確認 ※要確認（権限管理者）

**エラー:** ファイルが上書きできない
- 実行中のプロセスを終了
- タスクマネージャーで DigitalValueList.exe を終了

### 起動エラー

**エラー:** 「プログラムが見つかりません」
- `C:\ZBS\DVL\` フォルダが存在するか確認
- DigitalValueList.exe が存在するか確認

**エラー:** 「config.iniが見つかりません」
- config.ini の配置を確認 ※要確認（config.iniの配置場所）

**エラー:** 「DBファイルが見つかりません」
- db.sqlite3 の配置を確認 ※要確認（DBファイルの配置場所）

---

## チェックリスト（リリース時）

### ビルド前
- [ ] コード修正完了
- [ ] ローカルテスト完了
- [ ] version.txt 更新

### ビルド
- [ ] DigitalValueList.exe ビルド成功
- [ ] BatchAIExtract.exe ビルド成功
- [ ] デジタル価格表作成プログラム.exe ビルド成功

### 配置
- [ ] サーバーにアクセス可能
- [ ] DigitalValueList.exe コピー完了
- [ ] version.txt コピー完了
- [ ] ファイルタイムスタンプ確認

### 動作確認
- [ ] 開発環境でテスト完了
- [ ] テスト用PCで確認完了 ※要確認
- [ ] 既存環境で確認完了 ※要確認

### リリース後
- [ ] ユーザーへ通知 ※要確認（通知方法）
- [ ] リリースノート作成 ※要確認（管理方法）

---

## 補足情報

### バージョンチェッカーの仕組み

1. ユーザーが「デジタル価格表作成プログラム.exe」を起動
2. サーバーの `version.txt` とローカルの `version.txt` を比較
3. サーバー側が新しい場合、`DigitalValueList.exe` を自動ダウンロード
4. `C:\ZBS\DVL\DigitalValueList.exe` を起動

### ファイル構成

```
サーバー:
\\128.167.100.10\...\
  ├── デジタル価格表作成プログラム.exe  ← ユーザーが起動
  ├── DigitalValueList.exe              ← 本体（自動更新される）
  ├── BatchAIExtract.exe                ← AI抽出ツール
  └── version.txt                        ← バージョン番号

ユーザーPC:
C:\ZBS\DVL\
  ├── DigitalValueList.exe  ← サーバーからコピーされる
  └── version.txt            ← サーバーからコピーされる
```

### 連絡先 ※要確認

- 開発担当: ※要確認
- サーバー管理者: ※要確認
- 問い合わせ先: ※要確認

---

**最終更新日:** 2025/01/XX ※要確認  
**作成者:** ※要確認  
**バージョン:** 1.0
