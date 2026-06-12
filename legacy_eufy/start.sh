#!/bin/bash
echo "Starting internal DBus..."
mkdir -p /var/run/dbus
rm -f /var/run/dbus/pid /run/dbus/pid
dbus-daemon --system

echo "Starting internal Bluetooth daemon..."
/usr/libexec/bluetooth/bluetoothd &

echo "Waiting for bluetoothd..."
sleep 2

echo "Bringing up HCI interfaces..."
for i in $(hciconfig | grep hci | awk -F: '{print $1}'); do
    echo "Resetting $i..."
    hciconfig $i down
    sleep 1
    hciconfig $i up
done || true

echo "Starting API server..."
python -u api.py &

echo "Starting BLE scanner script..."
exec python -u ble_scanner.py
