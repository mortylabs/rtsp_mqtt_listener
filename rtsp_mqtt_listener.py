#!/usr/bin/python3
import os
import time
import logging
import requests
import subprocess
import threading
import paho.mqtt.client as mqtt
from collections import defaultdict
from queue import Queue

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Load environment variables
MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.1.15")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "home/automation/camera_capture")
RTSP_URL_TEMPLATE = os.getenv("RTSP_URL_TEMPLATE", "rtsp://{user}:{password}@{ip}/stream1?tcp")

CAMERA_CREDENTIALS = {
    "user": os.getenv("USER_TPLINK_CAM", "admin"),
    "password": os.getenv("PASS_TPLINK_CAM", "password")
}

# Load cameras dynamically from environment variables
def load_cameras_from_env():
    """Load camera names and their IP addresses from environment variables."""
    camera_names = os.getenv("CAMERA_NAMES", "").split(",")
    ip_cameras = {}

    for camera in camera_names:
        camera = camera.strip()
        if camera:
            ip_cameras[camera] = os.getenv(f"{camera.upper()}_IP")

    return ip_cameras

IP_CAMERAS = load_cameras_from_env()

# Camera request queues (one per camera)
camera_queues = {camera: Queue() for camera in IP_CAMERAS}
active_grabs = defaultdict(lambda: threading.Lock())  # Prevents multiple grabs on the same camera

# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram_message(message):
    """Send a text message to Telegram."""
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data={"chat_id": TELEGRAM_CHAT_ID, "text": message}
            )
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {e}")

def send_telegram_photo(photo, caption):
    """Send a photo to Telegram."""
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": photo}
            )
        except Exception as e:
            logging.error(f"Failed to send Telegram photo: {e}")

def get_camera_ip(camera_name):
    """Retrieve the IP address of the specified camera."""
    return IP_CAMERAS.get(camera_name, None)

def get_rtsp_url(camera_name):
    """Generate RTSP URL for the given camera using the configured template."""
    ip = get_camera_ip(camera_name)
    return RTSP_URL_TEMPLATE.format(
        user=CAMERA_CREDENTIALS["user"],
        password=CAMERA_CREDENTIALS["password"],
        ip=ip
    )

def capture_frame_ffmpeg(camera_name):
    """Capture a single frame using FFmpeg and send it via Telegram."""
    url = get_rtsp_url(camera_name)
    output_path = f"/tmp/{camera_name}.jpg"

    with active_grabs[camera_name]:  # Lock to prevent multiple grabs at once
        logging.info(f"Capturing frame from: {url}")
        
        start_time = time.time()  # Start time tracking

        try:
            # Grab a single frame using FFmpeg (ensures fast RTSP access)
            command = f"ffmpeg -rtsp_transport tcp -i {url} -frames:v 1 {output_path} -y"
            subprocess.run(command, shell=True, check=False)

            capture_duration = round(time.time() - start_time, 2)  # Calculate time taken

            if os.path.exists(output_path):
                with open(output_path, "rb") as img:
                    send_telegram_photo(
                        ("capture.jpg", img),
                        f"📷 {camera_name} captured in {capture_duration} secs"
                    )
                os.remove(output_path)
            else:
                send_telegram_message(f"⚠️ Capture failed for {camera_name}")

        except Exception as e:
            logging.error(f"Capture error ({camera_name}): {str(e)}")

def process_camera_queue(camera_name):
    """Continuously process capture requests from the queue."""
    while True:
        request = camera_queues[camera_name].get()
        capture_frame_ffmpeg(camera_name)
        camera_queues[camera_name].task_done()
        time.sleep(1)  # Small delay to prevent rapid-fire requests

def on_connect(client, userdata, flags, rc):
    """MQTT connection callback."""
    if rc == 0:
        logging.info(f"Connected to MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
    else:
        logging.error(f"MQTT connection failed with error code {rc}")

def on_message(client, userdata, msg):
    """MQTT message received callback."""
    camera_name = msg.payload.decode("utf-8").strip()
    if camera_name in camera_queues:
        logging.info(f"Received capture request for: {camera_name}")
        camera_queues[camera_name].put(camera_name)  # Add request to queue
    else:
        logging.warning(f"Unknown camera name received: {camera_name}")

def start_mqtt_listener():
    """Initialize and run MQTT listener indefinitely."""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        logging.error(f"MQTT connection error: {e}")

if __name__ == "__main__":
    logging.info("Starting MQTT RTSP Listener...")

    # Start a queue processing thread for each camera
    for camera in IP_CAMERAS:
        threading.Thread(target=process_camera_queue, args=(camera,), daemon=True).start()

    start_mqtt_listener()
