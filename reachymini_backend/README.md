# 📦 Reachy Mini Backend - Installation & Setup

> **Welcome to Reachy Mini!** This project serves as an isolated environment (Python 3.10) to control your Reachy Mini robot without dependency conflicts with the main AI bot.

## 🚀 Quick Start

To start the Reachy Mini control daemon, simply run:

```bash
uv run reachy-mini-daemon
```

This will start the hardware interface which the main AI bot can interact with.

---

# 📖 Official Installation Guide

<div align="center">

| 🐧 **Linux** | 🍎 **macOS** | 🪟 **Windows** |
|:---:|:---:|:---:|
| ✅ Supported | ✅ Supported | ✅ Supported |

</div>

**Need help?** Feel free to open an [issue](https://github.com/pollen-robotics/reachy_mini/issues) if you encounter any problem.

## 1. 📋 Prerequisites

<div align="center">

| Tool | Version | Purpose |
|------|---------|---------|
| 🐍 **Python** | 3.10 - 3.12 | Run Reachy Mini SDK |
| 📂 **Git** | Latest | Download source code and apps |
| 📦 **Git LFS** | Latest | Download model assets |

</div>

### 🐍 Install Python

We'll use `uv` - a fast Python package manager that makes installation simple!

#### Step 1: Install uv

<details>
<summary>🐧 <strong>Linux</strong> & 🍎 <strong>macOS</strong></summary>

In your terminal, run:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

</details>

**✅ Verify installation:**
```bash
uv --version
```

#### Step 2: Install Python

In your terminal, run:
```bash
uv python install 3.10
```

## 2. 🏠 Set up a Virtual Environment

This environment is already initialized in this directory.

### Create the environment
```bash
uv venv .venv --python 3.10
```

### Activate the environment
```bash
source .venv/bin/activate
```

## 3. 🚀 Install Reachy Mini

### 📦 Install from PyPI
In your terminal, run:
```bash
uv pip install "reachy-mini"
```

If you want to use the simulation mode, you need to add the `mujoco` extra:
```bash
uv pip install "reachy-mini[mujoco]"
```

### 🐧 Linux Users: USB Permission Setup

<details>
<summary>🔧 <strong>Click here to set up USB permissions</strong></summary>

Run these commands in your terminal:

```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d3", MODE="0666", GROUP="dialout"
SUBSYSTEM=="usb", ATTRS{idVendor}=="38fb", ATTRS{idProduct}=="1001", MODE="0666", GROUP="dialout"' \
| sudo tee /etc/udev/rules.d/99-reachy-mini.rules

sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG dialout $USER
```

> ⚠️ **Important:** Log out and log back in for the changes to take effect!

</details>

## ❓ Troubleshooting
Encountering an issue? 👉 **[Check the Troubleshooting & FAQ Guide](https://github.com/pollen-robotics/reachy_mini/blob/main/docs/troubleshooting.md)**
