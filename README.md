# 📥 Telegram Media Downloader

A Python-based GUI application to download media files from Telegram channels and chats.

## ✨ Features
- 🖥️ User-friendly GUI interface
- 📁 Custom download directory selection
- 🔄 Smart duplicate prevention
- 🎯 Selective media type filtering
- 🔒 Proxy support

## 💻 Requirements
- Python 3.7+
- Supported Media Types: 🎵 Audio, 📄 Documents, 📸 Photos, 🎥 Videos, 🗣️ Voice Notes

## 🛠️ Installation

```bash
$ git clone https://github.com/Dineshkarthik/telegram_media_downloader.git
$ cd telegram_media_downloader
$ pip3 install -r requirements.txt
```

## ⚙️ Setup

1. Get API Keys:
   - Visit [https://my.telegram.org/apps](https://my.telegram.org/apps)
   - Create new application
   - Note your `api_id` and `api_hash`

2. Get Chat/Channel ID:
   - Use [@username_to_id_bot](https://t.me/username_to_id_bot)
   - Or check web.telegram.org URL format

3. Configure `config.yaml`:
```yaml
api_hash: "your_api_hash"
api_id: your_api_id
chat_id: telegram_chat_id
media_types:
  - audio
  - document
  - photo
  - video
  - voice
file_formats:
  audio:
    - all
  document:
    - pdf
    - epub
  video:
    - mp4
```

## 🚀 Usage
```bash
$ python3 media_downloader.py
```

### 📂 Download Paths
| Media Type | Directory |
|------------|-----------|
| 🎵 Audio | `./audio` |
| 📄 Documents | `./document` |
| 📸 Photos | `./photo` |
| 🎥 Videos | `./video` |
| 🗣️ Voice | `./voice` |

### 🔒 Optional: Proxy Configuration
```yaml
proxy:
  scheme: socks5
  hostname: 11.22.33.44
  port: 1234
  username: your_username  # Optional
  password: your_password  # Optional
