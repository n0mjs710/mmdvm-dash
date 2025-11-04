# Installation

## Requirements

- Linux system with Python 3.8+
- MMDVMHost installed and configured
- User `mmdvm` with read access to MMDVM log files

## Install

```bash
# As mmdvm user
cd ~
git clone https://github.com/n0mjs710/mmdvm-dash.git
cd mmdvm-dash

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config/config.example.json config/config.json
nano config/config.json
```

Edit `config.json` to set paths to your INI files if different from defaults (`/etc/MMDVM.ini`, `/etc/DMRGateway.ini`, etc.)

## Run

```bash
# Manual run
cd ~/mmdvm-dash
source venv/bin/activate
python run_dashboard.py
```

Access at: `http://your-ip:8080`

## Systemd Service (auto-start)

```bash
# Install service
sudo cp mmdvm-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mmdvm-dashboard
sudo systemctl start mmdvm-dashboard

# Check status
sudo systemctl status mmdvm-dashboard
journalctl -u mmdvm-dashboard -f
```

## Update

```bash
cd ~/mmdvm-dash
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart mmdvm-dashboard
```

---

**0x49 DE N0MJS**
