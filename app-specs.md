
# Especificaciones: PyAudioGrabber (CLI)

## 1. Stack Tecnológico

* **Lenguaje:** Python 3.10+ (optimizado para arquitectura `arm64`).
* **Librería Core:** `PyObjC` (específicamente los wrappers `pyobjc-framework-ScreenCaptureKit` y `pyobjc-framework-AVFoundation`).
* **Interfaz CLI:** `argparse` (nativo de Python).
* **Procesamiento de Audio:** `SoundFile` o `Wave` para la escritura a disco.

## 2. Flujo de Trabajo del Script

1. **Validación de Permisos:** El script verificará si la Terminal (o el IDE) tiene permisos de "Grabación de Pantalla".
2. **Identificación del Proceso:** Buscará el `bundleID` del navegador (Safari, Chrome, etc.).
3. **Configuración de Stream:** Iniciará un `SCStream` silencioso que solo capture el audio del navegador.
4. **Captura en Bucle:** Los buffers de audio se recibirán en un callback y se escribirán en tiempo real.
5. **Cierre Seguro:** Al presionar `Ctrl+C`, se cerrará el archivo correctamente para no corromperlo.

---

## 3. Comandos y Argumentos

La herramienta se ejecutará de la siguiente forma:

```bash
python grabber.py --name "mi_grabacion.wav" --path "~/Downloads" --browser "Google Chrome"

```

### Argumentos definidos:

| Flag | Descripción | Default |
| --- | --- | --- |
| `--name`, `-n` | Nombre del archivo de salida. | `output.wav` |
| `--path`, `-p` | Directorio donde se guardará. | `./` |
| `--browser`, `-b` | Nombre del navegador a capturar. | `Safari` |
| `--bitrate` | Calidad del audio (si se usa AAC). | `192k` |

---

## 4. Requisitos de Implementación (Código Crítico)

Para que esto funcione en Apple Silicon sin drivers virtuales (como BlackHole), el script debe implementar un **Delegate** de Objective-C en Python para recibir los frames de audio:

```python
import ScreenCaptureKit
import AVFoundation
from PyObjC import NSObject

class AudioCaptureDelegate(NSObject):
    def stream_didOutputSampleBuffer_ofType_(self, stream, sampleBuffer, type):
        if type == ScreenCaptureKit.SCStreamOutputTypeAudio:
            # Aquí se procesan los datos raw de audio
            self.save_to_file(sampleBuffer)

```

---

## 5. Consideraciones para Apple Silicon

* **Entorno Virtual:** Es crucial crear un `venv` que sea `arm64`. Puedes verificarlo con `python -c "import platform; print(platform.machine())"`.
* **Firmado de Binarios:** A veces, macOS bloquea el acceso a la grabación de pantalla si el intérprete de Python no tiene un "Entitlement" de firma. Puede que necesites ejecutar el script a través de una terminal con permisos totales.

## 6. Ventajas de este enfoque CLI

* **Ligero:** No consume recursos en renderizar ventanas.
* **Automatizable:** Puedes programar grabaciones mediante `cron` o lanzarlas remotamente vía SSH.
* **Sin Drivers:** Al usar `ScreenCaptureKit`, no necesitas instalar software adicional como Loopback o BlackHole.

