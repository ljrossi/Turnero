#!/bin/bash

echo "=============================="
echo "  SHIFT SCHEDULER - SETUP"
echo "=============================="
echo ""

# Verificar si python3 existe
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed."
    echo ""
    echo "Please install Python 3 and Tkinter using your package manager:"
    echo "  - Debian/Ubuntu: sudo apt-get install python3 python3-pip python3-tk"
    echo "  - Fedora:       sudo dnf install python3 python3-pip python3-tkinter"
    echo "  - Arch:         sudo pacman -S python python-pip tk"
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[OK] Python3 found: $(python3 --version)"

# Verificar Tkinter (en Linux a veces viene por separado)
echo "[CHECK] Verifying Tkinter module..."
python3 -c "import tkinter" 2> /dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Tkinter module not found."
    echo ""
    echo "Tkinter is usually installed separately on Linux."
    echo "Run the appropriate command for your distribution:"
    echo "  - Debian/Ubuntu: sudo apt-get install python3-tk"
    echo "  - Fedora:       sudo dnf install python3-tkinter"
    echo "  - Arch:         sudo pacman -S tk"
    read -p "Press Enter to exit..."
    exit 1
fi
echo "[OK] Tkinter is available."

# Instalar ReportLab
echo ""
echo "[INSTALL] Installing ReportLab (PDF generator)..."
python3 -m pip install --upgrade reportlab
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install ReportLab."
    echo "Please try manually: python3 -m pip install reportlab"
    read -p "Press Enter to exit..."
    exit 1
fi

# Ejecutar la aplicación
echo ""
echo "[RUN] Starting the application..."
echo "=============================="
python3 main.py

# Reemplaza "main.py" por el nombre real de tu archivo principal (ej. turnero.py)

echo ""
echo "=============================="
echo "Application closed."
read -p "Press Enter to exit..."