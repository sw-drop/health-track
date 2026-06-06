FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y bluez dbus procps && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY ble_scanner.py .
COPY api.py .
COPY start.sh .

RUN chmod +x start.sh

# Create directory for data output
RUN mkdir -p /data

CMD ["./start.sh"]
