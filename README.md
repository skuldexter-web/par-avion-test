# PAR AVION — Tactical RF & Telemetry Suite

A lightweight Python/CustomTkinter GUI for Linux and Raspberry Pi OS, built around the original PAR AVION receive-only RF and telemetry modules.

## Features

- Modern CustomTkinter sidebar GUI with instant light/dark mode switching.
- Responsive layout for desktop and smaller touch displays.
- Background-thread execution for hardware scans, SDR operations, TLE retrieval, ADS-B/AIS tracking, audio pipelines and decoders.
- Live system telemetry (CPU, RAM, OS/architecture).
- Embedded timestamped terminal/log console with status levels.
- Start, Stop/Cancel, Clear Logs and Copy Output controls.
- Airplanes: ADS-B / dump1090 integration.
- Waterfalls: RTL-SDR FFT spectrum and scrolling waterfall, with a simulated fallback when hardware is absent.
- Radio: AM/FM rtl_fm + sox receive chain.
- Maritime: AIS / rtl_ais integration.
- ISS: CelesTrak TLE refresh, current sub-satellite position and GPS-based pass prediction.
- SSTV: Martin/Scottie/Robot decoder controls.
- Morse: CW decoder controls.
- Hardware diagnostics for SDR, GPS, DVB driver conflicts and dump1090.
- Original CLI/TUI implementation retained under `core/`.

## Screenshots

Add project screenshots here, for example:

`![Dashboard](assets/screenshot-dashboard.png)`

`![Waterfall](assets/screenshot-waterfall.png)`

## Prerequisites

- Kali Linux / Debian-family Linux or Raspberry Pi OS.
- Python 3.8+ (Python 3.10+ recommended).
- For live RF features: supported SDR hardware and the relevant Linux receiver tools.
- For GPS features: gpsd-compatible GPS hardware/daemon.

## Installation

```bash
chmod +x install.sh
./install.sh
```

The installer detects the Debian-family environment, installs system dependencies with `apt`, creates `.venv` to comply with PEP 668, installs Python requirements inside the environment, and attempts to add a per-user desktop launcher.

## Usage

```bash
.venv/bin/python main.py
```

The GUI is the default entry point. The original terminal interface remains available:

```bash
.venv/bin/python -m core.par_avion
```

## Architecture

```text
.
├── assets/              # Launcher and application assets
├── core/                # Original CLI/TUI modules
│   ├── modules/
│   └── par_avion.py
├── gui/                 # CustomTkinter GUI
├── main.py              # GUI entry point
├── install.sh           # Debian/Kali/Raspberry Pi installer
├── requirements.txt
├── .gitignore
└── README.md
```

### Threading model

Tk/CustomTkinter widgets are only touched from the GUI thread. Blocking or CPU-heavy backend operations are submitted to a `ThreadPoolExecutor`; results are returned to the GUI with `after()`. This keeps the event loop responsive while receivers, network operations and device scans run.

### Receive-only design

The bundled PAR AVION application is designed around receiving/decoding already-broadcast data. It does not provide an RF transmit control path.

## Troubleshooting

- **No SDR detected:** check `lsusb`, reconnect the dongle, and review the Hardware page.
- **RTL-SDR claimed by DVB:** follow the installer/kernel-module warning and reboot after blacklisting the DVB driver if required by your distribution.
- **Radio says tools are missing:** confirm `rtl_fm` and `play` are on `PATH`.
- **No GPS fix:** start/configure gpsd and verify the receiver appears under `/dev/ttyUSB*` or `/dev/ttyACM*`.
- **Audio input unavailable:** verify PortAudio/ALSA and the selected microphone device.

## License

Add the project's chosen license before publishing to GitHub.
