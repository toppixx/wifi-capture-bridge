from flask import Flask, render_template, request
import subprocess
import os
import time

# append logs to a file
logFileName="/var/log/wifi_recapture.log"
def log(text):
    print(text)
    with open(logFileName, "a") as f:
        f.write(f"{time.asctime()}: {text}\n")  

app = Flask(__name__)

# @app.route('/')
# def index():
#     result = subprocess.run(['nmcli', '-t', '-f', 'SSID', 'dev', 'wifi'], capture_output=True, text=True)
#     networks = sorted(set(filter(None, result.stdout.strip().split('\n'))))
#     return render_template('index.html', networks=networks)

# @app.route('/connect', methods=['POST'])
# def connect():
#     os.system('sudo rfkill unblock wifi')
#     os.system('sudo nmcli radio wifi on')
#     ssid = request.form['ssid']
#     password = request.form['password']
#     log(f"Connecting to {ssid}...")
#     result = subprocess.run(['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password, 'ifname', 'wlan1'])
#     log(f"Connecting to {result.stdout}...")

#     time.sleep(10)
#     result = subprocess.run(["iwgetid"], capture_output=True, text=True)
#     if ssid in result.stdout:
#         log(f"connected to wifi: {result.stdout}")
#     else:
#         log(f"failed to connect to wifi: {result.stdout}")
#     return ssid in result.stdout

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)


def run(command):
    command = command if isinstance(command, list) else command.split(" ")
    result = subprocess.run(command, capture_output=True, text=True)
    log(f"{' '.join(command)}")
    if(result.returncode != 0):
        log(f"Error executing command: {' '.join(command)}")
        log(f"Return code: {result.returncode}")
    if result.stdout:
        log(f"Stdout: {result.stdout}")
    if result.stderr:
        log(f"Stderr: {result.stderr}")
    return result

def remove_old_hotspot(name):
    result = subprocess.run(['nmcli', '-t', '-f', 'NAME', 'connection', 'show'], capture_output=True, text=True)
    connections = result.stdout.strip().split('\n')
    if name in connections:
        subprocess.run(['sudo', 'nmcli', 'connection', 'delete', name])
        print(f"Deleted connection: {name}")
    else:
        print(f"No connection named '{name}' found.")


def cretae_hotspot(ssid, password):
    log(f"Creating hotspot {ssid}...")
    run('sudo sysctl -w net.ipv4.ip_forward=1')
    run('sudo iptables -t nat -A POSTROUTING -o wlan1 -j MASQUERADE')
    run('sudo iptables -A FORWARD -i wlan1 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT')
    run('sudo iptables -A FORWARD -i wlan0 -o wlan1 -j ACCEPT')
    # result = subprocess.run(['nmcli', 'dev', 'wifi', 'hotspot', 'ifname', 'wlan0', 'con-name', ssid, 'ssid', ssid, 'band', 'bg', 'password', password], capture_output=True, text=True)
    # result = subprocess.run(["nmcli", "connection", "add", "type", "wifi", "ifname", "wlan0", "con-name", "MyHotspot", "autoconnect", "yes", "ssid", ssid, "wifi-mode", "ap", "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password, "ipv4.method", "shared"])
    remove_old_hotspot("MyHotspot")
    run(f"nmcli connection add type wifi ifname wlan0 con-name MyHotspot ssid {ssid}")
    run("nmcli connection modify MyHotspot 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared")
    run(f"nmcli connection modify MyHotspot wifi-sec.key-mgmt wpa-psk wifi-sec.psk {password}")
    result = run("nmcli connection up MyHotspot")

    log(f"Hotspot creation result: {result.stdout} {result.stderr}")
    if result.stdout and result.stderr:
        return result.returncode == 0, result.stdout + result.stderr
    elif result.stdout:
        return result.returncode == 0, result.stdout
    elif result.stderr:
        return result.returncode == 0, result.stderr
    return result.returncode == 0, ""

def scan_wifi():
    result = subprocess.run(['nmcli', '-t', '-f', 'SSID', 'dev', 'wifi'], capture_output=True, text=True)
    networks = sorted(set(filter(None, result.stdout.strip().split('\n'))))
    log(f"Available networks: {networks}")
    return networks

def connect_wifi(ssid, password):
    ssid = request.form['ssid']
    password = request.form['password']
    log(f"Connecting to {ssid}...")
    # result = subprocess.run(["nmcli", "connection", "add" ,"type", "wifi", "ifname", "wlan1", "autoconnect", "yes", "ssid", ssid, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password])

    run(f"sudo nmcli con add type wifi ifname wlan0 con-name Hotspot autoconnect yes ssid {ssid}")
    run("sudo nmcli con modify Hotspot 802-11-wireless.mode ap 802-11-wireless.band bg")
    run("sudo nmcli con modify Hotspot ipv4.method shared")
    run("sudo nmcli con modify Hotspot wifi-sec.key-mgmt wpa-psk")
    run(f"sudo nmcli con modify Hotspot wifi-sec.psk '{password}'")
    run("sudo nmcli con up Hotspot")

    result = subprocess.run(["iwgetid"], capture_output=True, text=True)
    if ssid in result.stdout:
        log(f"connected to wifi: {result.stdout}")
        return True, "connected to wifi: {result.stdout}"
    else:
        log(f"failed to connect to wifi: {result.stdout}")
        return False, f"failed to connect to wifi: {result.stdout + " " + result.stderr}"
    return result.returncode == 0, result.stdout + result.stderr

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'connect':
            ssid = request.form['ssid']
            password = request.form['password']
            success, message = connect_wifi(ssid, password)
        elif action == 'scan':
            networks = scan_wifi()
            return render_template('index.html', networks=networks)
        # exit()
        return render_template('result.html', success=success, message=message)

    networks = scan_wifi()
    return render_template('index.html', networks=networks)

@app.route('/result')
def result():
    return redirect(url_for('index'))

@app.route('/hotspot-detect.html')
def hotspot_detect():
    return "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>", 200

@app.route('/generate_204')
def android_check():
    return "", 200

@app.route('/ncsi.txt')
def windows_check():
    return "Microsoft NCSI", 200

if __name__ == '__main__':
    os.system('sudo rfkill unblock wifi')
    os.system('sudo nmcli radio wifi on')
    cretae_hotspot("WiFi_Captive_Portal", "password123")
    app.run(ssl_context=('cert.pem', 'key.pem'), host='0.0.0.0', port=5000)  