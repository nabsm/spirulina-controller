# Raspberry Pi Setup — Standalone Lux Controller

This guide covers setting up `lux_controller.py` on a Raspberry Pi to read an RS485 Modbus RTU lux sensor over USB and automatically toggle grow lights based on ambient lux thresholds.

## What you need

- Raspberry Pi (any model with USB — tested on Pi 4 / Pi Zero 2 W)
- RS485-to-USB adapter (e.g. CH340-based or FTDI-based dongle)
- RS485 Modbus RTU lux sensor (wired to the adapter's A/B terminals)
- USB relay module (for controlling the grow light — see [Relay setup](#relay-setup) below)
- 5V power supply for the Pi

## Wiring

```
Lux sensor (RS485)          USB-RS485 adapter          Raspberry Pi
┌──────────┐               ┌──────────────┐           ┌──────────┐
│  A+ ─────┼───────────────│ A+           │           │          │
│  B- ─────┼───────────────│ B-       USB ├───────────│ USB port │
│  GND ────┼───────────────│ GND          │           │          │
│  VCC ────┼── 12/24V DC   └──────────────┘           └──────────┘
└──────────┘

USB relay                   Raspberry Pi
┌──────────┐               ┌──────────┐
│      USB ├───────────────│ USB port │
│  NO ─────┼── to light    │          │
│  COM ────┼── from mains  └──────────┘
└──────────┘
```

## 1. OS setup

Start with Raspberry Pi OS Lite (Bookworm or later). Update the system:

```bash
sudo apt update && sudo apt upgrade -y
```

Install Python and serial dependencies:

```bash
sudo apt install -y python3 python3-pip python3-venv
```

## 2. Find your serial port

Plug in the USB-RS485 adapter and check which port it appears on:

```bash
ls /dev/ttyUSB*
```

Typically this will be `/dev/ttyUSB0`. If you have multiple USB-serial devices, identify the right one with:

```bash
dmesg | grep ttyUSB
```

## 3. Serial port permissions

Your user needs access to the serial port. Add yourself to the `dialout` group:

```bash
sudo usermod -aG dialout $USER
```

Log out and back in (or reboot) for this to take effect.

## 4. Install the controller

Copy `lux_controller.py` to the Pi (via scp, USB drive, or git clone), then set up a virtual environment:

```bash
mkdir -p ~/lux-controller
cp lux_controller.py ~/lux-controller/
cd ~/lux-controller

python3 -m venv venv
source venv/bin/activate
pip install pymodbus pyserial
```

## 5. Test the sensor

Run a quick test to confirm the sensor is responding:

```bash
cd ~/lux-controller
source venv/bin/activate

python lux_controller.py --port /dev/ttyUSB0 --verbose
```

You should see output like:

```
2026-02-14 10:30:00 INFO  Starting lux controller
2026-02-14 10:30:00 INFO    Port:       /dev/ttyUSB0 @ 9600 baud (slave 1)
2026-02-14 10:30:00 INFO    Sampling:   every 6.0s, avg over 5 samples (30s window)
2026-02-14 10:30:00 INFO    Thresholds: min=3000  max=6000  hysteresis=50
2026-02-14 10:30:00 INFO  Connected to /dev/ttyUSB0 @ 9600 baud
2026-02-14 10:30:00 INFO  [10:30:00] lux=4200  avg=4200 (1/5 samples)  light=OFF
2026-02-14 10:30:06 INFO  [10:30:06] lux=4180  avg=4190 (2/5 samples)  light=OFF
```

If you see `Modbus error` or `Cannot connect`, check:
- Wiring (A/B not swapped?)
- Baud rate matches your sensor (try `--baudrate 4800` or `--baudrate 19200`)
- Slave ID matches your sensor (try `--slave-id 1` through `--slave-id 5`)
- Function code (some sensors use input registers: `--function-code 4`)

Press `Ctrl+C` to stop.

## 6. Tune your settings

The key parameters to adjust for your setup:

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `/dev/ttyUSB0` | Serial port of the USB-RS485 adapter |
| `--baudrate` | `9600` | Must match your sensor |
| `--slave-id` | `1` | Modbus address of your sensor |
| `--function-code` | `3` | `3` = holding registers, `4` = input registers |
| `--register` | `0` | Which register holds the lux value |
| `--scale` | `1.0` | Multiplier (e.g. `0.1` if sensor reports lux x 10) |
| `--min-lux` | `3000` | Below this average the light turns ON |
| `--max-lux` | `6000` | Above this average the light turns OFF |
| `--hysteresis` | `50` | Dead band to prevent flapping near thresholds |
| `--sample-interval` | `6` | Seconds between sensor reads |
| `--avg-window` | `30` | Seconds of samples to average (30s / 6s = 5 samples) |
| `--min-switch-interval` | `60` | Minimum seconds between ON/OFF changes |

Example with custom thresholds:

```bash
python lux_controller.py \
    --port /dev/ttyUSB0 \
    --min-lux 2000 \
    --max-lux 5000 \
    --hysteresis 100 \
    --sample-interval 5 \
    --avg-window 30
```

## 7. Relay setup

The script includes a `RelayStub` class that logs ON/OFF decisions without controlling hardware. When you have your USB relay module, edit `lux_controller.py` and replace the `RelayStub` class.

### HID USB relay (most common Chinese modules)

These show up as HID devices, not serial ports. Install the `hidapi` library:

```bash
sudo apt install -y libhidapi-hidraw0
pip install hidapi
```

Example implementation:

```python
import hid

class HidRelay:
    def __init__(self, vendor_id=0x16c0, product_id=0x05df):
        self._vid = vendor_id
        self._pid = product_id
        self._state = False

    @property
    def state(self):
        return self._state

    def _send(self, cmd):
        dev = hid.device()
        dev.open(self._vid, self._pid)
        dev.write(cmd)
        dev.close()

    def turn_on(self):
        if not self._state:
            self._send([0x00, 0xFF, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            self._state = True
            logging.info("RELAY -> ON")

    def turn_off(self):
        if self._state:
            self._send([0x00, 0xFD, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            self._state = False
            logging.info("RELAY -> OFF")
```

To find your relay's vendor/product ID:

```bash
lsusb
# Look for something like "16c0:05df" or "1a86:7523"
```

### Serial USB relay

If your relay appears as `/dev/ttyUSB1` (a second serial port):

```python
import serial

class SerialRelay:
    def __init__(self, port="/dev/ttyUSB1", baudrate=9600):
        self._ser = serial.Serial(port, baudrate, timeout=1)
        self._state = False

    @property
    def state(self):
        return self._state

    def turn_on(self):
        if not self._state:
            self._ser.write(b'\xA0\x01\x01\xA2')  # varies by module
            self._state = True
            logging.info("RELAY -> ON")

    def turn_off(self):
        if self._state:
            self._ser.write(b'\xA0\x01\x00\xA1')  # varies by module
            self._state = False
            logging.info("RELAY -> OFF")
```

### GPIO relay (if using a relay board wired to GPIO pins)

```bash
pip install RPi.GPIO
```

```python
import RPi.GPIO as GPIO

class GpioRelay:
    def __init__(self, pin=17):
        self._pin = pin
        self._state = False
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    @property
    def state(self):
        return self._state

    def turn_on(self):
        if not self._state:
            GPIO.output(self._pin, GPIO.HIGH)
            self._state = True
            logging.info("RELAY -> ON (GPIO %d)", self._pin)

    def turn_off(self):
        if self._state:
            GPIO.output(self._pin, GPIO.LOW)
            self._state = False
            logging.info("RELAY -> OFF (GPIO %d)", self._pin)
```

After implementing your relay class, update the `run()` function in `lux_controller.py`:

```python
# Change this line:
relay = RelayStub()

# To:
relay = HidRelay()     # or SerialRelay() or GpioRelay()
```

## 8. Run on boot with systemd

Create a systemd service so the controller starts automatically:

```bash
sudo nano /etc/systemd/system/lux-controller.service
```

Paste the following (adjust paths and flags to match your setup):

```ini
[Unit]
Description=Spirulina Lux Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/lux-controller
ExecStart=/home/pi/lux-controller/venv/bin/python lux_controller.py \
    --port /dev/ttyUSB0 \
    --min-lux 3000 \
    --max-lux 6000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lux-controller
sudo systemctl start lux-controller
```

Check status and logs:

```bash
sudo systemctl status lux-controller
journalctl -u lux-controller -f
```

## 9. Stable USB device names (optional)

If you have both the RS485 adapter and a USB relay plugged in, `/dev/ttyUSB0` and `/dev/ttyUSB1` can swap on reboot. Fix this with a udev rule:

```bash
# Find the serial number of each adapter
udevadm info -a /dev/ttyUSB0 | grep serial

# Create a rule
sudo nano /etc/udev/rules.d/99-usb-serial.rules
```

Example rule:

```
SUBSYSTEM=="tty", ATTRS{serial}=="AB0123XY", SYMLINK+="tty_lux_sensor"
SUBSYSTEM=="tty", ATTRS{serial}=="CD4567ZW", SYMLINK+="tty_relay"
```

Reload and replug:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then use `--port /dev/tty_lux_sensor` in your command.

## Troubleshooting

**"Permission denied" on /dev/ttyUSB0**
- Run `sudo usermod -aG dialout $USER` and reboot.

**"Cannot connect" or no response**
- Check wiring. RS485 A/B lines can be swapped.
- Try different baud rates: `--baudrate 4800`, `9600`, `19200`.
- Try `--slave-id 2` (some sensors ship with address 2).
- Try `--function-code 4` (input registers instead of holding).

**Readings are wrong (e.g. 42000 instead of 4200)**
- Your sensor may report in units of 0.1 lux. Use `--scale 0.1`.

**Light flickers on/off rapidly**
- Increase `--hysteresis` (e.g. 200).
- Increase `--min-switch-interval` (e.g. 120).
- Increase `--avg-window` (e.g. 60) to smooth out transients.

**/dev/ttyUSB numbers keep changing**
- Set up udev rules as described in section 9 above.
