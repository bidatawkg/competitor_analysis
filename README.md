# Proyecto de Análisis de Competidores de Casino

## 1. Descripción General

Este proyecto es una solución integral para el análisis de competidores en el mercado de casinos en línea, diseñada para el departamento de Datos e Inteligencia Artificial de YYY Casino. El sistema automatiza la extracción, almacenamiento, comparación y visualización de datos sobre bonos y promociones de los principales competidores por país.

El objetivo principal es proporcionar a YYY Casino una herramienta poderosa para monitorear las estrategias de captación de la competencia, permitiendo una adaptación rápida y eficaz a las condiciones del mercado.

### Características Principales

- **Scraping Robusto**: Utiliza Playwright para la extracción de datos de sitios web dinámicos y con alto contenido de JavaScript, simulando una interacción humana para evitar bloqueos.
- **Integración de VPN/Proxy**: Diseñado para integrarse con servicios de VPN o proxies para realizar el scraping desde ubicaciones geográficas específicas (ej. Emiratos Árabes Unidos).
- **Base de Datos Histórica**: Almacena todos los datos extraídos en una base de datos SQLite, creando un registro histórico de las promociones de la competencia.
- **Análisis Comparativo**: Compara automáticamente los datos nuevos con los existentes para identificar nuevas promociones, actualizaciones o eliminaciones.
- **Dashboard Interactivo**: Genera un dashboard estático en HTML con visualizaciones interactivas (gráficos y tablas) para un análisis intuitivo y amigable de los datos.
- **Escalabilidad**: La arquitectura modular permite agregar fácilmente nuevos competidores y países para el análisis.

## 2. Estructura del Proyecto

El proyecto está organizado en los siguientes directorios y archivos clave:

```
competitor_analysis/
│
├── scraper/
│   ├── __init__.py
│   └── competitor_scraper.py   # Módulo de scraping con Playwright
│
├── database/
│   ├── __init__.py
│   └── db_manager.py           # Módulo de gestión de la base de datos SQLite
│
├── dashboard/
│   ├── index.html              # Plantilla del dashboard HTML
│   └── generate_dashboard.py   # Script para generar el dashboard con datos reales
│
├── output/
│   ├── reports/                # Directorio para informes futuros
│   ├── *.json                  # Archivos JSON con datos extraídos y de comparación
│   └── *.csv                   # Archivos CSV con datos extraídos
│
├── main.py                     # Script principal que orquesta todo el proceso
├── test_system.py              # Script de prueba con datos de muestra
├── competitors.db              # Base de datos SQLite
├── scraper.log                 # Log del proceso de scraping
└── README.md                   # Este archivo
```

### Componentes Clave

- **`scraper/competitor_scraper.py`**: Contiene la clase `CompetitorScraper` que se encarga de navegar a las URLs de los competidores, manejar pop-ups y extraer la información de las promociones. Está diseñado para ser resistente a bloqueos mediante el uso de cabeceras de navegador realistas y tiempos de espera aleatorios.

- **`database/db_manager.py`**: Contiene la clase `DatabaseManager` que gestiona todas las interacciones con la base de datos SQLite. Se encarga de crear las tablas, insertar y actualizar promociones, realizar comparaciones y exportar los datos a formatos CSV y JSON.

- **`main.py`**: Es el punto de entrada principal del sistema. Orquesta el flujo de trabajo completo: ejecuta el scraper, almacena los datos en la base de datos, realiza la comparación y genera los archivos de salida.

- **`dashboard/generate_dashboard.py`**: Este script toma los archivos JSON generados por el `db_manager`, los inyecta en una plantilla HTML (`index.html`) y produce el archivo final del dashboard (`dashboard_current.html`).

## 3. Cómo Utilizar el Proyecto

### Requisitos Previos

- Python 3.8+
- Navegadores compatibles con Playwright (Chromium, Firefox, WebKit)

### Pasos para la Ejecución

1.  **Instalar Dependencias**: Abra una terminal en el directorio raíz del proyecto y ejecute:
    ```bash
    pip install -r requirements.txt
    python -m playwright install
    ```
    *(Nota: Se deberá crear un archivo `requirements.txt` con las bibliotecas necesarias: `playwright`, `beautifulsoup4`, `lxml`, `aiohttp`)*

2.  **Configurar Competidores**: Abra el archivo `scraper/competitor_scraper.py` y modifique el diccionario `self.competitors` para agregar o cambiar los competidores y países que desea analizar.

3.  **Configurar Proxies/VPN (Opcional pero Recomendado)**: En `scraper/competitor_scraper.py`, reemplace la lista `self.uae_proxies` con los datos de su proveedor de VPN o proxy. Para activar el uso de proxy, asegúrese de que el parámetro `use_proxy` esté en `True` al instanciar el `CompetitorScraper`.

4.  **Ejecutar el Análisis Completo**: Para iniciar el proceso de scraping y análisis, ejecute el script principal desde la terminal:
    ```bash
    python main.py --country UAE
    ```
    - Puede cambiar el país con el argumento `--country`.
    - Use `--use-proxy` para activar el proxy si no está activado por defecto.

5.  **Generar el Dashboard**: Una vez que el proceso principal ha finalizado y ha generado los archivos de datos en el directorio `output/`, puede generar o actualizar el dashboard ejecutando:
    ```bash
    python dashboard/generate_dashboard.py
    ```

6.  **Ver el Dashboard**: Abra el archivo `dashboard/dashboard_current.html` en su navegador web para ver los resultados del análisis.

### Ejecución de Prueba con Datos de Muestra

Para probar rápidamente la funcionalidad de la base de datos y la generación del dashboard sin ejecutar el scraper (que puede tardar), puede usar el script de prueba:

```bash
python test_system.py
```

Este comando utilizará datos de muestra predefinidos para poblar la base de datos, generar los archivos de salida y permitirle crear un dashboard de demostración.

## 4. Detalles del Dashboard

El dashboard estático (`dashboard_current.html`) es el producto final y está diseñado para ser auto-contenido y fácilmente desplegable en cualquier servidor web.

### Secciones del Dashboard

- **Cabecera**: Muestra el título, la fecha de la última actualización y un selector de país (funcionalidad preparada para futura expansión).
- **Tarjetas de Estadísticas**: Ofrece una vista rápida de los KPIs más importantes: total de promociones, número de competidores, nuevas promociones detectadas y el valor promedio de los bonos.
- **Gráficos Interactivos**:
    - **Promociones por Competidor**: Un gráfico de dona que muestra la distribución de la cuota de mercado de las promociones.
    - **Tipos de Bonos**: Un gráfico de barras que desglosa las promociones por tipo (Bienvenida, Cashback, etc.), revelando las estrategias más comunes.
- **Insights Clave**: Tarjetas que resumen automáticamente los hallazgos más importantes del análisis, como qué competidor es el más agresivo o qué tipo de bono es tendencia.
- **Tabla de Promociones**: Una lista detallada de todas las promociones activas. Incluye un sistema de filtros para navegar fácilmente por tipo de bono. Cada tarjeta de promoción muestra el título, competidor, descripción, monto del bono y las condiciones.

## 5. Escalabilidad y Futuras Mejoras

- **Añadir más Países**: Simplemente agregue una nueva entrada en el diccionario `self.competitors` y ejecute el `main.py` con el nuevo país como argumento.
- **Mejorar la Extracción de Datos**: Los selectores de CSS en `scraper/competitor_scraper.py` pueden ser refinados para cada sitio de competidor para una extracción de datos más precisa.
- **Análisis de Sentimiento**: Se podría integrar una biblioteca de NLP para analizar el texto de las promociones y determinar el 
