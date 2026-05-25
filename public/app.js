(() => {
  const $ = (sel) => document.querySelector(sel);
  const formulario = $("#formulario");
  const archivo = $("#archivo");
  const materia = $("#materia");
  const cabecera = $("#cabecera");
  const respuestas = $("#respuestas");
  const filasEsperadas = $("#filas_esperadas");
  const resultado = $("#resultado");
  const btnPreview = $("#btn-preview");
  const btnConvertir = $("#btn-convertir");

  function escapar(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function pintarError(mensaje) {
    resultado.classList.remove("oculto");
    resultado.innerHTML = `<p class="estado-error"><strong>Error:</strong> ${escapar(mensaje)}</p>`;
  }

  function construirFormData() {
    if (!archivo.files || archivo.files.length === 0) {
      pintarError("Selecciona un archivo PDF.");
      return null;
    }
    const fd = new FormData();
    fd.append("file", archivo.files[0]);
    if (materia.value.trim()) fd.append("materia", materia.value.trim());
    if (cabecera.value.trim()) fd.append("cabecera", cabecera.value.trim());
    if (respuestas.value.trim()) fd.append("respuestas", respuestas.value.trim());
    if (filasEsperadas.value.trim()) fd.append("filas_esperadas", filasEsperadas.value.trim());
    return fd;
  }

  function pintarAdvertencias(advertencias) {
    if (!advertencias || advertencias.length === 0) return "";
    const items = advertencias.map((a) => `<li>${escapar(a)}</li>`).join("");
    return `<details><summary class="estado-aviso">Advertencias (${advertencias.length})</summary><ul>${items}</ul></details>`;
  }

  function pintarNoParseadas(lista) {
    if (!lista || lista.length === 0) return "";
    return `<p class="estado-aviso">Preguntas sin 4 opciones (revisar a mano): ${lista
      .map(escapar)
      .join(", ")}</p>`;
  }

  async function enviar(url, fd, etiqueta) {
    btnPreview.disabled = true;
    btnConvertir.disabled = true;
    resultado.classList.remove("oculto");
    resultado.innerHTML = `<p>${escapar(etiqueta)}…</p>`;

    try {
      const r = await fetch(url, { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) {
        pintarError(data.detail || `HTTP ${r.status}`);
        return null;
      }
      return data;
    } catch (e) {
      pintarError(e.message || String(e));
      return null;
    } finally {
      btnPreview.disabled = false;
      btnConvertir.disabled = false;
    }
  }

  btnPreview.addEventListener("click", async () => {
    const fd = construirFormData();
    if (!fd) return;
    fd.append("n", "5");
    const data = await enviar("/api/preview", fd, "Generando previsualización");
    if (!data) return;

    const filas = data.muestra || [];
    let tabla = "";
    if (filas.length > 0) {
      const cols = data.cabecera;
      tabla = `<table class="tabla-preview"><thead><tr>${cols
        .map((c) => `<th>${escapar(c)}</th>`)
        .join("")}</tr></thead><tbody>${filas
        .map(
          (f) =>
            `<tr>${cols.map((c) => `<td>${escapar(f[c] ?? "")}</td>`).join("")}</tr>`,
        )
        .join("")}</tbody></table>`;
    }

    resultado.innerHTML = `
      <p class="estado-ok"><strong>Previsualización OK</strong> · ${data.filas_totales} filas · plantilla ${
        data.plantilla_detectada ? "detectada" : "no detectada"
      }</p>
      ${pintarNoParseadas(data.preguntas_no_parseadas)}
      ${pintarAdvertencias(data.advertencias)}
      ${tabla}
    `;
  });

  formulario.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = construirFormData();
    if (!fd) return;
    const data = await enviar("/api/convert", fd, "Convirtiendo y subiendo CSV");
    if (!data) return;

    const urlSeguro = escapar(data.csv_url);
    resultado.innerHTML = `
      <p class="estado-ok"><strong>CSV listo</strong> · ${data.filas} filas · ${data.columnas} columnas · plantilla ${
        data.plantilla_detectada ? "detectada" : "no detectada"
      }</p>
      <p><a href="${urlSeguro}" download class="bloque-url">${urlSeguro}</a></p>
      <p><button type="button" id="btn-copiar">Copiar URL</button></p>
      ${pintarNoParseadas(data.preguntas_no_parseadas)}
      ${pintarAdvertencias(data.advertencias)}
    `;
    const btn = document.getElementById("btn-copiar");
    if (btn) {
      btn.addEventListener("click", () => navigator.clipboard.writeText(data.csv_url));
    }
  });
})();
