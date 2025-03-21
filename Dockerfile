# Use an official Python image built for ARM (e.g., python:3.9-slim)
FROM python:3.9-slim

# Install OS-level dependencies for OpenCV and other libraries
RUN apt-get update && apt-get install -y \
    libsm6 libxext6 libxrender-dev \
    libglib2.0-0 \
    gstreamer1.0-tools gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libgstreamer1.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose any ports if needed (not required for MQTT listeners typically)
# EXPOSE 8080

# Command to run your script
CMD ["python", "rtsp_mqtt_listener.txt"]
