#!/bin/bash

# Script de instalación para el Proyecto de Análisis de Competidores
# YYY Casino - Departamento de Datos e IA

echo "🎰 Instalando Proyecto de Análisis de Competidores - YYY Casino"
echo "=============================================================="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado"
    exit 1
fi

echo "✅ Python 3 encontrado: $(python3 --version)"

# Crear entorno virtual (opcional)
read -p "¿Desea crear un entorno virtual? (y/n): " create_venv
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Entorno virtual activado"
fi

# Instalar dependencias de Python
echo "📦 Instalando dependencias de Python..."
pip install -r requirements.txt

# Instalar navegadores de Playwright
echo "🌐 Instalando navegadores de Playwright..."
python3 -m playwright install

# Instalar dependencias del sistema para Playwright
echo "🔧 Instalando dependencias del sistema..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y libgtk-4-1 libatomic1 libevent-2.1-7 libwebpdemux2 libenchant-2-2 libsecret-1-0
fi

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p output/reports
mkdir -p logs

# Configurar permisos
chmod +x main.py
chmod +x test_system.py
chmod +x dashboard/generate_dashboard.py

echo ""
echo "✅ Instalación completada!"
echo ""
echo "📋 Próximos pasos:"
echo "1. Configurar competidores en scraper/competitor_scraper.py"
echo "2. Configurar proxies/VPN si es necesario"
echo "3. Ejecutar: python3 test_system.py (para prueba con datos de muestra)"
echo "4. Ejecutar: python3 main.py --country UAE (para análisis real)"
echo "5. Generar dashboard: python3 dashboard/generate_dashboard.py"
echo ""
echo "📖 Consulte README.md para más información detallada"
echo "=============================================================="
