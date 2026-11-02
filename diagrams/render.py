#!/usr/bin/env python3
"""Renderiza los diagramas .html a PNG, con el alto ajustado al contenido.

Por que no se usa `chrome --screenshot` a secas: ese modo usa un viewport de
alto fijo, asi que la captura sale siempre del mismo alto y deja una franja
de fondo vacia abajo. Aca se abre Chrome con el protocolo de DevTools, se le
pregunta el alto real del documento y se recorta exacto con Pillow.
"""

import base64
import io
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

import websocket
from PIL import Image

SITE = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
BUILD = os.environ.get("BUILD_DIR", "/tmp/lautea-v3")
CHROME = os.environ.get(
    "CHROME",
    os.path.expanduser("~/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome"),
)

# html de entrada -> png de salida (dentro de assets/images/)
JOBS = [
    ("te-verde.html", "diagram-te-verde.png"),
    ("hebras-vs-saquito.html", "diagram-hebras-vs-saquito.png"),
    ("green-tea.html", "diagram-green-tea.png"),
    ("loose-leaf-vs-bags.html", "diagram-loose-leaf-vs-bags.png"),
]


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Chrome:
    def __init__(self, port):
        self.port = port
        # Perfil nuevo en cada corrida. Si se reusa el mismo directorio, un
        # Chrome anterior que no cerro bien deja el SingletonLock puesto y el
        # nuevo arranca sin abrir el puerto de DevTools.
        self.profile = os.path.join(BUILD, f".chrome-profile-{port}")
        shutil.rmtree(self.profile, ignore_errors=True)
        self.proc = subprocess.Popen(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                "--window-size=1200,900",
                f"--remote-debugging-port={port}",
                "--user-data-dir=" + self.profile,
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.ws = None
        last = None
        for _ in range(80):
            try:
                raw = urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/list", timeout=1
                ).read()
                pages = [t for t in json.loads(raw) if t["type"] == "page"]
                if pages:
                    # suppress_origin: sin esto el cliente manda cabecera
                    # Origin y Chrome 145+ responde 403 Forbidden al handshake.
                    self.ws = websocket.create_connection(
                        pages[0]["webSocketDebuggerUrl"],
                        timeout=30,
                        suppress_origin=True,
                    )
                    return
            except websocket.WebSocketException as exc:
                last = exc
            except Exception as exc:
                last = exc
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"Chrome termino con codigo {self.proc.returncode} antes de "
                    f"abrir el puerto de DevTools ({port})"
                )
            time.sleep(0.25)
        raise RuntimeError(
            f"Chrome no respondio al protocolo de DevTools ({port}): {last!r}"
        )

    def send(self, method, **params):
        self._id = getattr(self, "_id", 0) + 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def kill(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def render(chrome, url, out_path, width=1200):
    chrome.send("Page.enable")
    chrome.send("Page.navigate", url=url)
    # Esperar a que las fuentes esten listas: sin esto la captura puede salir
    # con la tipografia de fallback y el alto medido seria el equivocado.
    for _ in range(60):
        r = chrome.send(
            "Runtime.evaluate",
            expression="document.fonts.status === 'loaded' && !!document.body",
            returnByValue=True,
        )
        if r.get("result", {}).get("value") is True:
            break
        time.sleep(0.15)
    time.sleep(0.25)

    # El ancho real hay que fijarlo ANTES de medir: la ventana de Chrome
    # arranca en 1200 y si el diagrama tuviera otro ancho el texto cortaria
    # distinto. Ademas se achica el alto a 100px, porque scrollHeight nunca
    # devuelve menos que la ventana: con una ventana alta, un contenido corto
    # informa el alto de la ventana y sobra fondo abajo.
    chrome.send(
        "Emulation.setDeviceMetricsOverride",
        width=width,
        height=100,
        deviceScaleFactor=1,
        mobile=False,
    )
    time.sleep(0.2)
    metrics = chrome.send(
        "Runtime.evaluate",
        expression="JSON.stringify({h: Math.ceil(document.documentElement.scrollHeight)})",
        returnByValue=True,
    )
    height = json.loads(metrics["result"]["value"])["h"]
    chrome.send("Emulation.clearDeviceMetricsOverride")
    chrome.send(
        "Emulation.setDeviceMetricsOverride",
        width=width,
        height=height,
        deviceScaleFactor=2,  # 2x: nitido en pantallas retina
        mobile=False,
    )
    time.sleep(0.2)
    # Ojo: el clip va con scale 1. El factor 2x ya lo aporta deviceScaleFactor;
    # con scale 2 se multiplican y la captura sale al doble de ancho, mostrando
    # solo la mitad izquierda de la pagina. El campo es obligatorio si hay clip.
    shot = chrome.send(
        "Page.captureScreenshot",
        format="png",
        clip={
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "scale": 1,
        },
        captureBeyondViewport=True,
    )
    raw = base64.b64decode(shot["data"])

    img = Image.open(io.BytesIO(raw)).convert("RGB")
    # Recorte exacto por si la captura excede el alto medido.
    img = img.crop((0, 0, min(img.width, width * 2), min(img.height, height * 2)))
    img.save(out_path, "PNG", optimize=True)
    return img.size


def main():
    src = os.path.join(SITE, "diagrams")
    for f in os.listdir(src):
        if f.endswith((".html", ".css")):
            shutil.copy(os.path.join(src, f), os.path.join(BUILD, f))

    # Los .html cargan las fuentes y el CSS por rutas absolutas (/fonts/...),
    # asi que necesitan servirse por HTTP. Se levanta uno efimero en localhost.
    port_http = free_port()
    server = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-m",
            "http.server",
            str(port_http),
            "--bind",
            "127.0.0.1",
            "-d",
            BUILD,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port_http}"
    for _ in range(40):
        try:
            urllib.request.urlopen(f"{base}/base.css", timeout=1).read(1)
            break
        except Exception:
            if server.poll() is not None:
                raise RuntimeError("El servidor HTTP local no pudo arrancar")
            time.sleep(0.25)
    else:
        raise RuntimeError(f"El servidor HTTP no respondio en {base}")

    chrome = Chrome(free_port())
    try:
        for html, png in JOBS:
            out = os.path.join(SITE, "assets", "images", png)
            size = render(chrome, f"{base}/{html}", out)
            print(f"  {html:28} -> {png:36} {size[0]}x{size[1]}")
        print(f"{len(JOBS)}/{len(JOBS)} diagramas renderizados.")
    finally:
        chrome.kill()
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
