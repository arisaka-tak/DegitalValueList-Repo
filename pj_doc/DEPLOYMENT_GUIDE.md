# デジタル価格表システム 配布ガイド

## 配布構成

### ファイルサーバー側
```
共有フォルダ/
├── DigitalPriceList.exe  # 配布用実行ファイル
├── db.sqlite3           # 共有データベース
├── config.ini           # 設定ファイル（オプション）
└── README.txt           # 利用説明書
```

### クライアントPC側
```
任意のフォルダ/
└── DigitalPriceList.exe  # コピーして実行
```

## セットアップ手順

### 1. ファイルサーバー準備
1. 共有フォルダを作成
2. `DigitalPriceList.exe` を配置
3. 初期データベース `db.sqlite3` を配置
4. 共有フォルダの読み書き権限を設定

### 2. クライアント利用

#### 方法1: 直接実行（推奨）
1. ファイルサーバー上の `DigitalValueList.exe` を直接ダブルクリック
2. 自動的にデータベースに接続

#### 方法2: ローカルコピー
1. `DigitalValueList.exe` を各PCにコピー
2. 実行ファイルをダブルクリック
3. 自動的にサーバーのデータベースに接続

## データベース配置パターン

### パターン1: 同一フォルダ
```
DigitalPriceList.exe と db.sqlite3 を同じフォルダに配置
```

### パターン2: ネットワークドライブ
```
Z:\DigitalPriceList\db.sqlite3
```

### パターン3: UNCパス
```
\\server\share\DigitalPriceList\db.sqlite3
```

## 設定ファイル（config.ini）

### 基本設定
```ini
[DATABASE]
# データベースファイルのパス（ファイル名も含む）
path = db.sqlite3

[SYSTEM]
port = 8000
auto_browser = true
```

### 環境別データベース設定例

#### 本番環境
```ini
[DATABASE]
path = db_production.sqlite3
```

#### テスト環境
```ini
[DATABASE]
path = db_test.sqlite3
```

#### ネットワーク上の本番環境
```ini
[DATABASE]
path = \\server\share\DigitalPriceList\db_production.sqlite3
```

#### ローカルテスト
```ini
[DATABASE]
path = C:\temp\db_test.sqlite3
```

### 設定変更手順
1. `config.ini` ファイルを編集
2. `[DATABASE]` の `path` を変更
3. アプリケーションを再起動

**注意**: ファイル名も自由に設定可能です。拡張子は `.sqlite3` を推奨します。

## トラブルシューティング

### データベースが見つからない
- ネットワーク接続を確認
- 共有フォルダのアクセス権限を確認
- パスの記述を確認（バックスラッシュのエスケープ）

### ポートエラー
- 他のアプリケーションがポート8000を使用していないか確認
- config.ini でポート番号を変更

### 起動しない
- ウイルス対策ソフトの除外設定
- 管理者権限での実行を試行

## バックアップ

定期的にデータベースファイルをバックアップしてください。

```bash
# 例：日次バックアップ（本番環境）
copy db_production.sqlite3 backup\db_production_20241016.sqlite3

# 例：テスト環境
copy db_test.sqlite3 backup\db_test_20241016.sqlite3
```

**重要**: `config.ini` で指定したデータベースファイルをバックアップしてください。

## 直接実行のメリット

- ✅ **更新が簡単**: サーバー上のexeを差し替えるだけで全員に反映
- ✅ **バージョン統一**: 全員が常に同じバージョンを使用
- ✅ **ディスク容量節約**: 各PCにコピー不要
- ✅ **管理が楽**: 1箇所だけ管理すればOK

## 更新手順

### 直接実行の場合
1. 全ユーザーにシステム終了を依頼
2. データベースファイルをバックアップ（`config.ini` で指定されたファイル）
3. 新しい `DigitalPriceList.exe` に差し替え
4. 利用再開（各ユーザーはサーバー上のexeを再実行）

### ローカルコピーの場合
1. 全ユーザーにシステム終了を依頼
2. データベースファイルをバックアップ（`config.ini` で指定されたファイル）
3. 新しい `DigitalPriceList.exe` を各PCに配布
4. 利用再開

### 環境切り替え手順
1. システムを終了
2. `config.ini` の `[DATABASE] path` を変更
3. システムを再起動

例：本番からテストに切り替え
```ini
# 変更前（本番）
path = db_production.sqlite3

# 変更後（テスト）
path = db_test.sqlite3
```

## セキュリティ考慮事項

- データベースファイルへのアクセス権限を適切に設定
- 定期的なバックアップの実施
- ネットワーク経由でのアクセスログ監視