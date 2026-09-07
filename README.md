# Par-Avion GUI Suite

A high-performance, multithreaded Graphical User Interface for the Par-Avion SDR and Telemetry suite. Built specifically for **Kali Linux** and **Raspberry Pi OS**, it provides a modern, mouse-driven experience over the original CLI framework.

## 🚀 Features
* **Modern UI:** Responsive `CustomTkinter` interface adaptable to any display size.
* **Multithreaded:** CLI processing runs in background daemons. The UI *never* freezes.
* **Live Telemetry:** Real-time hardware monitoring (CPU & RAM) built into the sidebar.
* **Theme Switching:** Instant toggle between Light and Dark mode.
* **Integrated Log Output:** Real-time colored streaming of `stdout` and `stderr` directly into the bottom pane.

## 📦 Requirements
* **OS:** Debian-based Linux (Kali Linux, Raspberry Pi OS, Ubuntu)
* **Architecture:** x86_64, ARM32, ARM64
* **Python:** 3.8+

## ⚙️ Installation

We provide a self-contained install script that handles OS detection, package installation, virtual environment (`.venv`) configuration, and desktop launcher creation.

```bash
git clone https://github.com/your-username/par-avion-gui.git
cd par-avion-gui
chmod +x install.sh
./install.sh
```

## 🖥 Usage
If the desktop launcher was created successfully, simply search for **Par-Avion GUI** in your application menu. 

To run manually via terminal:
```bash
source .venv/bin/activate
python main.py
```
