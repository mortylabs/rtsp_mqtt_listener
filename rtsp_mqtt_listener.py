#!/usr/bin/env python3
import os
import time
import sys
import signal
import logging
import requests
import threading
import concurrent.futures
import paho.mqtt.client as mqtt
import cv2
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration from environment ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.1.15")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "home/automation/camera_capture")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Load cameras dynamically.
# .env should include:
#   CAMERAS=garage,carport,frontdoor,aothercamera,etc
#   CAMERA_URL_GARAGE=rtsp://username:password@192.168.1.20/stream1
#   CAMERA_URL_CARPORT=rtsp://username:password@192.168.1.21/stream1
#   CAMERA_URL_FRONTDOOR=rtsp://username:password@192.168.1.22/stream1
#   CAMERA_URL_AOTHERCAMERA=rtsp://username:password@192.168.1.22/stream1

# etc
camera_names = [name.strip() for name in os.getenv("CAMERA_NAMES", "").split(",") if name.strip()]
IP_CAMERAS = {name: os.getenv(f"CAMERA_URL_{name.upper()}") for name in camera_names if os.getenv(f"CAMERA_URL_{name.upper()}")}

# --- Thread management ---
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)  # Limit to 3 concurrent captures per camera
last_captures = {}  # Tracks recent capture times (per camera) for rate limiting

# --- Logging Configuration ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Use 2 threads for OpenCV operations
cv2.setNumThreads(2)

# --- Function: Capture a frame using OpenCV ---
def capture_frame_opencv(camera_name):
    """Capture a frame from an RTSP stream using OpenCV and send it via Telegram."""
    if camera_name not in IP_CAMERAS:
        logging.warning(f"Unknown camera: {camera_name}")
        return

    url = IP_CAMERAS[camera_name]
    start_time = time.time()

    logging.info(f"Attempting to capture frame from: {url}")
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        logging.error(f"Failed to open RTSP stream: {url}")
        send_telegram_message(f"🚨 RTSP ERROR: {camera_name} failed to open stream")
        return

    # Set timeouts and reduce buffering for faster capture
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # Use grab/retrieve to minimize decoding overhead
    cap.grab()
    ret, frame = cap.retrieve()
    cap.release()

    if not ret:
        logging.error(f"Failed to grab frame from {camera_name}")
        send_telegram_message(f"🚨 RTSP ERROR: {camera_name} failed to grab frame")
        return

    # Encode frame as JPEG in memory
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    ret2, im_buf_arr = cv2.imencode(".jpg", frame, encode_param)
    if not ret2:
        logging.error(f"Failed to encode image for {camera_name}")
        send_telegram_message(f"🚨 ERROR: {camera_name} failed to encode frame")
        return

    image_bytes = im_buf_arr.tobytes()
    capture_time = round(time.time() - start_time, 2)
    logging.info(f"Sending image to Telegram (Captured in {capture_time}s)")
    send_telegram_photo(image_bytes, f"📷 {camera_name} captured in {capture_time} secs")

# --- Telegram Integration Functions ---
def send_telegram_photo(image_bytes, caption=""):
    """Send an image to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram bot is disabled (No Token/Chat ID).")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {"photo": ("image.jpg", image_bytes, "image/jpeg")}
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}

    logging.info("Sending image to Telegram API now...")
    try:
        response = requests.post(url, files=files, data=data, timeout=10)
        if response.status_code == 200:
            logging.info("Telegram API acknowledged message successfully")
        else:
            logging.error(f"Telegram API Error: {response.text}")
    except Exception as e:
        logging.error(f"Error sending Telegram photo: {e}")

def send_telegram_message(text):
    """Send a text message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")

# --- MQTT Event Handlers ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Handle MQTT connection events.

    Subscribes to the configured MQTT topic upon successful connection.
    """
    if rc == 0:
        logging.info(f"Connected to MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        logging.info(f"Subscribed to MQTT topic: {MQTT_TOPIC}")
    else:
        logging.error(f"MQTT connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Handle incoming MQTT messages and process capture requests.

    Decodes the camera name from the message, applies rate limiting, and dispatches
    a new thread to capture and process the frame.
    """
    camera_name = msg.payload.decode("utf-8").strip()
    if camera_name not in IP_CAMERAS:
        logging.warning(f"Unknown camera received: {camera_name}")
        return

    now = time.time()
    last_captures.setdefault(camera_name, [])
    # Keep only captures within the last 2 seconds
    last_captures[camera_name] = [t for t in last_captures[camera_name] if now - t < 2]
    if len(last_captures[camera_name]) >= 3:
        logging.info(f"Skipping {camera_name} (Already 3 captures in 2 sec)")
        return

    last_captures[camera_name].append(now)
    logging.info(f"Received MQTT request for: {camera_name}")
    executor.submit(capture_frame_opencv, camera_name)

# --- Graceful Shutdown Handler ---
def graceful_shutdown(signum, frame):
    """Handles graceful shutdown on receiving termination signals."""
    logging.info(f"Received signal {signum}. Initiating graceful shutdown...")
    client.disconnect()  # Disconnect from MQTT broker
    executor.shutdown(wait=True)
    sys.exit(0)

# --- Main Application Entry Point ---
def main():
    """Main entry point for the MQTT RTSP Listener application.

    Sets up MQTT client, registers signal handlers, and starts the client loop.
    """
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    global client  # Make client accessible in the shutdown handler
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.connect(MQTT_BROKER, MQTT_PORT)
    logging.info("MQTT RTSP Listener Started. Waiting for messages...")

    client.loop_start()  # Start the MQTT network loop in a background thread
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        graceful_shutdown(signal.SIGINT, None)
    finally:
        client.loop_stop()

if __name__ == "__main__":
    main()
