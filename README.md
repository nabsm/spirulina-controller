# Spirulina Controller

Full-stack IoT lighting controller for spirulina cultivation. Monitors ambient lux via RS485 Modbus RTU sensors and automatically toggles LED grow lights based on configurable time-windowed schedules with hysteresis.

## Quick Start (Development)

```bash
# Backend
source venv/bin/activate
SENSOR_MODE=sim uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd dashboard
npm install    # first time only
npm run dev    # dev server at :5173, proxies /api to :8000
```

## Production Deployment on Raspberry Pi

### Prerequisites

```bash
# Install Node.js (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs

# Clone and set up
cd /home/admin/dev
git clone <repo-url> spirulina-controller
cd spirulina-controller

# Python venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build frontend
cd dashboard
npm install
npm run build
cd ..
```

### Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings:
#   SENSOR_MODE=rs485
#   ACTUATOR_MODE=sonoff
#   SONOFF_IP=192.168.1.19
#   etc.
```

### Serve Frontend from Backend

The production setup serves the built frontend directly from uvicorn. The built files are in `dashboard/dist/`. Use a reverse proxy (caddy/nginx) or serve them with uvicorn + static file mounting.

Simplest approach — use `caddy` as a reverse proxy:

```bash
sudo apt install -y caddy
```

Create `/etc/caddy/Caddyfile`:

```
:80 {
    handle /api/* {
        reverse_proxy localhost:8000
    }

    handle {
        root * /home/admin/dev/spirulina-controller/dashboard/dist
        try_files {path} /index.html
        file_server
    }
}
```

```bash
sudo systemctl enable caddy
sudo systemctl restart caddy
```

### Set Up systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/spirulina.service
```

Paste the following (adjust paths/user if needed):

```ini
[Unit]
Description=Spirulina Controller Backend
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/dev/spirulina-controller
Environment=PATH=/home/admin/dev/spirulina-controller/venv/bin:/usr/bin:/bin
EnvironmentFile=/home/admin/dev/spirulina-controller/.env
ExecStart=/home/admin/dev/spirulina-controller/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable spirulina.service
sudo systemctl start spirulina.service
```

### Useful Commands

```bash
# Check status
sudo systemctl status spirulina

# View logs (live)
sudo journalctl -u spirulina -f

# Restart after code changes
cd /home/admin/dev/spirulina-controller
git pull
source venv/bin/activate
pip install -r requirements.txt
cd dashboard && npm install && npm run build && cd ..
sudo systemctl restart spirulina

# Stop
sudo systemctl stop spirulina

# Disable auto-start
sudo systemctl disable spirulina
```

### Accessing the Dashboard

Once both services are running:

- **With Caddy**: `http://<pi-ip>/` (port 80)
- **Without Caddy** (dev mode): `http://<pi-ip>:5173/` (run `npm run dev` in dashboard/)
- **API only**: `http://<pi-ip>:8000/api/live`
