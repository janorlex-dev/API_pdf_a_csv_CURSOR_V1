# PDF a CSV API

API para convertir exámenes en PDF a CSV de forma **literal**. Sirve para **cualquier asignatura**
y **cualquier número de preguntas** (20+2 reservas, 25+2, 50 del común de abogacía, etc.),
siempre que el PDF tenga capa de texto y el formato tipo test esperado.

Stack: **Python 3.12 + FastAPI + PyMuPDF (fitz)** desplegado en **Vercel Serverless**. Almacenamiento de los CSV en **Vercel Blob** con URL no listable (token aleatorio en la ruta).

- Cabecera por defecto: `numero,pregunta,a,b,c,d,correcta,materia` (configurable por petición).
- Extrae **solo preguntas numeradas** (`1.-`, `2.`, …) con enunciado literal y opciones **a, b, c, d** (4 opciones en v1).
- La columna `correcta` se extrae **automáticamente** de la última hoja del PDF; se puede **aportar manualmente** (JSON o texto tipo `1.B`).
- Preguntas mal parseadas **se incluyen** con campos vacíos y se listan en `preguntas_no_parseadas` (nunca se inventan).
- Web mínima responsive (PC y Android) en `/` (redirige a `/index.html`).

---

## Índice

1. [Estructura del proyecto](#estructura-del-proyecto)
2. [Endpoints](#endpoints)
3. [Variables de entorno](#variables-de-entorno)
4. [Ejecución local](#ejecución-local)
5. [Despliegue en Vercel desde GitHub](#despliegue-en-vercel-desde-github)
6. [Uso remoto (PC y Android)](#uso-remoto-pc-y-android)
7. [Reglas de Cursor](#reglas-de-cursor)
8. [Limitaciones y notas](#limitaciones-y-notas)

---

## Estructura del proyecto

```
.
├── api/
│   └── index.py                    # FastAPI app: /api/health, /api/convert, /api/preview, /docs
├── lib/
│   ├── pdf_parser.py               # Extracción de texto literal con PyMuPDF (fitz)
│   ├── plantilla.py                # Detecta la plantilla de respuestas en las últimas hojas
│   ├── extractor_estructurado.py   # Parsea preguntas 1.- a) b) c) d), con parse_ok
│   ├── csv_builder.py              # QUOTE_ALL + UTF-8 con BOM
│   ├── validator.py                # Comprobaciones (filas, columnas, repetidas, vacías)
│   ├── storage.py                  # Subida a Vercel Blob
│   └── models.py                   # Esquemas Pydantic
├── public/
│   ├── index.html                  # Web mínima
│   ├── styles.css
│   └── app.js
├── docs/
│   ├── base_pdf_a_csv.txt          # Script Python de referencia (fuente del diseño)
│   └── historico/                  # Chats previos archivados (no se cargan)
├── .cursor/rules/                  # Reglas Cursor (proyecto, python, api, dominio, script-base)
├── requirements.txt
├── runtime.txt                     # python-3.12
├── vercel.json                     # Rewrite / → index.html
├── .env.example
└── README.md
```

## Endpoints

| Método | Ruta             | Descripción                                                  |
| ------ | ---------------- | ------------------------------------------------------------ |
| `GET`  | `/`              | Web mínima (formulario subir PDF → descargar CSV)            |
| `GET`  | `/api/health`    | Estado del servicio                                          |
| `POST` | `/api/convert`   | Convierte un PDF a CSV y lo sube a Vercel Blob               |
| `POST` | `/api/preview`   | Igual que `/convert` pero devuelve N filas y NO sube         |
| `GET`  | `/docs`          | Swagger UI auto-generado por FastAPI                         |
| `GET`  | `/openapi.json`  | Esquema OpenAPI                                              |

### Campos del formulario (`multipart/form-data`)

- `file` *(obligatorio)* — el PDF.
- `cabecera` *(opcional)* — cabecera CSV separada por comas. Ej: `numero,pregunta,a,b,c,d,correcta,bloque`.
- `materia` *(opcional)* — valor fijo para la columna `materia` / `bloque` / `tema` / `asignatura`. Ej: `comun`, `penal`.
- `respuestas` *(opcional)* — plantilla manual si el PDF **no trae solucionario al final**. Acepta:
  - **JSON**: `{"1":"b","2":"c",...}`
  - **Texto plano** (como en exámenes UNED/abogacía):
    ```
    COMUN 2019_2
    1.B          26.B
    2.C          27.B
    3.D          28.D
    ```
    También vale `1 B` (una por línea) o `1.B` sin columnas.
- `filas_esperadas` *(opcional)* — entero. Si se aporta, el validador avisa si el número de filas útiles no coincide (ej. `27` para 25 preguntas + 2 reservas).
- `n` *(solo preview, opcional, 1–50)* — número de filas a devolver. Default 5.

### Respuesta de `/api/convert`

```json
{
  "ok": true,
  "csv_url": "https://...vercel-storage.com/csv/<token>/examen.csv",
  "filas": 52,
  "columnas": 8,
  "cabecera": ["numero","pregunta","a","b","c","d","correcta","materia"],
  "plantilla_detectada": true,
  "preguntas_no_parseadas": [],
  "advertencias": []
}
```

## Variables de entorno

| Variable                 | Obligatoria | Descripción                                                                                  |
| ------------------------ | ----------- | -------------------------------------------------------------------------------------------- |
| `BLOB_READ_WRITE_TOKEN`  | **Sí**      | Token de Vercel Blob (Storage → Blob → Create Token).                                        |
| `MAX_PDF_BYTES`          | No          | Tamaño máximo del PDF en bytes. Default `10485760` (10 MB).                                  |
| `DEFAULT_HEADER`         | No          | Cabecera por defecto. Default `numero,pregunta,a,b,c,d,correcta,materia`.                    |

Copia `.env.example` a `.env` para local. En Vercel se configuran en **Project Settings → Environment Variables**.

## Ejecución local

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install uvicorn

copy .env.example .env
# Edita .env y pon tu BLOB_READ_WRITE_TOKEN

uvicorn api.index:app --reload --port 3000
```

Luego abre <http://localhost:3000/docs> para Swagger, o <http://localhost:3000> para la web mínima.

> En local, los archivos estáticos no se sirven solos: para probar la web mínima usa **Vercel CLI**:
>
> ```powershell
> npm i -g vercel
> vercel dev
> ```

## Despliegue en Vercel desde GitHub

### 1. Subir el proyecto a GitHub

```powershell
git init
git add .
git commit -m "feat: API PDF a CSV con PyMuPDF"
git branch -M main
git remote add origin https://github.com/<TU_USUARIO>/<TU_REPO>.git
git push -u origin main
```

### 2. Crear el proyecto en Vercel

1. Entra en <https://vercel.com> y conecta tu cuenta de GitHub.
2. **Add New… → Project** y selecciona el repo.
3. **Framework Preset**: *Other* (Vercel detecta `vercel.json` y el runtime Python por `runtime.txt`).
4. **Root Directory**: dejar `.` (la raíz).
5. No hace falta build command ni output directory.

### 3. Crear el Blob Storage

1. En tu proyecto de Vercel: **Storage → Create Database → Blob**.
2. Ponle un nombre (ej. `pdf-a-csv`).
3. Pestaña **Tokens**: copia el `BLOB_READ_WRITE_TOKEN`.

### 4. Variables de entorno

En **Project Settings → Environment Variables**:

- `BLOB_READ_WRITE_TOKEN` = (el token del paso 3) — **Production, Preview, Development**.
- (opcional) `MAX_PDF_BYTES`, `DEFAULT_HEADER`.

### 5. Desplegar

- Pulsa **Deploy**.
- Cuando termine, tendrás una URL del estilo `https://<tu-repo>.vercel.app`.
- A partir de ese momento, cada `git push` a `main` despliega automáticamente.

### 6. Comprobar que vive

```bash
curl https://<tu-repo>.vercel.app/api/health
```

Debe responder:

```json
{"ok": true, "servicio": "pdf-a-csv", "version": "1.1.0"}
```

## Uso remoto (PC y Android)

### Desde el navegador (PC o móvil)

Abre `https://<tu-repo>.vercel.app` desde Chrome / Edge / Firefox / Safari en cualquier dispositivo.

1. Selecciona un PDF.
2. Rellena `materia` y, si quieres, `cabecera`, `filas_esperadas` o `respuestas`.
3. **Previsualizar** para ver las 5 primeras filas (no guarda nada).
4. **Convertir y descargar** → te devuelve la URL del CSV en Vercel Blob.

> En Android puedes añadir la web a la pantalla de inicio desde Chrome: ⋮ → *Añadir a pantalla de inicio*. Queda como una app.

### Desde `curl`

```bash
curl -X POST "https://<tu-repo>.vercel.app/api/convert" \
  -F "file=@./examen.pdf" \
  -F "materia=comun" \
  -F "filas_esperadas=52" \
  -F 'respuestas={"1":"a","2":"b"}'
```

En **PowerShell**:

```powershell
curl.exe -X POST "https://<tu-repo>.vercel.app/api/convert" `
  -F "file=@.\examen.pdf" `
  -F "materia=comun"
```

### Previsualizar antes de subir

```bash
curl -X POST "https://<tu-repo>.vercel.app/api/preview" \
  -F "file=@./examen.pdf" -F "n=5"
```

Devuelve un JSON con `muestra` (primeras 5 filas) sin subir nada a Blob.

## Reglas de Cursor

En `.cursor/rules/`:

- **`proyecto.mdc`** *(alwaysApply)* — stack, estructura, qué se puede y qué no.
- **`python.mdc`** *(`**/*.py`)* — estilo Python 3.12, dependencias, errores, CSV.
- **`api.mdc`** *(`api/`, `lib/`)* — contrato de endpoints, códigos HTTP, CORS.
- **`pdf-csv-dominio.mdc`** *(extractores y builder)* — literalidad, plantilla, reservas, anuladas, parse_ok.
- **`script-base.mdc`** *(extractores y builder)* — correspondencia con `docs/base_pdf_a_csv.txt`, diferencias intencionadas y cosas que no tocar sin pedir permiso.

## Limitaciones y notas

- **v1 — 4 opciones fijas** (a, b, c, d). Roadmap: parámetro `num_opciones=3|4` para exámenes con tres respuestas (aún no implementado).
- **Formato de pregunta**: debe empezar con número (`1.-`, `2.`, `3)`, …) y opciones `a)`, `b)`, `c)`, `d)`.
- **PDFs de dos columnas**: extracción con `get_text("text", sort=True)` (Medicina legal, común, etc.).
- **Sin OCR en v1**: PDFs escaneados como imagen devolverán `422`.
- **Función Vercel**: máx **60 s** y **1024 MB** de memoria (configurado en `vercel.json`).
- **Tamaño máx PDF**: 10 MB (variable `MAX_PDF_BYTES`).
- **API pública sin auth**: la URL del CSV es no listable (token aleatorio), pero quien tenga el enlace puede descargar el CSV. Para borrar un CSV manualmente: panel **Vercel → Storage → Blob → Files**.
- **Idioma de mensajes**: español.
- **No** se almacenan los PDF originales: solo el CSV resultante.
- **No** se rellena `correcta` con conocimiento propio: solo desde la plantilla del PDF o del campo `respuestas`.
