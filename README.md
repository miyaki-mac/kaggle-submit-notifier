# Slack Submit Notifier

最近Kaggleを始めたのですが、提出（submit）の処理時間を確認する方法が見つからなかったため、
自分で簡易的な監視ツールを作成しました。

このツールは、Kaggleコンペティションへの提出状況をリアルタイムで監視し、
進行状態（例：pending → complete、pending → error）を自動的にSlackへ通知します。
定期的にKaggle APIから最新の提出情報を取得し、ステータスの変化を検出すると、
整形済みのメッセージをSlackに送信します。

Slackの無料プラン（一か月版）でも動作するため、
チーム内での提出状況共有や、チームマージ後の進捗確認などにも手軽に活用できます。
---

# 機能
- 指定したKaggleコンペティションの提出状況をリアルタイムで監視
- 提出ステータスの変化（例：pending → complete、pending → error）を自動検出
- 指定したSlackチャンネルへ結果を自動通知
- 通知内容には、公開／非公開リーダーボードスコアも含む
- ポーリング間隔と通知間隔を分単位の設定で統一管理

---

## 🧰 Requirements

### 1. Kaggle APIの認証情報

Kaggle APIキーを正しく設定してください。

```bash
mkdir -p ~/.kaggle
cp kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

> You can download your API key from [Kaggle Account Settings → Create New API Token](https://www.kaggle.com/settings).

---

### 2. Install dependencies

```bash
pip install kaggle requests
```

---

### 3. tmuxを利用した常時実行環境の準備（おすすめ）

長時間の自動監視を行う場合は、tmuxを利用すると便利です。
ターミナルを閉じてもスクリプトを継続実行できます。

```
sudo apt install tmux -y
tmux new -s kaggle-notifier
```
tmuxセッションを開いた状態で次の手順（通知スクリプトの実行）を行ってください。
セッションを維持したままバックグラウンドで動かすことができます。

### 4. Run the notifier

```bash
python main.py   --competition jigsaw-agile-community-rules   --slack-webhook "https://hooks.slack.com/services/XXX/YYY/ZZZ"   --interval-min 5
```

| Argument | Required | Default | Description |
|-----------|-----------|----------|-------------|
| `--competition` | ✅ | – | Kaggle competition slug (e.g., `jigsaw-agile-community-rules`) |
| `--slack-webhook` | ✅ | `$SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
| `--interval-min` | Optional | `10` | Interval (minutes) for both polling and reporting |
