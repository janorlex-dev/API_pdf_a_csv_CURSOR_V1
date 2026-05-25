# Api para conversión de pdf a csv
_Exported on 5/15/2026 at 20:42:38 GMT+2 from Cursor (2.6.21)_

---

**User**

vamos a crear una api para pasar de archivo pdf a csv y como orientacion te he paasafo el file .md 
vamos a hacer el index y el .rules de cursos , las intruciones para poder ejecutarlo en remoto una vez subido a github y desplegado en vercel desde cualqueir pc o movil android , hazme las preguntas necesarias para definir la aplicacion 

---

**Cursor**

Leyendo tu archivo de orientación y revisando el proyecto para formular preguntas concretas.



He leído `pdf a csv de chatgpt thinking.md`. Mezcla un skill de hojas de cálculo de otro entorno y, al final, un ejemplo concreto: CSV con columnas `pregunta`, `a`, `b`, `c`, `d`, `correcta`, `materia` y dudas sobre cuántas filas incluir según el PDF. Eso orienta el **dominio** (tests tipo oposición), pero no define sola la API técnica.

Para poder definir bien la aplicación (y luego el `index`, las reglas de Cursor y el despliegue en Vercel), necesito que aclares lo siguiente.

---

### 1. Origen y forma de los PDF
- ¿Los PDF serán **siempre el mismo tipo** (mismo examen/plantilla) o **cualquier PDF** con tablas o texto libre?
- ¿Son PDF **con texto seleccionable** o a veces **escaneados** (hace falta OCR)?
- ¿Tamaño máximo razonable por archivo (por ejemplo 5 MB, 20 MB)?

### 2. Qué debe salir en el CSV
- ¿El esquema fijo es el del ejemplo (`pregunta`, `a`, `b`, `c`, `d`, `correcta`, `materia`) o **otras columnas**?
- Si el PDF no encaja en ese esquema, ¿prefieres **error claro**, CSV “lo mejor posible”, o **dos modos** (estructurado vs. volcado plano de texto/tablas)?

### 3. Comportamiento de la API
- ¿Solo **subir PDF y devolver CSV** (descarga o JSON con URL), o también **listar jobs**, **historial**, etc.?
- ¿Debe ser **pública** (cualquiera con la URL) o **protegida** (API key en header, login, etc.)?
- ¿Límite de **peticiones por minuto/día** o uso solo personal?

### 4. Stack y Vercel
- ¿Te vale **Node/TypeScript** en Vercel (Serverless/Edge) o prefieres **Python** (por ejemplo solo en otra plataforma, o Vercel con runtime Python si lo usas)?
- En Vercel hay límites de **tamaño del body** y **tiempo de ejecución**; ¿te sirve procesar PDFs “pequeños/medianos” en una sola request o necesitas **archivos grandes** (quizá otro servicio de almacenamiento + cola)?

### 5. Cliente (PC y Android)
- ¿Consumo solo por **HTTP** (Postman, `curl`, script) o quieres una **página web mínima** (formulario: elegir PDF → descargar CSV) usable desde el móvil?
- ¿Idioma de mensajes de error y documentación solo **español**?

### 6. Privacidad y datos
- ¿Los PDF pueden contener **datos sensibles**? (afecta si guardamos archivos en disco, logs, caché en Vercel, etc.)
- ¿Necesitas **no almacenar** el PDF tras generar el CSV (solo memoria temporal)?

### 7. Cursor: `.rules` / reglas del proyecto
- ¿Quieres una regla orientada solo a **este repo** (PDF→CSV, Vercel, sin commits automáticos) o también **estilo de código** (TypeScript estricto, tests obligatorios, etc.)?

---

Responde con lo que tengas claro y “no sé” en lo que quieras que proponga yo un valor por defecto razonable. Con esas respuestas podemos cerrar el diseño de la API y redactar el `index` (README/inicio), las reglas de Cursor y las instrucciones de despliegue y uso remoto sin ambigüedades.

