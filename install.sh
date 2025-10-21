#!/bin/bash

set -e

APP_DIR="/opt/captive-portal"
VENV_DIR="wifi_env"

echo "🔧 Updating system and installing dependencies..."
sudo apt update
sudo apt install -y network-manager dnsmasq iptables python3 python3-pip git

echo "🔧 Creating virtual environment in $VENV_DIR..."
python3 -m venv $APP_DIR/$VENV_DIR

echo "🐍 Installing Flask..."
$APP_DIR/$VENV_DIR/bin/pip3 install flask gunicorn


echo "🔐 Installing OpenSSL..."
sudo apt install openssl

echo "📁 Setting up Flask app..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR
sudo cp portal.py $APP_DIR/portal.py

sudo cp -r templates $APP_DIR/
sudo cp -r static $APP_DIR/


echo "🌐 Configuring dnsmasq on network manager..."
sudo mkdir -p /etc/NetworkManager/dnsmasq-shared.d
# sudo cp configs/dnsmasq.conf /etc/dnsmasq.conf
sudo cp configs/dnsmasq-wlan0.conf /etc/NetworkManager/dnsmasq-shared.d/wlan0.conf
sudo cp configs/network-manager-dnsmasq.conf /etc/NetworkManager/conf.d/dnsmasq.conf
sudo sudo systemctl restart NetworkManager

echo "🔑 Generating self-signed SSL certificate..."
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365  -subj "/C=DE/ST=Bayern/L=Muenchen/O=Teddy/CN=localhost"

echo "📄 Configure flasks ssl"
sudo cp key.pem $APP_DIR/
sudo cp cert.pem $APP_DIR/

echo "🔁 Enabling IP forwarding..."
sudo sysctl -w net.ipv4.ip_forward=1

echo "🧱 Setting up iptables redirect..."
sudo iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 5000

# echo "📡 Creating WPA2 hotspot..."
# nmcli dev wifi hotspot ifname wlan0 ssid CapturePortal password "HotspotPassword123"

echo "🚀 Creating systemd service..."
# ExecStart=/usr/bin/python3 $APP_DIR/portal.py
sudo bash -c "cat <<EOF > /etc/systemd/system/captive-portal.service
[Unit]
Description=Captive Portal Flask App
After=network.target

[Service]
ExecStart=/bin/bash -c 'cd $APP_DIR && ./wifi_env/bin/python3 -u -m gunicorn --certfile=cert.pem --keyfile=key.pem -b 0.0.0.0:443 portal:app'
WorkingDirectory=$APP_DIR
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl enable captive-portal
sudo systemctl restart captive-portal

echo "✅ Setup complete! Connect to 'CapturePortal' and visit any website to access the portal."
echo "check service by using 'systemctl status captive-portal'"