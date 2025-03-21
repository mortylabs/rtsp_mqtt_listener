# 🚨 RTSP MQTT Camera Snapshot Listener

**Capture camera snapshots at blazing speeds—faster and more reliable than traditional Home Assistant plugins.**

RTSP MQTT Camera Snapshot Listener is a streamlined Python app designed to deliver instant snapshots from your security cameras straight to your Telegram. Powered by optimized OpenCV pipelines and MQTT integration, it ensures real-time home security monitoring wherever you are. Tested and proven blazing fast on TP-Link Tapo cameras, it's perfect for keeping a security feed directly accessible on your phone via Telegram.

> **Real-time alerts. Instant peace of mind.**
<p align="center">
  <img src="https://github.com/user-attachments/assets/a64c679f-09ee-4356-a581-1ff1f199ca7d" alt="Telegram Screenshot" width="300">
</p>

---

## 🌟 Key Features

- **⚡ Ultra-Fast Snapshots:** Leverages optimized OpenCV techniques and thread pooling for rapid snapshot capture.
- **📡 MQTT Integration:** Instantly responds to MQTT triggers, capturing camera snapshots immediately.
- **📲 Telegram Notifications:** Sends snapshots directly to your Telegram for immediate security updates.
- **🔧 Flexible Configuration:** Easily configure multiple cameras and credentials via environment variables.
- **🐳 Docker & k3s Ready:** Fully containerized for effortless deployment on modern platforms, including Raspberry Pi clusters.
- **🍓 Optimized for Raspberry Pi:** ARM-compatible with optional hardware-accelerated decoding via GStreamer.

---

## 🤔 Why Use This Project?

Typical Home Assistant camera plugins introduce latency and complexity. This project removes delays, ensuring rapid snapshot delivery critical for effective home security. It’s lightweight, easy to configure, and built specifically for containerized deployments, including Kubernetes (k3s) on devices like the Raspberry Pi 4B.

---

## 📦 Installation

### ✅ **Prerequisites**

- Python 3.9+
- RTSP-compatible cameras
- MQTT broker
- Telegram Bot
- (Optional) Docker / Kubernetes (k3s)

### 💻 **Local Setup**

1. **Clone Repository:**

```bash
git clone https://github.com/your_username/rtsp-mqtt-camera-snapshot-listener.git
cd rtsp-mqtt-camera-snapshot-listener
```

2. **Setup Python Environment:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configure App:**

Create and configure `.env`:

```bash
cp .env.sample .env
# Edit .env with MQTT, camera URLs, and Telegram credentials
```

4. **Launch App:**

```bash
python rtsp_mqtt_listener.py
```

### 🐳 **Docker Quickstart**

Optimized Docker image for Raspberry Pi 4B:

```bash
docker pull your_dockerhub_username/rtsp-mqtt-listener:latest

docker run -d \
  --name rtsp-mqtt-listener \
  -e MQTT_BROKER="192.168.1.15" \
  -e MQTT_PORT="31883" \
  -e MQTT_USER="user" \
  -e MQTT_PASS="pass" \
  -e MQTT_TOPIC="home/automation/camera_capture" \
  -e CAMERAS="garage,frontdoor" \
  -e CAMERA_URL_GARAGE="rtsp://user:pass@192.168.1.36/stream1" \
  -e CAMERA_URL_FRONTDOOR="rtsp://user:pass@192.168.1.34/stream1" \
  -e TELEGRAM_BOT_TOKEN="your_bot_token" \
  -e TELEGRAM_CHAT_ID="your_chat_id" \
  your_dockerhub_username/rtsp-mqtt-listener:latest
```

### 🚀 **Deploying with Kubernetes (k3s)**

Check [mortylabs/kubernetes](https://github.com/mortylabs/kubernetes) for a ready-to-use deployment YAML.

---



