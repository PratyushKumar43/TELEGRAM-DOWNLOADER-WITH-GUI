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
$ git clone https://github.com/PratyushKumar43/telegram-media-downloader.git
$ cd telegram-media-downloader
$ pip install -r requirements.txt
```

## ⚙️ Setup

1. Get API Keys:
   - Visit [https://my.telegram.org/apps](https://my.telegram.org/apps)
   - Create new application
   - Note your `api_id` and `api_hash`

2. Get Chat/Channel ID:
   - Use [@username_to_id_bot](https://t.me/username_to_id_bot)
   - Or check web.telegram.org URL format
   - For private chats, you'll need to use the numerical ID

3. Configure `config.yaml`:
   - Copy `config.yaml.template` to `config.yaml`
   - Fill in your details:
```yaml
api_hash: "your_api_hash"
api_id: your_api_id
chat_id: telegram_chat_id
phone_number: "your_phone_number"
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
download_settings:
  chunk_size: 2097152  # 2MB chunks for downloads
```

## 🚀 Usage

1. Start the application:
```bash
$ python media_downloader.py
```

2. GUI Features:
   - 📂 Browse and select download directory
   - ✅ Choose media types to download
   - 🔄 View download progress
   - ⏸️ Pause/Resume downloads
   - 🔍 Monitor download status

### 📂 Default Download Paths
| Media Type | Directory |
|------------|-----------|
| 🎵 Audio | `./audio` |
| 📄 Documents | `./document` |
| 📸 Photos | `./photo` |
| 🎥 Videos | `./video` |
| 🗣️ Voice | `./voice` |

### 🔒 Optional: Proxy Configuration
Add the following to your `config.yaml` if you need to use a proxy:
```yaml
proxy:
  scheme: socks5
  hostname: 11.22.33.44
  port: 1234
  username: your_username  # Optional
  password: your_password  # Optional
```

## 📦 Dependencies
- pyrogram - Telegram client library
- tgcrypto - Crypto functions for Telegram
- pyyaml - YAML file handling
- rich - Terminal formatting
- tqdm - Progress bars
- pillow - Image processing
