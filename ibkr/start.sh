#!/bin/bash
set -e

echo "Starting Xvfb..."
Xvfb :1 -screen 0 1024x768x24 -ac &
sleep 2

echo "Starting X11VNC server..."
x11vnc -display :1 -bg -forever -nopw -quiet -listen 0.0.0.0 -xkb

echo "Setting up port forwarding..."
socat TCP-LISTEN:${TWS_PORT},fork TCP:localhost:${TWS_PORT} &

echo "Checking if jts.ini exists..."
if [ ! -f /root/Jts/jts.ini ]; then
    echo "Creating default jts.ini..."
    cp /opt/ibc/config/jts.ini.default /root/Jts/jts.ini
fi

echo "Updating trading mode to: ${TRADING_MODE}"
sed -i "s/TradingMode=.*/TradingMode=${TRADING_MODE}/" /opt/ibc/config.ini

echo "Starting IB Gateway with IBC..."
cd /opt/ibc
./scripts/IBController.sh /opt/ibc/config.ini &

echo "IB Gateway startup complete!"

# Keep container running and capture logs
tail -f /opt/ibc/logs/*.log