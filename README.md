# PyAudioGrabber

Herramienta CLI para capturar audio exclusivamente de navegadores web en macOS, usando la API nativa **ScreenCaptureKit** a través de PyObjC. No requiere drivers virtuales como BlackHole o Soundflower.

## Requisitos

- **macOS 12.3+** (Monterey o superior)
- **Python 3.10+** (arquitectura arm64 para Apple Silicon)
- Permisos de "Grabación de Pantalla" habilitados

## Instalación

Usando `uv`:

```bash
# Clonar el repositorio
cd catch-browser-sound

# Instalar dependencias
uv sync
```

## Uso

### Capturar audio de un navegador

```bash
# Capturar audio de Safari (por defecto)
uv run grabber

# Capturar audio de Google Chrome
uv run grabber --browser "Google Chrome"

# Especificar nombre y ruta del archivo
uv run grabber --name "podcast.wav" --path ~/Music --browser "Google Chrome"

# Ver todos los argumentos disponibles
uv run grabber --help
```

### Argumentos

| Flag | Descripción | Default |
|------|-------------|---------|
| `-n`, `--name` | Nombre del archivo de salida | `output.wav` |
| `-p`, `--path` | Directorio donde se guardará | `./` |
| `-b`, `--browser` | Navegador a capturar | `Safari` |
| `--sample-rate` | Frecuencia de muestreo (Hz) | `48000` |
| `--channels` | Canales de audio (1=mono, 2=stereo) | `2` |
| `--list-browsers` | Listar navegadores disponibles | - |

### Navegadores soportados

- Safari
- Google Chrome
- Firefox
- Microsoft Edge
- Arc
- Brave Browser
- Opera
- Vivaldi

### Detener la grabación

Presiona `Ctrl+C` para detener la grabación. El archivo se guardará automáticamente.

## Permisos

La primera vez que ejecutes la aplicación, macOS solicitará permisos de "Grabación de Pantalla". Para habilitarlos:

1. Abre **Configuración del Sistema** > **Privacidad y Seguridad** > **Grabación de Pantalla**
2. Habilita el acceso para **Terminal** (o tu IDE)
3. Reinicia la terminal y ejecuta el comando nuevamente

## Arquitectura

```
src/grabber/
├── __init__.py      # Versión del paquete
├── __main__.py      # Entry point CLI
├── cli.py           # Parsing de argumentos
├── permissions.py   # Validación de permisos macOS
├── process.py       # Búsqueda de navegadores
├── capture.py       # Captura de audio con SCStream
└── writer.py        # Escritura WAV asíncrona
```

## Cómo funciona

1. **Identificación del proceso**: Busca el navegador por su Bundle ID
2. **Filtrado**: Crea un filtro que solo captura audio del navegador seleccionado
3. **Captura**: Usa `SCStream` para recibir buffers de audio en tiempo real
4. **Escritura**: Escribe los datos de forma asíncrona a un archivo WAV

## Ventajas

- **Sin drivers**: No necesitas BlackHole, Soundflower ni Loopback
- **Audio limpio**: Captura solo el audio del navegador, sin notificaciones ni otras apps
- **Nativo Apple Silicon**: Optimizado para procesadores M1/M2/M3
- **Calidad de estudio**: Audio PCM digital sin conversiones analógicas

## Licencia

MIT



