# Truco Laya

Juego web de truco argentino para **2, 4 o 6 jugadores**. Un humano ocupa el primer asiento; los demás son jugadores de IA controlados por [Laya](https://github.com/NandhaKishorM/laya). Los equipos se alternan alrededor de la mesa: asientos pares contra impares.

## Instalación sin Docker (Windows, Linux y macOS)

Necesitás [Python 3.10 o superior](https://www.python.org/downloads/) y [Node.js 20.9 o superior con npm](https://nodejs.org/en/download). [Descargá el proyecto como ZIP](https://github.com/guillermojmontenegro-hub/TrucoLaya/archive/refs/heads/main.zip) y descomprimilo, o clonalo con Git. Después abrí una terminal en la carpeta `TrucoLaya` y ejecutá **un solo comando**:

```powershell
# Windows (PowerShell)
py -3 run.py
```

```bash
# Linux y macOS
python3 run.py
```

El lanzador crea el entorno Python, instala Laya y las dependencias web, inicia ambos servidores y abre <http://localhost:3000>. Las siguientes veces reutiliza lo instalado. Para detener el juego, presioná `Ctrl+C`. No requiere Docker, privilegios de administrador ni comandos distintos para backend y frontend. Se necesita conexión a internet durante la instalación y la primera partida: Laya descarga su checkpoint multilingüe desde Hugging Face en su primera decisión; puede tardar varios minutos y necesita memoria y espacio en disco suficientes. Si falla, el juego muestra el error y permite reintentar. La documentación de la API está en <http://localhost:8000/docs>.

Si `python3 -m venv` falla en Debian/Ubuntu, instalá el paquete `python3-venv` del sistema y ejecutá el lanzador otra vez. Para instalar sin iniciar el juego, agregá `--install-only`; para evitar que se abra el navegador, agregá `--no-browser`. Si los puertos 3000 u 8000 están ocupados, elegí otros con `--port 3001 --api-port 8001`.

### Opción con Docker

```bash
git clone https://github.com/guillermojmontenegro-hub/TrucoLaya.git
cd TrucoLaya
docker compose up --build
```

En Docker, el checkpoint descargado queda en el volumen `laya-models`.

### Desarrollo manual

Requisitos: Python 3.12, Node.js 22 y npm.

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/uvicorn truco.api:app --reload
```

En otra terminal:

```bash
cd frontend
npm ci
npm run dev
```

La app web usa el proxy `/api` de Next.js. Para cambiar la dirección del backend, definí `API_INTERNAL_URL` al iniciar Next.js.

## Reglas incluidas

- Baraja española de 40 cartas, tres cartas por jugador, tres bazas y jerarquía argentina de cartas.
- Partida a 30 puntos. Truco, retruco y vale cuatro; aceptar, rechazar, subir o ir al mazo.
- Envido simple de dos puntos cuando se acepta, uno si se rechaza. Se permite durante la primera baza antes de que haya truco. El valor de cada equipo es la mejor mano individual de sus integrantes. En empate gana el equipo del jugador mano.
- Si empatan una baza, la siguiente define; si persiste el empate, prevalece la primera baza ganada o el equipo del mano.

Esta primera versión omite flor, real envido, falta envido y partidas humanas multijugador. En mesas de 4 o 6, el humano comparte equipo con compañeros Laya. Las partidas viven en memoria del proceso API; reiniciar el servidor las borra.

## Cómo decide Laya

Laya es un motor de decisiones tipadas, no un modelo que genera texto libre. La [API `Router.predict`](https://github.com/NandhaKishorM/laya#quickstart) recibe un estado y preguntas de tipo `choice`, `score` o `noul`; nuestro adaptador usa **`choice`**. Cada turno, el motor de reglas produce acciones legales como `play:7-espada`, `truco`, `envido`, `accept` o `reject`. El adaptador entrega a Laya una pregunta con **sólo esas opciones** y un contexto en español: cartas propias, cartas públicas en la mesa, bazas, puntajes, nivel de truco y canto pendiente. Laya devuelve la opción elegida; el dominio vuelve a validarla antes de ejecutar el movimiento.

Se fuerza `model="multilingual"` para las instrucciones en español. El `Router` se crea al primer turno de IA y reutiliza el modelo durante el proceso. El checkpoint base es generalista y no fue entrenado específicamente para truco: sus jugadas pueden ser débiles. Para mejorar estrategia, se podría recopilar partidas etiquetadas y ajustar un checkpoint de Laya siguiendo su [guía de fine-tuning](https://github.com/NandhaKishorM/laya#fine-tune-for-better-accuracy). El backend nunca envía a la IA cartas ocultas de otros jugadores.

## Arquitectura

```text
frontend/ (Next.js, React, TypeScript)
  app/page.tsx       interfaz y cliente HTTP
  next.config.ts     proxy /api hacia el backend
            │
            ▼
backend/truco/api.py      FastAPI, contratos y errores HTTP
backend/truco/service.py  sesiones, turnos de IA, sincronización
backend/truco/domain.py   cartas, reglas, acciones legales y puntajes
backend/truco/ai.py       puerto DecisionMaker + adaptador Laya
            │
            ▼
       paquete laya / checkpoint multilingüe
```

`run.py` prepara las dependencias y administra los dos procesos locales en Windows, Linux y macOS.

El dominio no importa FastAPI ni Laya. `GameService` depende del contrato `DecisionMaker`, lo que permite probar partidas con una implementación determinista. El adaptador Laya sólo conoce las acciones legales y el estado público que necesita. Cada sesión tiene un bloqueo para evitar dos acciones simultáneas; las sesiones se guardan en memoria. Para desplegar múltiples réplicas del backend se necesitaría un almacén compartido y un mecanismo de bloqueo distribuido.

## Calidad y entrega

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/pytest tests -q
cd ../frontend
npm run lint
npm run typecheck
npm run build
```

GitHub Actions ejecuta lint, pruebas y compilación en cada push y pull request. Si CI termina correctamente en `main`, CD construye y publica imágenes Docker de API y web en GHCR con la etiqueta del commit. No se despliega automáticamente a un servidor porque el repositorio no contiene credenciales ni destino de despliegue.
