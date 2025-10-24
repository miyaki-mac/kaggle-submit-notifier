# 🧠 Kaggle Submission Watcher (Slack Notifier)

Monitor your **Kaggle competition submissions** in real time and automatically **send status updates to Slack**.

This tool periodically fetches your latest Kaggle submissions, detects any status changes (e.g., *running → complete*, *complete → error*), and sends formatted Slack notifications — so you no longer have to keep refreshing the leaderboard 👀.

---

## 🚀 Features

- 🔁 Periodically polls Kaggle for submission updates  
- 🧩 Detects new or changed submission statuses  
- 💬 Sends rich Slack messages (with public/private LB scores if available)  
- ⏱ Uses a **single interval (in minutes)** for both polling and reporting  
- 🔒 Works with your existing `~/.kaggle/kaggle.json` authentication  
- 💡 Minimal dependencies (`kaggle`, `requests`)  

---

## 🧰 Requirements

### 1️⃣ Kaggle API credentials

Make sure your Kaggle API key is properly set up:

```bash
mkdir -p ~/.kaggle
cp kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
