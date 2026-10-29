/* CORT · HUD: orbe de partículas, estados, reloj, chat y modelos. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const TAU = Math.PI * 2;
  const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let CAPTURA = false;
  try { CAPTURA = new URLSearchParams(location.search).has("captura"); } catch (e) { /* sin URL */ }

  const ESTADOS = {
    idle: ["en reposo", "núcleo local"],
    listening: ["escuchando", "micrófono"],
    thinking: ["procesando", "cerebro"],
    executing: ["ejecutando", "herramienta"],
    speaking: ["hablando", "voz"],
    downloading: ["descargando", "modelos"],
    error: ["alerta", "fallo"],
    alert: ["alarma", "recordatorio"],
    offline: ["sin conexión", "núcleo"],
  };

  const COLORES = {
    idle: [111, 243, 255],
    listening: [166, 255, 104],
    thinking: [255, 196, 107],
    executing: [193, 139, 255],
    speaking: [185, 251, 255],
    downloading: [125, 183, 255],
    error: [255, 94, 108],
    alert: [255, 160, 74],
    offline: [126, 154, 166],
  };

  const NOMBRES_ESTILO = {
    esfera: "esfera de líneas",
    anillo: "anillo vortex",
    cinta: "cinta de plasma",
    enjambre: "enjambre",
  };

  const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

  const ui = {
    enviando: false,
    ultimoSig: "",
    fechaServidor: "",
    silencio: false,
    iniciado: false,
    estilo: "esfera",
    eventoId: 0,
    ultimoEstado: "",
    descargando: false,
    descargaLocal: false,
    descargaPct: null,
    cargandoLista: false,
    pollModelos: 0,
    modelosLeidos: null,
    enfocado: false,
    modelosAbiertos: false,
    capacidadesAbiertas: false,
    capCargadas: false,
    capHerramientas: [],
    paletaAbierta: false,
    paletaIndice: 0,
    paletaItems: [],
    ejecTimer: 0,
  };

  /* ---------------- reloj ---------------- */
  const SEGMENTOS = {
    0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg",
    5: "acdfg", 6: "acdefg", 7: "abc", 8: "abcdefg", 9: "abcdfg",
  };

  function construirReloj() {
    const caja = $("hora");
    if (!caja) return;
    caja.innerHTML = "";
    for (let i = 0; i < 6; i++) {
      if (i === 2 || i === 4) {
        const sep = document.createElement("span");
        sep.className = "clock-colon";
        sep.setAttribute("aria-hidden", "true");
        sep.append(document.createElement("i"), document.createElement("i"));
        caja.appendChild(sep);
      }
      const digito = document.createElement("span");
      digito.className = "clock-digit";
      digito.dataset.valor = "";
      for (const letra of "abcdefg") {
        const seg = document.createElement("i");
        seg.className = `seg-${letra}`;
        seg.dataset.seg = letra;
        digito.appendChild(seg);
      }
      caja.appendChild(digito);
    }
  }

  function fechaLarga(d) {
    return `${DIAS[d.getDay()]} ${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`;
  }

  function tickReloj() {
    const ahora = new Date();
    const hh = String(ahora.getHours()).padStart(2, "0");
    const mm = String(ahora.getMinutes()).padStart(2, "0");
    const ss = String(ahora.getSeconds()).padStart(2, "0");
    const texto = `${hh}${mm}${ss}`;
    const caja = $("hora");
    const digitos = caja.querySelectorAll(".clock-digit");
    for (let i = 0; i < digitos.length; i++) {
      const digito = digitos[i];
      const valor = texto[i];
      if (digito.dataset.valor === valor) continue;
      digito.dataset.valor = valor;
      const activos = SEGMENTOS[valor] || "";
      for (const seg of digito.children) {
        // dataset.seg evita leer la clase ya mutada («seg-a on»): si se parsea
        // className, cada cambio de dígito apagaría los segmentos encendidos.
        seg.classList.toggle("on", activos.includes(seg.dataset.seg));
      }
    }
    caja.setAttribute("aria-label", `hora local ${hh}:${mm}:${ss}`);
    if (!ui.fechaServidor) $("fecha").textContent = fechaLarga(ahora);
  }
  construirReloj();
  setInterval(tickReloj, 500);
  tickReloj();

  /* ---------------- utilidades ---------------- */
  function toast(texto, ms = 2600) {
    const el = $("toast");
    el.textContent = texto;
    el.classList.add("visible");
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove("visible"), ms);
  }

  function horaCorta(ts) {
    if (!ts) return "--:--";
    const d = new Date(ts * 1000);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }

  function agregarBurbuja(rol, texto, herramienta = "", ms = 0, error = false) {
    const cont = $("messages");
    const div = document.createElement("div");
    div.className = `msg ${rol}${error ? " error" : ""}`;
    const p = document.createElement("span");
    p.textContent = texto;
    div.appendChild(p);
    if (herramienta || ms) {
      const meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = [herramienta, ms ? `${ms} ms` : ""].filter(Boolean).join(" · ");
      div.appendChild(meta);
    }
    cont.appendChild(div);
    cont.scrollTop = cont.scrollHeight;
  }

  function renderMensajes(lista) {
    const ultimo = lista[lista.length - 1] || {};
    const sig = `${lista.length}|${ultimo.ts || 0}|${(ultimo.texto || "").length}|${ultimo.rol || ""}`;
    if (sig === ui.ultimoSig) return;
    ui.ultimoSig = sig;
    const cajaParcial = $("parcial");
    if (cajaParcial) {
      cajaParcial.hidden = true;
      cajaParcial.textContent = "";
    }
    const cont = $("messages");
    cont.innerHTML = "";
    if (!lista.length) {
      agregarBurbuja("cort", "CORT en línea. Escribí «ayuda» o tocá un comando rápido.");
      return;
    }
    const cercaDelFondo = cont.scrollHeight - cont.scrollTop - cont.clientHeight < 90;
    for (const m of lista) {
      const rol = m.rol === "user" ? "user" : "cort";
      agregarBurbuja(rol, m.texto, m.herramienta, m.ms);
    }
    if (cercaDelFondo) cont.scrollTop = cont.scrollHeight;
  }

  function renderTraza(eventos) {
    const cont = $("traza");
    const lista = (eventos || []).slice(-6).reverse();
    if (!lista.length) {
      cont.innerHTML = '<div class="traza-vacia">sin acciones todavía</div>';
      return;
    }
    cont.innerHTML = "";
    for (const e of lista) {
      const detalle = e.detalle || {};
      const fila = document.createElement("div");
      fila.className = `traza-fila${e.tipo === "error" || detalle.ok === false ? " error" : ""}`;
      const hora = document.createElement("span");
      hora.className = "traza-hora";
      hora.textContent = horaCorta(e.ts);
      const texto = document.createElement("span");
      texto.className = "traza-texto";
      const icono = e.tipo === "error" ? "✕ " : e.tipo === "alarma" ? "▲ " : e.tipo === "descarga" ? "↓ " : e.tipo === "detenido" ? "■ " : "◇ ";
      texto.textContent = icono + (detalle.herramienta || e.etiqueta || e.tipo || "acción");
      if (detalle.ms != null) {
        const ms = document.createElement("span");
        ms.className = "traza-ms";
        ms.textContent = `${detalle.ms} ms`;
        texto.appendChild(ms);
      }
      fila.appendChild(hora);
      fila.appendChild(texto);
      const extra = detalle.args || detalle.paso;
      if (extra) {
        const linea = document.createElement("span");
        linea.className = "traza-detalle";
        linea.textContent = detalle.args ? detalle.args : `paso ${detalle.paso}`;
        fila.appendChild(linea);
      }
      cont.appendChild(fila);
    }
  }

  /* ---------------- estado ---------------- */
  function mostrarEjecucion(texto, ms = "", activa = false, autoOcultar = 0) {
    const caja = $("ejecucion");
    caja.classList.add("visible");
    caja.classList.toggle("activa", !!activa);
    $("ejecucion-tool").textContent = texto || "preparando";
    $("ejecucion-ms").textContent = ms ? `${ms} ms` : "";
    $("ejecucion-icon").textContent = activa ? "◌" : "◇";
    $("ejecucion-barra").style.width = activa ? "" : "100%";
    clearTimeout(ui.ejecTimer);
    if (autoOcultar > 0) {
      ui.ejecTimer = setTimeout(() => caja.classList.remove("visible"), autoOcultar);
    }
  }

  function dispararEvento(evento) {
    if (!evento || !evento.id) return;
    ui.eventoId = Math.max(ui.eventoId, evento.id);
    const etiqueta = evento.etiqueta || evento.tipo || "acción";
    mostrarEjecucion(etiqueta, "", false, 2400);
    burst = {
      t0: performance.now(),
      tipo: evento.tipo || "ejecucion",
    };
    for (const p of puntos) p.imp = 1;
  }

  function aplicarEstado(d) {
    const estado = d.estado || "idle";
    document.body.dataset.state = estado;
    const par = ESTADOS[estado] || [estado, "núcleo"];
    $("state-text").textContent = par[0];
    $("state-era").textContent = d.descargando ? "descarga" : par[1];

    if (d.version) $("version").textContent = d.version;
    if (d.fecha) {
      ui.fechaServidor = d.fecha;
      $("fecha").textContent = d.fecha;
    }

    const m = d.metricas || {};
    const cpu = Number(m.cpu || 0);
    const ram = Number(m.ram || 0);
    $("w-cpu").textContent = `${cpu.toFixed(0)}%`;
    $("w-ram").textContent = `${ram.toFixed(0)}%`;
    $("bar-cpu").style.width = `${Math.min(100, cpu)}%`;
    $("bar-ram").style.width = `${Math.min(100, ram)}%`;
    $("m-cpu").textContent = `${cpu.toFixed(0)} %`;
    $("m-ram").textContent = `${ram.toFixed(0)} %`;

    const partes = [];
    if (m.ram_usada_gb != null) partes.push(`RAM ${m.ram_usada_gb}/${m.ram_total_gb} GB`);
    if (m.bateria != null) partes.push(`batería ${m.bateria.porcentaje} %`);
    $("m-detalle").textContent = partes.join(" · ") || "sin datos";

    const voz = d.voz || {};
    const flags = d.flags || {};
    $("w-mic").textContent = voz.stt ? "ON" : "OFF";
    $("w-ia").textContent = flags.ollama_ok ? (d.modelo || "ON") : "OFF";
    $("ia-led").classList.toggle("ok", !!flags.ollama_ok);
    $("chat-model").textContent = d.modelo ? `modelo · ${d.modelo}` : "sin modelo local";

    ui.silencio = !!voz.silencio;
    const mute = $("mute");
    mute.classList.toggle("activo", ui.silencio);
    mute.textContent = ui.silencio ? "✕" : "♪";
    const railVoz = $("rail-silencio");
    if (railVoz) {
      railVoz.classList.toggle("activo", ui.silencio);
      const icono = railVoz.querySelector("b");
      if (icono) icono.textContent = ui.silencio ? "✕" : "♪";
    }

    const alarma = (d.alarmas || [])[0];
    if (alarma && alarma.cuando) {
      $("alarma").textContent = `alarma ${alarma.cuando.slice(11, 16)} · ${alarma.texto}`;
    } else {
      $("alarma").textContent = "sin alarmas";
    }

    const log = $("log");
    const lineas = (d.log || []).join("\n");
    if (log.textContent !== lineas) {
      log.textContent = lineas;
      log.scrollTop = log.scrollHeight;
    }

    renderMensajes(d.mensajes || []);
    renderTraza(d.eventos || []);

    const stop = $("stop");
    const activo = ["speaking", "listening", "thinking", "executing", "alert"].includes(estado);
    stop.hidden = !activo;
    const railStop = $("rail-stop");
    if (railStop) railStop.hidden = !activo;

    ui.descargando = !!d.descargando || ui.descargaLocal;

    if (!ui.descargaLocal && d.descarga && d.descarga.modelo) {
      $("descarga").hidden = false;
      if (d.descarga.porcentaje != null || d.descarga.total) {
        pintarProgreso(d.descarga, d.descarga.modelo);
      } else {
        $("descarga-texto").textContent = `${d.descarga.modelo} · ${d.descarga.estado || "descargando"}`;
      }
    }

    const parcial = (d.parcial || "").trim();
    const cajaParcial = $("parcial");
    if (parcial && ["thinking", "speaking", "executing"].includes(estado)) {
      cajaParcial.hidden = false;
      cajaParcial.textContent = parcial;
    } else if (cajaParcial.textContent !== parcial) {
      cajaParcial.hidden = true;
      cajaParcial.textContent = "";
    }

    if (d.evento && d.evento.id > ui.eventoId) {
      if (ui.iniciado) dispararEvento(d.evento);
      else ui.eventoId = d.evento.id;
    }

    if (estado !== ui.ultimoEstado) {
      ui.ultimoEstado = estado;
      if (estado === "executing" || estado === "thinking") {
        mostrarEjecucion(estado === "thinking" ? "pensando" : "preparando", "", true);
      } else if (estado === "downloading") {
        mostrarEjecucion("descargando modelo", "", true);
      } else if (estado === "idle" || estado === "offline") {
        clearTimeout(ui.ejecTimer);
        ui.ejecTimer = setTimeout(() => $("ejecucion").classList.remove("visible"), 900);
      }
    }

    ui.iniciado = true;
  }

  async function pedirEstado() {
    try {
      const r = await fetch("/api/estado", { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      aplicarEstado(await r.json());
    } catch (e) {
      document.body.dataset.state = "offline";
      $("state-text").textContent = ESTADOS.offline[0];
      $("state-era").textContent = ESTADOS.offline[1];
    }
  }
  pedirEstado();
  if (!CAPTURA) setInterval(pedirEstado, 900);

  /* ---------------- chat ---------------- */
  const form = $("form");
  const input = $("texto");

  async function enviarTexto(texto) {
    texto = (texto || "").trim();
    if (!texto || ui.enviando) return;
    ui.enviando = true;
    input.value = "";
    agregarBurbuja("user", texto);
    document.body.dataset.state = "thinking";
    $("state-text").textContent = ESTADOS.thinking[0];
    $("state-era").textContent = ESTADOS.thinking[1];
    mostrarEjecucion("pensando", "", true);

    const ctrl = new AbortController();
    const temporizador = setTimeout(() => ctrl.abort(), 300000);
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto }),
        signal: ctrl.signal,
      });
      const d = await r.json();
      if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);
      if (d.evento && d.evento.id) dispararEvento(d.evento);
      if (d.herramienta === "error" || (d.herramienta || "").includes("(error)")) {
        document.body.dataset.state = "error";
      }
    } catch (e) {
      const mensaje = e.name === "AbortError"
        ? "CORT tardó demasiado en responder. El modelo puede estar cargándose; probá otra vez."
        : `No pude contactar al núcleo de CORT. ${e.message || ""}`;
      agregarBurbuja("cort", mensaje, "error", 0, true);
      document.body.dataset.state = "error";
      $("state-text").textContent = ESTADOS.error[0];
      mostrarEjecucion("sin respuesta", "", false, 2600);
    } finally {
      clearTimeout(temporizador);
      ui.enviando = false;
      ui.ultimoSig = "";
      pedirEstado();
    }
  }

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    enviarTexto(input.value);
  });

  $("quick").addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.modelos) {
      abrirModelos();
      return;
    }
    if (b.dataset.texto) enviarTexto(b.dataset.texto);
  });

  async function detenerTurno() {
    try {
      await fetch("/api/accion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "detener" }),
      });
      document.body.dataset.state = "idle";
      $("state-text").textContent = ESTADOS.idle[0];
      $("parcial").hidden = true;
      toast("Turno detenido", 1600);
    } catch (e) {
      toast("No pude detener el turno.", 2200);
    }
    pedirEstado();
  }

  async function hablarAhora() {
    if (ui.enviando) return;
    ui.enviando = true;
    document.body.dataset.state = "listening";
    $("state-text").textContent = ESTADOS.listening[0];
    toast("Escuchando… hablá ahora", 5000);
    try {
      const r = await fetch("/api/accion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "escuchar" }),
      });
      const d = await r.json();
      toast(d.mensaje || (d.ok ? "Listo" : "No pude escuchar"), 4000);
    } catch (e) {
      toast("No pude usar el micrófono.", 4000);
    } finally {
      ui.enviando = false;
      ui.ultimoSig = "";
      pedirEstado();
    }
  }

  async function alternarSilencio() {
    ui.silencio = !ui.silencio;
    try {
      await fetch("/api/accion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "silencio", activar: ui.silencio }),
      });
    } catch (e) { /* el próximo sondeo corrige el estado */ }
    $("mute").classList.toggle("activo", ui.silencio);
    $("mute").textContent = ui.silencio ? "✕" : "♪";
    const railVoz = $("rail-silencio");
    if (railVoz) {
      railVoz.classList.toggle("activo", ui.silencio);
      const icono = railVoz.querySelector("b");
      if (icono) icono.textContent = ui.silencio ? "✕" : "♪";
    }
    toast(ui.silencio ? "Voz silenciada" : "Voz activada", 1600);
  }

  $("stop").addEventListener("click", detenerTurno);
  $("mic").addEventListener("click", hablarAhora);
  $("mute").addEventListener("click", alternarSilencio);

  /* ---------------- enfoque ---------------- */
  function setEnfoque(valor, avisar = true) {
    ui.enfocado = !!valor;
    document.body.classList.toggle("enfoque", ui.enfocado);
    $("enfoque").textContent = ui.enfocado ? "◰" : "◱";
    $("enfoque").setAttribute("aria-pressed", ui.enfocado ? "true" : "false");
    const railEnfoque = $("rail-enfoque");
    if (railEnfoque) {
      railEnfoque.classList.toggle("activo", ui.enfocado);
      railEnfoque.setAttribute("aria-pressed", ui.enfocado ? "true" : "false");
      const icono = railEnfoque.querySelector("b");
      if (icono) icono.textContent = ui.enfocado ? "◰" : "◱";
    }
    localStorage.setItem("cort.enfoque", ui.enfocado ? "1" : "0");
    if (avisar) toast(ui.enfocado ? "Modo enfoque" : "Paneles visibles", 1400);
  }
  $("enfoque").addEventListener("click", () => setEnfoque(!ui.enfocado));
  try {
    if (localStorage.getItem("cort.enfoque") === "1") setEnfoque(true, false);
  } catch (e) { /* sin almacenamiento */ }

  /* ---------------- estilos del orbe ---------------- */
  function setEstilo(nuevo, avisar = true) {
    if (!NOMBRES_ESTILO[nuevo] || nuevo === ui.estilo && puntos.length) return;
    ui.estilo = nuevo;
    document.body.dataset.orb = nuevo;
    cambiarEstiloOrbe(nuevo);
    try { localStorage.setItem("cort.orbe", nuevo); } catch (e) { /* sin almacenamiento */ }
    document.querySelectorAll("#orb-styles button").forEach((b) => {
      b.classList.toggle("activo", b.dataset.estilo === nuevo);
    });
    burst = { t0: performance.now(), tipo: "estilo" };
    for (const p of puntos) p.imp = 0.7;
    if (avisar) toast(`Orbe · ${NOMBRES_ESTILO[nuevo]}`, 1600);
  }

  $("orb-styles").addEventListener("click", (ev) => {
    const b = ev.target.closest("button[data-estilo]");
    if (b) setEstilo(b.dataset.estilo);
  });

  try {
    const guardado = localStorage.getItem("cort.orbe");
    if (NOMBRES_ESTILO[guardado]) {
      ui.estilo = guardado;
      document.body.dataset.orb = guardado;
      document.querySelectorAll("#orb-styles button").forEach((b) => {
        b.classList.toggle("activo", b.dataset.estilo === guardado);
      });
    }
  } catch (e) { /* sin almacenamiento */ }

  /* ---------------- modelos ---------------- */
  function abrirModelos() {
    if (ui.capacidadesAbiertas) cerrarCapacidades();
    if (ui.paletaAbierta) cerrarPaleta();
    ui.modelosAbiertos = true;
    const panel = $("modelos");
    panel.hidden = false;
    panel.removeAttribute("aria-hidden");
    cargarModelos();
    clearInterval(ui.pollModelos);
    ui.pollModelos = setInterval(() => {
      if (!ui.modelosAbiertos) return;
      const d = ui.modelosLeidos;
      if (!ui.descargaLocal && (d && d.descargando)) cargarModelos();
    }, 3000);
  }

  function cerrarModelos() {
    ui.modelosAbiertos = false;
    const panel = $("modelos");
    const activo = document.activeElement;
    if (activo && panel.contains(activo)) activo.blur();
    panel.hidden = true;
    clearInterval(ui.pollModelos);
    ui.pollModelos = 0;
  }

  $("abrir-modelos").addEventListener("click", abrirModelos);
  $("cerrar-modelos").addEventListener("click", cerrarModelos);

  function tamano(gb) {
    if (!gb) return "—";
    return gb >= 1 ? `${gb.toFixed(1)} GB` : `${Math.max(1, Math.round(gb * 1024))} MB`;
  }

  async function cargarModelos() {
    const cont = $("modelos-lista");
    const estado = $("modelos-estado");
    if (ui.cargandoLista) return;
    ui.cargandoLista = true;
    estado.classList.remove("error");
    estado.textContent = "consultando Ollama…";
    cont.innerHTML = '<div class="modelos-vacio">buscando modelos instalados…</div>';
    try {
      const r = await fetch("/api/modelos", { cache: "no-store" });
      const d = await r.json();
      ui.modelosLeidos = d;
      if (!d.ok) {
        estado.classList.add("error");
        estado.textContent = `Ollama no responde en ${d.url || "127.0.0.1:11434"}: ${d.motivo || "sin detalle"}. Encendé Ollama y volvé a intentar.`;
        cont.innerHTML = '<div class="modelos-vacio">No puedo listar modelos sin el servidor de Ollama.</div>';
        renderRecomendados(d.recomendados, d.activo);
        return;
      }
      estado.textContent = d.modelos.length
        ? `${d.modelos.length} modelo(s) instalado(s) · activo: ${d.activo || "ninguno"}`
        : "Ollama responde, pero no hay modelos instalados.";
      if (!d.modelos.length) {
        cont.innerHTML = '<div class="modelos-vacio">Descargá uno pequeño para empezar: qwen2.5:0.5b o qwen3:0.6b.</div>';
      } else {
        cont.innerHTML = "";
        for (const m of d.modelos) {
          const fila = document.createElement("button");
          fila.type = "button";
          fila.className = `modelo-fila${m.nombre === d.activo ? " activo" : ""}`;
          fila.dataset.nombre = m.nombre;
          const nombre = document.createElement("span");
          nombre.className = "nombre";
          nombre.textContent = m.nombre;
          const tam = document.createElement("span");
          tam.className = "tamano";
          tam.textContent = tamano(m.tamano_gb);
          const detalle = document.createElement("span");
          detalle.className = "detalle";
          detalle.textContent = [m.familia, m.parametros, m.cuantizacion].filter(Boolean).join(" · ") || "modelo local";
          fila.appendChild(nombre);
          fila.appendChild(tam);
          if (m.nombre === d.activo) {
            const marca = document.createElement("span");
            marca.className = "marca";
            marca.textContent = "ACTIVO";
            fila.appendChild(marca);
          }
          fila.appendChild(detalle);
          fila.addEventListener("click", () => elegirModelo(m.nombre));
          cont.appendChild(fila);
        }
      }
      renderRecomendados(d.recomendados, d.activo);
      if (d.descargando && d.progreso) {
        $("descarga").hidden = false;
        pintarProgreso(d.progreso, d.descargando);
      }
    } catch (e) {
      estado.classList.add("error");
      estado.textContent = `No pude consultar el panel de modelos: ${e.message || e}`;
      cont.innerHTML = '<div class="modelos-vacio">Revisá que el núcleo de CORT siga vivo.</div>';
    } finally {
      ui.cargandoLista = false;
    }
  }

  function renderRecomendados(lista, activo) {
    const cont = $("recomendados");
    if (!cont) return;
    cont.innerHTML = "";
    if (!Array.isArray(lista) || !lista.length) {
      cont.innerHTML = '<span class="sugerencias-vacio">sin recomendados</span>';
      return;
    }
    for (const rec of lista) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `rec${rec.instalado ? " instalado" : ""}`;
      b.dataset.modelo = rec.nombre;
      b.dataset.instalado = rec.instalado ? "1" : "";
      const nombre = document.createElement("b");
      nombre.textContent = rec.nombre;
      const meta = document.createElement("span");
      meta.textContent = `≈ ${rec.gb} GB · ${rec.nota}`;
      const accion = document.createElement("em");
      accion.textContent = rec.instalado ? (rec.nombre === activo ? "activo" : "usar") : "instalar";
      b.appendChild(nombre);
      b.appendChild(meta);
      b.appendChild(accion);
      b.addEventListener("click", () => {
        if (rec.instalado) elegirModelo(rec.nombre);
        else descargarModelo(rec.nombre);
      });
      cont.appendChild(b);
    }
  }

  function bytes(n) {
    if (!n) return "0 MB";
    return n >= 1073741824 ? `${(n / 1073741824).toFixed(2)} GB` : `${(n / 1048576).toFixed(1)} MB`;
  }

  let descargaVel = { t: 0, bytes: 0, bps: 0 };
  let ultimoProgreso = null;

  function pintarProgreso(dato, nombre) {
    if (!dato || typeof dato !== "object") return;
    ultimoProgreso = dato;
    const pct = dato.porcentaje == null ? null : Math.max(0, Math.min(100, Number(dato.porcentaje)));
    if (pct != null) {
      ui.descargaPct = pct;
      $("bar-descarga").style.width = `${pct}%`;
    }
    const ahora = performance.now();
    if (dato.total > 0) {
      if (!descargaVel.t) {
        descargaVel = { t: ahora, bytes: dato.completado || 0, bps: 0 };
      } else if (ahora - descargaVel.t > 1200) {
        const dt = (ahora - descargaVel.t) / 1000;
        const db = (dato.completado || 0) - descargaVel.bytes;
        if (db >= 0 && dt > 0) descargaVel.bps = db / dt;
        descargaVel.t = ahora;
        descargaVel.bytes = dato.completado || 0;
      }
    }
    const partes = [];
    if (dato.total > 0) partes.push(`${bytes(dato.completado || 0)} / ${bytes(dato.total)}`);
    if (descargaVel.bps > 0) partes.push(`${bytes(descargaVel.bps)}/s`);
    if (descargaVel.bps > 0 && dato.total > dato.completado) {
      const falta = Math.round((dato.total - dato.completado) / descargaVel.bps);
      partes.push(`faltan ${falta > 90 ? Math.round(falta / 60) + " min" : falta + " s"}`);
    }
    if (dato.capas) partes.push(`${dato.capas} capa(s)`);
    $("descarga-stats").textContent = partes.join(" · ");
    const etiqueta = pct == null ? (dato.estado || "descargando") : `${dato.estado || "descargando"} · ${pct.toFixed(1)} %`;
    $("descarga-texto").textContent = `${nombre || ""} ${etiqueta}`.trim();
  }

  async function elegirModelo(nombre) {
    try {
      const r = await fetch("/api/modelos/seleccionar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre }),
      });
      const d = await r.json();
      if (!d.ok) {
        toast(d.error || "No pude cambiar el modelo.", 3600);
        return;
      }
      toast(`Modelo activo: ${d.modelo}`, 2200);
      pedirEstado();
      cargarModelos();
    } catch (e) {
      toast("No pude cambiar el modelo.", 3000);
    }
  }

  function procesarProgreso(dato, nombre, fallo) {
    if (!dato || typeof dato !== "object") return;
    if (dato.error) {
      fallo.texto = dato.error;
      return;
    }
    if (dato.inicio) {
      $("descarga-texto").textContent = `iniciando ${dato.modelo || nombre}…`;
      return;
    }
    pintarProgreso(dato, nombre);
    if (dato.ok) {
      $("descarga-texto").textContent = `${dato.modelo || nombre} lista · activa en CORT`;
      $("bar-descarga").style.width = "100%";
      $("descarga-stats").textContent = "";
    }
  }

  async function cancelarDescarga() {
    const boton = $("cancelar-descarga");
    boton.disabled = true;
    try {
      const r = await fetch("/api/modelos/cancelar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const d = await r.json();
      if (!d.ok) toast(d.error || "No hay ninguna descarga en curso.", 3000);
      else $("descarga-texto").textContent = "cancelando…";
    } catch (e) {
      toast("No pude cancelar la descarga.", 2800);
    } finally {
      setTimeout(() => { boton.disabled = false; }, 1500);
    }
  }

  async function descargarModelo(nombre) {
    nombre = (nombre || "").trim();
    if (!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$/.test(nombre)) {
      toast("Nombre de modelo inválido. Ejemplo: qwen3:0.6b", 3600);
      return;
    }
    if (ui.descargando) {
      toast("Ya hay una descarga en curso.", 2400);
      return;
    }
    ui.descargando = true;
    ui.descargaLocal = true;
    ui.descargaPct = null;
    descargaVel = { t: 0, bytes: 0, bps: 0 };
    ultimoProgreso = null;
    $("descarga").hidden = false;
    $("bar-descarga").style.width = "0%";
    $("descarga-texto").textContent = `iniciando ${nombre}…`;
    $("descarga-stats").textContent = "";
    $("descargar-btn").disabled = true;
    document.body.dataset.state = "downloading";
    $("state-text").textContent = ESTADOS.downloading[0];
    mostrarEjecucion(`descargando ${nombre}`, "", true);
    const fallo = { texto: "" };
    try {
      const r = await fetch("/api/modelos/descargar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      if (r.body && r.body.getReader) {
        const lector = r.body.getReader();
        const dec = new TextDecoder();
        let resto = "";
        while (true) {
          const { done, value } = await lector.read();
          if (done) break;
          resto += dec.decode(value, { stream: true });
          const lineas = resto.split("\n");
          resto = lineas.pop() || "";
          for (const linea of lineas) {
            if (!linea.trim()) continue;
            try {
              procesarProgreso(JSON.parse(linea), nombre, fallo);
            } catch (e) { /* línea parcial o ruido */ }
            if (fallo.texto) break;
          }
          if (fallo.texto) break;
        }
        if (resto.trim() && !fallo.texto) {
          try { procesarProgreso(JSON.parse(resto), nombre, fallo); } catch (e) { /* ruido */ }
        }
      } else {
        const texto = await r.text();
        for (const linea of texto.split("\n")) {
          if (!linea.trim()) continue;
          try { procesarProgreso(JSON.parse(linea), nombre, fallo); } catch (e) { /* ruido */ }
        }
      }
      if (fallo.texto) throw new Error(fallo.texto);
      $("descarga-texto").textContent = `${nombre} lista · activa en CORT`;
      $("bar-descarga").style.width = "100%";
      toast(`Descarga terminada. CORT usa ${nombre}.`, 4200);
      document.body.dataset.state = "idle";
      mostrarEjecucion(`${nombre} lista`, "", false, 2600);
    } catch (e) {
      $("descarga-texto").textContent = `error: ${e.message || e}`;
      toast(`No pude descargar ${nombre}.`, 3600);
      document.body.dataset.state = "error";
      $("state-text").textContent = ESTADOS.error[0];
      mostrarEjecucion("descarga fallida", "", false, 3000);
    } finally {
      ui.descargando = false;
      ui.descargaLocal = false;
      $("descargar-btn").disabled = false;
      pedirEstado();
      cargarModelos();
    }
  }

  $("cancelar-descarga").addEventListener("click", cancelarDescarga);

  $("form-modelo").addEventListener("submit", (ev) => {
    ev.preventDefault();
    descargarModelo($("modelo-nombre").value);
  });

  /* ---------------- capacidades reales ---------------- */
  const normalizar = (texto) => String(texto || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  function crearTarjetaCapacidad(tool) {
    const caja = document.createElement("div");
    caja.className = "cap-tool";
    const fila = document.createElement("div");
    fila.className = "cap-tool-top";
    const nombre = document.createElement("span");
    nombre.className = "cap-nombre";
    nombre.textContent = tool.nombre;
    const riesgo = document.createElement("span");
    riesgo.className = "cap-riesgo";
    riesgo.textContent = tool.riesgo || "bajo";
    fila.append(nombre, riesgo);
    const desc = document.createElement("div");
    desc.className = "cap-desc";
    desc.textContent = tool.descripcion || "";
    const ejemplo = document.createElement("button");
    ejemplo.type = "button";
    ejemplo.className = "cap-ejemplo";
    ejemplo.textContent = `${tool.ejemplo || "probar"} →`;
    ejemplo.addEventListener("click", () => cargarEjemplo(tool.ejemplo));
    caja.append(fila, desc, ejemplo);
    return caja;
  }

  function renderCapacidades(filtro = "") {
    const lista = $("cap-lista");
    if (!lista) return;
    const q = normalizar(filtro);
    const items = ui.capHerramientas.filter((t) => {
      if (!q) return true;
      // La categoría no entra en el filtro: buscar «clima» no debe traer
      // «fecha» y «hora» sólo porque comparten «Tiempo y clima».
      return normalizar(`${t.nombre} ${t.descripcion} ${t.ejemplo}`).includes(q);
    });
    lista.innerHTML = "";
    if (!items.length) {
      const vacio = document.createElement("div");
      vacio.className = "cap-vacio";
      vacio.textContent = q ? "No encontré herramientas con ese filtro." : "Todavía no cargué el registro.";
      lista.appendChild(vacio);
      return;
    }
    if (q) {
      for (const tool of items) lista.appendChild(crearTarjetaCapacidad(tool));
      return;
    }
    const grupos = new Map();
    for (const tool of items) {
      if (!grupos.has(tool.categoriaNombre)) grupos.set(tool.categoriaNombre, []);
      grupos.get(tool.categoriaNombre).push(tool);
    }
    for (const [nombreGrupo, tools] of grupos) {
      const grupo = document.createElement("div");
      grupo.className = "cap-grupo";
      const titulo = document.createElement("div");
      titulo.className = "cap-grupo-titulo";
      titulo.textContent = nombreGrupo;
      grupo.appendChild(titulo);
      for (const tool of tools) grupo.appendChild(crearTarjetaCapacidad(tool));
      lista.appendChild(grupo);
    }
  }

  async function cargarCapacidades() {
    const estado = $("cap-estado");
    if (!estado) return;
    estado.classList.remove("error");
    estado.textContent = "consultando el registro de herramientas…";
    try {
      const r = await fetch("/api/capacidades", { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      if (!d.ok) throw new Error("el núcleo no devolvió capacidades");
      ui.capHerramientas = [];
      for (const categoria of d.categorias || []) {
        for (const tool of categoria.herramientas || []) {
          ui.capHerramientas.push({ ...tool, categoriaNombre: categoria.nombre, categoriaId: categoria.id });
        }
      }
      ui.capCargadas = true;
      estado.textContent = `${d.total} herramientas · ${(d.categorias || []).length} categorías · lista permitida`;
      renderCapacidades($("cap-buscar").value);
      if (ui.paletaAbierta) renderPaleta($("paleta-buscar").value);
    } catch (e) {
      ui.capCargadas = false;
      estado.classList.add("error");
      estado.textContent = `No pude leer las capacidades: ${e.message || e}. ¿Sigue vivo el núcleo?`;
      $("cap-lista").innerHTML = "";
    }
  }

  function abrirCapacidades() {
    cerrarModelos();
    cerrarPaleta();
    ui.capacidadesAbiertas = true;
    const panel = $("capacidades");
    panel.hidden = false;
    panel.removeAttribute("aria-hidden");
    if (!ui.capCargadas) cargarCapacidades();
    else renderCapacidades($("cap-buscar").value);
    setTimeout(() => $("cap-buscar").focus(), 40);
  }

  function cerrarCapacidades() {
    ui.capacidadesAbiertas = false;
    const panel = $("capacidades");
    const activo = document.activeElement;
    if (activo && panel.contains(activo)) activo.blur();
    panel.hidden = true;
  }

  function cargarEjemplo(texto) {
    if (!texto) return;
    cerrarCapacidades();
    cerrarPaleta();
    input.value = texto;
    input.focus();
    input.setSelectionRange(texto.length, texto.length);
    toast("Ejemplo cargado · revisá y enviá", 2200);
  }

  /* ---------------- paleta de comandos ---------------- */
  function ciclarEstilo() {
    const orden = ["esfera", "anillo", "cinta", "enjambre"];
    const actual = Math.max(0, orden.indexOf(ui.estilo));
    setEstilo(orden[(actual + 1) % orden.length]);
  }

  async function pantallaCompleta() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch (e) {
      toast("Este entorno no permite pantalla completa.", 2400);
    }
  }

  function accionesPaleta() {
    const acciones = [
      { etiqueta: "Hablar ahora", detalle: "una escucha del micrófono", atajo: "", run: hablarAhora },
      { etiqueta: "Detener el turno", detalle: "corta la voz y el modelo", atajo: "", run: detenerTurno },
      { etiqueta: "Panel de modelos", detalle: "Ollama local, descargas y modelo activo", atajo: "m", run: abrirModelos },
      { etiqueta: "Ver capacidades", detalle: "herramientas reales y ejemplos", atajo: "c", run: abrirCapacidades },
      { etiqueta: "Modo enfoque", detalle: "oculta paneles laterales", atajo: "f", run: () => setEnfoque(!ui.enfocado) },
      { etiqueta: "Silenciar o activar la voz", detalle: "control del TTS local", atajo: "", run: alternarSilencio },
      { etiqueta: "Cambiar estilo del orbe", detalle: "esfera, anillo, cinta o enjambre", atajo: "1–4", run: ciclarEstilo },
      { etiqueta: "Pantalla completa", detalle: "modo kiosco del HUD", atajo: "", run: pantallaCompleta },
      { etiqueta: "Ayuda", detalle: "lista de comandos de CORT", atajo: "", run: () => enviarTexto("ayuda") },
      { etiqueta: "Limpiar contexto", detalle: "borra el hilo; la memoria queda intacta", atajo: "", run: () => enviarTexto("limpia el contexto") },
    ];
    const ejemplos = ui.capHerramientas
      .filter((t) => t.ejemplo)
      .map((t) => ({
        etiqueta: t.ejemplo,
        detalle: `${t.nombre} · ${t.categoriaNombre}`,
        buscar: `${t.ejemplo} ${t.nombre} ${t.descripcion}`,
        atajo: "",
        run: () => cargarEjemplo(t.ejemplo),
      }));
    return acciones.concat(ejemplos);
  }

  function seleccionarPaleta(indice) {
    ui.paletaIndice = indice;
    const lista = $("paleta-lista");
    [...lista.querySelectorAll(".paleta-item")].forEach((el, i) => {
      el.classList.toggle("sel", i === indice);
      el.setAttribute("aria-selected", i === indice ? "true" : "false");
      if (i === indice) el.scrollIntoView({ block: "nearest" });
    });
  }

  function renderPaleta(filtro = "") {
    const lista = $("paleta-lista");
    if (!lista) return;
    const q = normalizar(filtro);
    const items = accionesPaleta().filter((item) => {
      if (!q) return true;
      const texto = item.buscar || `${item.etiqueta} ${item.detalle}`;
      return normalizar(texto).includes(q);
    });
    ui.paletaItems = items;
    lista.innerHTML = "";
    if (!items.length) {
      const vacio = document.createElement("div");
      vacio.className = "paleta-vacio";
      vacio.textContent = "Sin resultados. Probá «modelo», «voz», «hora» o «clima».";
      lista.appendChild(vacio);
      ui.paletaIndice = 0;
      return;
    }
    items.forEach((item, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "paleta-item";
      b.setAttribute("role", "option");
      b.dataset.indice = String(i);
      const titulo = document.createElement("b");
      titulo.textContent = item.etiqueta;
      const atajo = document.createElement("span");
      atajo.className = "atajo";
      atajo.textContent = item.atajo || "";
      const detalle = document.createElement("small");
      detalle.textContent = item.detalle || "";
      b.append(titulo, atajo, detalle);
      b.addEventListener("click", () => ejecutarPaleta(i));
      b.addEventListener("mousemove", () => seleccionarPaleta(i));
      lista.appendChild(b);
    });
    seleccionarPaleta(0);
  }

  function ejecutarPaleta(indice = ui.paletaIndice) {
    const item = ui.paletaItems[indice];
    if (!item) return;
    cerrarPaleta();
    try {
      item.run();
    } catch (e) {
      toast(`No pude ejecutar el comando: ${e.message || e}`, 2600);
    }
  }

  function abrirPaleta() {
    cerrarModelos();
    cerrarCapacidades();
    ui.paletaAbierta = true;
    const panel = $("paleta");
    panel.hidden = false;
    $("paleta-buscar").value = "";
    renderPaleta("");
    setTimeout(() => $("paleta-buscar").focus(), 30);
    if (!ui.capCargadas) cargarCapacidades();
  }

  function cerrarPaleta() {
    ui.paletaAbierta = false;
    const panel = $("paleta");
    if (panel) panel.hidden = true;
    const buscar = $("paleta-buscar");
    if (buscar) buscar.blur();
  }

  function alternarPaleta() {
    if (ui.paletaAbierta) cerrarPaleta();
    else abrirPaleta();
  }

  $("paleta").addEventListener("click", (ev) => {
    if (ev.target === $("paleta")) cerrarPaleta();
  });
  $("paleta-buscar").addEventListener("input", (ev) => renderPaleta(ev.target.value));
  $("paleta-buscar").addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      if (ui.paletaItems.length) seleccionarPaleta((ui.paletaIndice + 1) % ui.paletaItems.length);
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      if (ui.paletaItems.length) seleccionarPaleta((ui.paletaIndice - 1 + ui.paletaItems.length) % ui.paletaItems.length);
    } else if (ev.key === "Enter") {
      ev.preventDefault();
      ejecutarPaleta();
    } else if (ev.key === "Escape") {
      ev.preventDefault();
      cerrarPaleta();
    }
  });
  $("cap-buscar").addEventListener("input", (ev) => renderCapacidades(ev.target.value));
  $("cerrar-capacidades").addEventListener("click", cerrarCapacidades);
  $("abrir-capacidades").addEventListener("click", abrirCapacidades);
  $("abrir-paleta").addEventListener("click", alternarPaleta);
  $("rail-capacidades").addEventListener("click", abrirCapacidades);
  $("rail-comandos").addEventListener("click", alternarPaleta);
  $("rail-modelos").addEventListener("click", abrirModelos);
  $("rail-hablar").addEventListener("click", hablarAhora);
  $("rail-stop").addEventListener("click", detenerTurno);
  $("rail-silencio").addEventListener("click", alternarSilencio);
  $("rail-enfoque").addEventListener("click", () => setEnfoque(!ui.enfocado));
  $("rail-pantalla").addEventListener("click", pantallaCompleta);

  /* ---------------- arranque ---------------- */
  function iniciarArranque() {
    const boot = $("boot");
    if (!boot) return;
    let forzado = false;
    try { forzado = new URLSearchParams(location.search).has("noboot"); } catch (e) { /* sin URL */ }
    let yaVisto = false;
    try { yaVisto = sessionStorage.getItem("cort.arranque") === "1"; } catch (e) { /* sin almacenamiento */ }
    if (CAPTURA || reducido || forzado || yaVisto) {
      boot.classList.add("oculto");
      boot.remove();
      return;
    }
    document.body.classList.add("booteando");
    const cont = $("boot-lineas");
    const lineas = [
      ["modo", "local"],
      ["datos", "en esta máquina"],
      ["voz", "según configuración"],
      ["hud", "listo"],
    ];
    let i = 0;
    let hecho = false;
    const reloj = setInterval(() => {
      if (i >= lineas.length) return;
      const fila = document.createElement("div");
      const nombre = document.createElement("span");
      nombre.textContent = lineas[i][0];
      const valor = document.createElement("b");
      valor.textContent = lineas[i][1];
      fila.append(nombre, valor);
      cont.appendChild(fila);
      i += 1;
      if (i >= lineas.length) {
        clearInterval(reloj);
        setTimeout(fin, 380);
      }
    }, 150);
    function fin() {
      if (hecho) return;
      hecho = true;
      clearInterval(reloj);
      try { sessionStorage.setItem("cort.arranque", "1"); } catch (e) { /* sin almacenamiento */ }
      boot.classList.add("oculto");
      document.body.classList.remove("booteando");
      setTimeout(() => boot.remove(), 700);
    }
    boot.addEventListener("click", fin);
    window.addEventListener("keydown", fin, { once: true });
  }

  document.addEventListener("keydown", (ev) => {
    const escribiendo = /^(INPUT|TEXTAREA|SELECT)$/.test((ev.target && ev.target.tagName) || "");
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "k" || ev.key === "K")) {
      ev.preventDefault();
      alternarPaleta();
      return;
    }
    if (ev.key === "Escape") {
      if (ui.paletaAbierta) {
        cerrarPaleta();
      } else if (ui.capacidadesAbiertas) {
        cerrarCapacidades();
      } else if (ui.modelosAbiertos) {
        cerrarModelos();
      } else if (escribiendo) {
        input.value = "";
        input.blur();
      } else {
        $("ejecucion").classList.remove("visible");
      }
      return;
    }
    if (!escribiendo && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
      if (ev.key === "f" || ev.key === "F") {
        ev.preventDefault();
        setEnfoque(!ui.enfocado);
      } else if (ev.key === "1") setEstilo("esfera");
      else if (ev.key === "2") setEstilo("anillo");
      else if (ev.key === "3") setEstilo("cinta");
      else if (ev.key === "4") setEstilo("enjambre");
      else if (ev.key === "m" || ev.key === "M") abrirModelos();
      else if (ev.key === "c" || ev.key === "C") abrirCapacidades();
    }
  });

  iniciarArranque();

  /* ---------------- orbe ---------------- */
  const canvas = $("orb");
  const ctx = canvas.getContext("2d", { alpha: true });
  let W = 0, H = 0, DPR = 1;
  let puntos = [];
  let pares = [];
  let ultimoFrame = 0;
  let visible = true;
  let color = [...COLORES.idle];
  let colorHebra = [255, 255, 255];
  let burst = null;
  let calidad = 1;
  let costoMedio = 14;

  function cantidadPuntos() {
    if (reducido) return 180;
    if (W < 640) return 300;
    if (W < 1180) return 520;
    return 700;
  }

  function crearPuntos(n, estilo) {
    const salida = [];
    for (let i = 0; i < n; i++) {
      let x = 0, y = 0, z = 0;
      if (estilo === "anillo") {
        const u = (i / n) * TAU * 3 + (i % 5) * 0.02;
        const v = i * 2.399963229728653;
        const radio = 0.76 + 0.22 * Math.cos(v) + (Math.random() - 0.5) * 0.035;
        x = Math.cos(u) * radio;
        y = Math.sin(v) * 0.24 + Math.sin(u * 2 + v) * 0.025;
        z = Math.sin(u) * radio;
      } else if (estilo === "cinta") {
        const u = (i / n) * TAU;
        const ancho = 0.2 + 0.06 * Math.sin(u * 5);
        const v = Math.sin(u * 3 + i * 0.001) * ancho;
        const radio = 0.82;
        x = (radio + v * Math.cos(u / 2)) * Math.cos(u);
        z = (radio + v * Math.cos(u / 2)) * Math.sin(u);
        y = v * Math.sin(u / 2) * 2.4 + Math.sin(u * 2) * 0.045;
      } else if (estilo === "enjambre") {
        const r = 0.68 + Math.random() * 0.42;
        const phi = Math.acos(2 * Math.random() - 1);
        const theta = Math.random() * TAU;
        x = r * Math.sin(phi) * Math.cos(theta);
        y = r * Math.cos(phi);
        z = r * Math.sin(phi) * Math.sin(theta);
      } else {
        const y0 = 1 - (i / (n - 1)) * 2;
        const r = Math.sqrt(Math.max(0, 1 - y0 * y0));
        const th = Math.PI * (3 - Math.sqrt(5)) * i;
        /* radio irregular: la silueta del ovillo no es un círculo perfecto */
        const onda = 1 + 0.03 * Math.sin(i * 1.7) + (Math.random() - 0.5) * 0.075;
        x = Math.cos(th) * r * onda;
        y = y0 * onda;
        z = Math.sin(th) * r * onda;
      }
      salida.push({
        x, y, z,
        bx: x, by: y, bz: z,
        tx: x, ty: y, tz: z,
        ph: Math.random() * TAU,
        s: 0.5 + Math.random() * 1.15,
        imp: 0,
      });
    }
    return salida;
  }

  function crearPares(pts, estilo) {
    const salida = [];
    const n = pts.length;
    const umbral = estilo === "enjambre" ? 0.17 : estilo === "anillo" ? 0.2 : 0.235;
    const umbral2 = umbral * umbral;
    const maxPor = estilo === "cinta" ? 4 : 3;
    const tope = estilo === "enjambre" ? 360 : estilo === "cinta" ? 880 : 680;
    const cuenta = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
      const a = pts[i];
      for (let j = i + 1; j < n; j++) {
        if (cuenta[i] >= maxPor && cuenta[j] >= maxPor) continue;
        const b = pts[j];
        const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 > umbral2) continue;
        if (cuenta[i] >= maxPor || cuenta[j] >= maxPor) continue;
        salida.push([i, j, Math.random() * 2 - 1, Math.random()]);
        cuenta[i]++;
        cuenta[j]++;
        if (salida.length >= tope) return salida;
      }
    }
    if (estilo === "cinta") {
      for (let i = 0; i + 2 < n; i += 2) {
        salida.push([i, i + 2, 0.4, Math.random()]);
      }
    }
    return salida;
  }

  /* hebras largas sobre la esfera: el ovillo luminoso de la referencia */
  let hebras = [];
  let motas = [];

  function crearHebras() {
    /* cáscara: arcos rotos pegados al borde, no círculos máximos completos */
    const total = reducido ? 34 : W < 640 ? 50 : W < 1180 ? 62 : 74;
    hebras = [];
    for (let k = 0; k < total; k++) {
      let ux = Math.random() * 2 - 1;
      let uy = Math.random() * 2 - 1;
      let uz = Math.random() * 2 - 1;
      const modulo = Math.hypot(ux, uy, uz) || 1;
      ux /= modulo; uy /= modulo; uz /= modulo;
      /* base perpendicular al eje del círculo máximo */
      let bx = -uy, by = ux, bz = 0;
      if (Math.abs(bx) + Math.abs(by) < 0.001) { bx = 1; by = 0; bz = 0; }
      const bl = Math.hypot(bx, by, bz) || 1;
      bx /= bl; by /= bl; bz /= bl;
      const cxv = uy * bz - uz * by;
      const cyv = uz * bx - ux * bz;
      const czv = ux * by - uy * bx;
      const radio = 0.66 + Math.pow(Math.random(), 0.7) * 0.44;
      const inicio = Math.random() * TAU;
      const arco = TAU * (0.06 + Math.pow(Math.random(), 1.6) * 0.34);
      const pasos = 26;
      const f1 = 1.3 + Math.random() * 2.6;
      const f2 = 3.5 + Math.random() * 4.5;
      const fase = Math.random() * TAU;
      const amp1 = 0.018 + Math.random() * 0.075;
      const amp2 = 0.008 + Math.random() * 0.04;
      const pts = [];
      for (let i = 0; i <= pasos; i++) {
        const a = inicio + (arco * i) / pasos;
        const ca = Math.cos(a), sa = Math.sin(a);
        let px = bx * ca + cxv * sa;
        let py = by * ca + cyv * sa;
        let pz = bz * ca + czv * sa;
        const r = radio * (1 + amp1 * Math.sin(a * f1 + fase) + amp2 * Math.sin(a * f2 - fase));
        const vibra = 1 + 0.012 * Math.sin(i * 12.9898 + k * 78.233);
        px *= r * vibra; py *= r * vibra; pz *= r * vibra;
        /* serpenteo fuera del círculo perfecto: hebras de verdad, no aros */
        px += 0.038 * Math.sin(i * 1.3 + fase);
        py += 0.038 * Math.sin(i * 2.7 + fase * 1.4);
        pz += 0.038 * Math.sin(i * 1.9 + fase * 0.7);
        pts.push([px, py, pz]);
      }
      hebras.push({ pts, brillo: 0.5 + Math.random() * 0.35, fase });
    }

    /* brazos: filamentos que nacen en el núcleo y estallan hacia la silueta,
       el gesto dominante del orbe en reposo del video */
    const brazos = reducido ? 14 : W < 640 ? 20 : W < 1180 ? 26 : 34;
    for (let k = 0; k < brazos; k++) {
      const phi = Math.acos(2 * Math.random() - 1);
      const th = Math.random() * TAU;
      const dx = Math.sin(phi) * Math.cos(th);
      const dy = Math.cos(phi);
      const dz = Math.sin(phi) * Math.sin(th);
      let bx = -dy, by = dx, bz = 0;
      if (Math.abs(bx) + Math.abs(by) < 0.001) { bx = 1; by = 0; bz = 0; }
      const bl = Math.hypot(bx, by, bz) || 1;
      bx /= bl; by /= bl; bz /= bl;
      const curl = (0.7 + Math.random() * 1.6) * (Math.random() < 0.5 ? -1 : 1);
      const rIni = 0.12 + Math.random() * 0.2;
      const rFin = 0.82 + Math.random() * 0.33;
      const fase = Math.random() * TAU;
      const pasos = 22;
      const pts = [];
      for (let i = 0; i <= pasos; i++) {
        const t = i / pasos;
        const a = curl * t;
        const r = (rIni + (rFin - rIni) * Math.pow(t, 0.9)) * (1 + 0.035 * Math.sin(i * 1.9 + fase));
        const ca = Math.cos(a), sa = Math.sin(a);
        const ondula = 0.018 * Math.sin(i * 2.2 + fase);
        pts.push([
          (dx * ca + bx * sa) * r + ondula,
          (dy * ca + by * sa) * r + 0.014 * Math.sin(i * 1.6 + fase * 1.3),
          (dz * ca + bz * sa) * r + 0.016 * Math.sin(i * 2.9 + fase * 0.7),
        ]);
      }
      hebras.push({ pts, brillo: 0.85 + Math.random() * 0.25, fase });
    }

    /* puntas cortas que sobresalen del ovillo: silueta irregular */
    const puntas = reducido ? 14 : W < 640 ? 24 : W < 1180 ? 34 : 46;
    for (let k = 0; k < puntas; k++) {
      let ux = Math.random() * 2 - 1;
      let uy = Math.random() * 2 - 1;
      let uz = Math.random() * 2 - 1;
      const modulo = Math.hypot(ux, uy, uz) || 1;
      ux /= modulo; uy /= modulo; uz /= modulo;
      let bx = -uy, by = ux, bz = 0;
      if (Math.abs(bx) + Math.abs(by) < 0.001) { bx = 1; }
      const bl = Math.hypot(bx, by, bz) || 1;
      bx /= bl; by /= bl; bz /= bl;
      const cxv = uy * bz - uz * by;
      const cyv = uz * bx - ux * bz;
      const czv = ux * by - uy * bx;
      const radio = 0.98 + Math.random() * 0.2;
      const inicio = Math.random() * TAU;
      const arco = 0.04 + Math.random() * 0.14;
      const fase = Math.random() * TAU;
      const pts = [];
      for (let i = 0; i <= 6; i++) {
        const a = inicio + (arco * i) / 6;
        const r = radio * (1 + 0.05 * Math.sin(a * 9 + fase));
        pts.push([
          (bx * Math.cos(a) + cxv * Math.sin(a)) * r + 0.02 * Math.sin(i * 2.3 + fase),
          (by * Math.cos(a) + cyv * Math.sin(a)) * r + 0.02 * Math.sin(i * 1.6 + fase),
          (bz * Math.cos(a) + czv * Math.sin(a)) * r + 0.02 * Math.sin(i * 2.9 + fase),
        ]);
      }
      hebras.push({ pts, brillo: 0.7 + Math.random() * 0.3, fase });
    }

    /* hebras interiores: rellenan el volumen, no sólo la cáscara */
    const interiores = reducido ? 16 : W < 640 ? 30 : W < 1180 ? 42 : 54;
    for (let k = 0; k < interiores; k++) {
      let ux = Math.random() * 2 - 1;
      let uy = Math.random() * 2 - 1;
      let uz = Math.random() * 2 - 1;
      const modulo = Math.hypot(ux, uy, uz) || 1;
      ux /= modulo; uy /= modulo; uz /= modulo;
      let bx = -uy, by = ux, bz = 0;
      if (Math.abs(bx) + Math.abs(by) < 0.001) { bx = 1; by = 0; bz = 0; }
      const bl = Math.hypot(bx, by, bz) || 1;
      bx /= bl; by /= bl; bz /= bl;
      const cxv = uy * bz - uz * by;
      const cyv = uz * bx - ux * bz;
      const czv = ux * by - uy * bx;
      const radio = 0.12 + Math.pow(Math.random(), 1.35) * 0.55;
      const inicio = Math.random() * TAU;
      const arco = TAU * (0.1 + Math.random() * 0.55);
      const pasos = 20;
      const fase = Math.random() * TAU;
      const pts = [];
      for (let i = 0; i <= pasos; i++) {
        const a = inicio + (arco * i) / pasos;
        const r = radio * (1 + 0.1 * Math.sin(a * 3 + fase));
        pts.push([
          (bx * Math.cos(a) + cxv * Math.sin(a)) * r + 0.02 * Math.sin(i * 2.1 + fase),
          (by * Math.cos(a) + cyv * Math.sin(a)) * r + 0.02 * Math.sin(i * 1.4 + fase),
          (bz * Math.cos(a) + czv * Math.sin(a)) * r + 0.02 * Math.sin(i * 2.7 + fase),
        ]);
      }
      hebras.push({ pts, brillo: 0.72 + Math.random() * 0.28, fase });
    }

    /* polvo luminoso alrededor de la silueta: el borde nunca queda limpio */
    motas = [];
    const totalMotas = reducido ? 56 : W < 640 ? 108 : 184;
    for (let k = 0; k < totalMotas; k++) {
      const phi = Math.acos(2 * Math.random() - 1);
      const th = Math.random() * TAU;
      const r = k % 5 < 3 ? 0.15 + Math.random() * 0.5 : 0.85 + Math.random() * 0.5;
      motas.push({
        x: Math.sin(phi) * Math.cos(th) * r,
        y: Math.cos(phi) * r,
        z: Math.sin(phi) * Math.sin(th) * r,
        s: 0.25 + Math.random() * 0.7,
        ph: Math.random() * TAU,
      });
    }
  }

  let escalaPuntos = 1;

  function cambiarEstiloOrbe(nuevo) {
    const n = puntos.length || cantidadPuntos();
    const nuevos = crearPuntos(n, nuevo);
    if (!puntos.length) {
      puntos = nuevos;
    } else {
      for (let i = 0; i < puntos.length; i++) {
        const p = puntos[i];
        const q = nuevos[i] || nuevos[nuevos.length - 1];
        p.tx = q.x;
        p.ty = q.y;
        p.tz = q.z;
        p.ph = q.ph;
        p.s = q.s;
      }
    }
    pares = crearPares(puntos.map((p) => ({ x: p.tx, y: p.ty, z: p.tz })), nuevo);
  }

  function redimensionar() {
    DPR = Math.min(window.devicePixelRatio || 1, 1.5);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.floor(W * DPR);
    canvas.height = Math.floor(H * DPR);
    canvas.style.width = `${W}px`;
    canvas.style.height = `${H}px`;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    const n = cantidadPuntos();
    if (!puntos.length) {
      puntos = crearPuntos(n, ui.estilo);
      pares = crearPares(puntos, ui.estilo);
    } else if (n !== puntos.length) {
      const actuales = puntos.map((p) => ({ x: p.bx, y: p.by, z: p.bz }));
      puntos = crearPuntos(n, ui.estilo);
      for (let i = 0; i < n; i++) {
        const prev = actuales[i % Math.max(1, actuales.length)] || { x: 0, y: 0, z: 0 };
        puntos[i].bx = prev.x;
        puntos[i].by = prev.y;
        puntos[i].bz = prev.z;
      }
      pares = crearPares(puntos, ui.estilo);
    }
    if (!hebras.length) crearHebras();
    const g = geometriaOrbe();
    document.documentElement.style.setProperty("--orbe-centro", `${g.cy}px`);
    document.documentElement.style.setProperty("--orbe-radio", `${g.R}px`);
  }

  function geometriaOrbe() {
    const cx = W / 2;
    const cy = H * (W < 700 ? 0.37 : 0.405);
    const base = Math.min(W, H) * (W < 700 ? 0.235 : 0.18);
    const R = Math.max(92, Math.min(210, base));
    return { cx, cy, R };
  }

  function mezclar(a, b, f) {
    a[0] += (b[0] - a[0]) * f;
    a[1] += (b[1] - a[1]) * f;
    a[2] += (b[2] - a[2]) * f;
  }

  function rgba(alpha) {
    return `rgba(${color[0] | 0},${color[1] | 0},${color[2] | 0},${alpha})`;
  }

  function rgbaH(alpha) {
    return `rgba(${colorHebra[0] | 0},${colorHebra[1] | 0},${colorHebra[2] | 0},${alpha})`;
  }

  function dibujarPlasma(now, cx, cy, R, estado) {
    if (ui.estilo === "anillo") {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(now * 0.00018);
      for (let k = 0; k < 4; k++) {
        const rr = R * (1.02 + k * 0.08 + 0.02 * Math.sin(now * 0.001 + k));
        ctx.beginPath();
        ctx.ellipse(0, 0, rr, rr * 0.38, k * 0.12, 0, TAU);
        ctx.strokeStyle = rgba(0.05 + k * 0.018);
        ctx.lineWidth = k === 0 ? 1.5 : 0.8;
        ctx.stroke();
      }
      for (let k = 0; k < 14; k++) {
        const a = now * 0.0005 + k * 0.77;
        const r1 = R * 0.72;
        const r2 = R * (1.02 + 0.12 * Math.sin(now * 0.0012 + k));
        ctx.beginPath();
        ctx.moveTo(Math.cos(a) * r1, Math.sin(a) * r1 * 0.38);
        ctx.lineTo(Math.cos(a + 0.08) * r2, Math.sin(a + 0.08) * r2 * 0.38);
        ctx.strokeStyle = rgba(0.03 + 0.03 * Math.sin(a * 3));
        ctx.stroke();
      }
      ctx.restore();
      return;
    }

    if (ui.estilo === "cinta") {
      const n = 70;
      for (let capa = 0; capa < 3; capa++) {
        ctx.beginPath();
        for (let i = 0; i <= n; i++) {
          const u = (i / n) * TAU;
          const v = Math.sin(u * 3 + now * 0.0008 + capa * 0.8) * (0.18 + capa * 0.04);
          const radio = R * 0.9;
          const x = (radio + v * Math.cos(u / 2)) * Math.cos(u);
          const z = (radio + v * Math.cos(u / 2)) * Math.sin(u);
          const y = v * Math.sin(u / 2) * 2.2 + Math.sin(u * 2) * R * 0.04;
          const px = cx + x;
          const py = cy + y;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.strokeStyle = rgba(0.05 + capa * 0.02);
        ctx.lineWidth = capa === 0 ? 1.6 : 0.8;
        ctx.stroke();
      }
      return;
    }

    if (ui.estilo === "enjambre") {
      for (let k = 0; k < 10; k++) {
        const a = now * 0.0004 + k * 0.63;
        const fin = R * (1.05 + 0.14 * Math.sin(now * 0.001 + k));
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.bezierCurveTo(
          cx + Math.cos(a + 0.4) * R * 0.38,
          cy + Math.sin(a + 0.4) * R * 0.38,
          cx + Math.cos(a - 0.5) * R * 0.72,
          cy + Math.sin(a - 0.5) * R * 0.72,
          cx + Math.cos(a) * fin,
          cy + Math.sin(a) * fin
        );
        ctx.strokeStyle = rgba(0.035 + 0.02 * Math.sin(now * 0.002 + k));
        ctx.lineWidth = 0.9;
        ctx.stroke();
      }
      return;
    }

    /* esfera: curvas de plasma y anillos */
    for (let k = 0; k < 5; k++) {
      const ang = now * 0.00035 + (k / 5) * TAU;
      const fin = R * (0.96 + 0.08 * Math.sin(now * 0.0011 + k));
      const c1x = cx + Math.cos(ang + 0.6) * R * 0.48;
      const c1y = cy + Math.sin(ang + 0.6) * R * 0.48;
      const c2x = cx + Math.cos(ang - 0.4) * R * 0.78;
      const c2y = cy + Math.sin(ang - 0.4) * R * 0.78;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.bezierCurveTo(c1x, c1y, c2x, c2y, cx + Math.cos(ang) * fin, cy + Math.sin(ang) * fin);
      ctx.strokeStyle = rgba(0.05 + 0.03 * Math.sin(now * 0.002 + k));
      ctx.lineWidth = 1.05;
      ctx.stroke();
    }
    const giro = now * (estado === "thinking" ? 0.00055 : 0.00013);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(giro);
    ctx.beginPath();
    ctx.ellipse(0, 0, R * 1.2, R * 1.2 * 0.4, 0, 0, TAU);
    ctx.strokeStyle = rgba(0.14);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.beginPath();
    ctx.ellipse(0, 0, R * 1.33, R * 1.33 * 0.33, 0.5, 0, TAU);
    ctx.strokeStyle = rgba(0.08);
    ctx.stroke();
    for (let i = 0; i < 72; i++) {
      const a = (i / 72) * TAU;
      const largo = i % 6 === 0 ? 7 : 3;
      const r1 = R * 1.37;
      ctx.beginPath();
      ctx.moveTo(Math.cos(a) * r1, Math.sin(a) * r1);
      ctx.lineTo(Math.cos(a) * (r1 + largo), Math.sin(a) * (r1 + largo));
      ctx.strokeStyle = rgba(i % 6 === 0 ? 0.2 : 0.08);
      ctx.stroke();
    }
    ctx.restore();
  }

  const RAYOS = Array.from({ length: 22 }, (_, i) => ({
    ang: (i / 22) * TAU,
    largo: 0.55 + ((i * 37) % 100) / 145,
    fino: i % 3 === 0,
    fase: (i * 1.7) % TAU,
  }));

  function dibujarArcos(now, cx, cy, R, estado) {
    const giroBase = now * (estado === "thinking" ? 0.00034 : 0.00016);
    const arcos = [
      { radio: 1.0, incl: 1.18, giro: giroBase, vel: 0.0009 },
      { radio: 1.03, incl: 0.42, giro: -giroBase * 1.3 + 0.7, vel: -0.0011 },
      { radio: 0.97, incl: 1.62, giro: giroBase * 0.7 + 1.9, vel: 0.0014 },
    ];
    ctx.lineWidth = 0.9;
    arcos.forEach((arco, indice) => {
      const cosI = Math.cos(arco.incl), sinI = Math.sin(arco.incl);
      const cosG = Math.cos(arco.giro), sinG = Math.sin(arco.giro);
      const n = 54;
      for (let i = 0; i < n; i++) {
        if ((i + indice * 3) % 13 < 5) continue;
        const a = (i / n) * TAU;
        const x0 = Math.cos(a) * arco.radio * R;
        const z0 = Math.sin(a) * arco.radio * R;
        const y1 = -z0 * sinI;
        const z1 = z0 * cosI;
        const x2 = x0 * cosG - z1 * sinG;
        const z2 = x0 * sinG + z1 * cosG;
        const prof = (z2 / R + 1) / 2;
        const px = cx + x2;
        const py = cy + y1;
        const tam = 0.45 + prof * 1.15;
        ctx.beginPath();
        ctx.arc(px, py, tam, 0, TAU);
        ctx.fillStyle = rgba(0.045 + prof * 0.3);
        ctx.fill();
      }
      /* chispa que recorre el arco con estela */
      const avance = now * arco.vel + indice * 2.1;
      for (let k = 0; k < 4; k++) {
        const a = avance - k * 0.045;
        const x0 = Math.cos(a) * arco.radio * R;
        const z0 = Math.sin(a) * arco.radio * R;
        const y1 = -z0 * sinI;
        const z1 = z0 * cosI;
        const x2 = x0 * cosG - z1 * sinG;
        const z2 = x0 * sinG + z1 * cosG;
        const prof = (z2 / R + 1) / 2;
        ctx.beginPath();
        ctx.arc(cx + x2, cy + y1, 1.6 - k * 0.3, 0, TAU);
        ctx.fillStyle = rgba((0.55 - k * 0.12) * (0.35 + prof * 0.65));
        ctx.fill();
      }
    });
  }

  function dibujarToro(now, cx, cy, R, estado) {
    if (!["thinking", "downloading", "executing", "listening"].includes(estado)) return;
    const progreso = estado === "downloading" && ui.descargaPct != null
      ? ui.descargaPct / 100
      : null;
    const incl = 1.02 + Math.sin(now * 0.0005) * 0.08;
    const giro = now * (estado === "downloading" ? 0.00055 : 0.00032);
    const cosI = Math.cos(incl), sinI = Math.sin(incl);
    const cosG = Math.cos(giro), sinG = Math.sin(giro);
    const Rm = R * 0.86;
    const r = R * 0.2;
    const brillo = estado === "downloading" ? 0.2 : estado === "thinking" ? 0.17 : 0.11;
    const anillos = 5;
    const pasos = 26;
    for (let j = 0; j < anillos; j++) {
      const phi = (j / anillos) * TAU + now * 0.0004;
      const anillo = Rm + Math.cos(phi) * r;
      const altura = Math.sin(phi) * r;
      for (let i = 0; i < pasos; i++) {
        const theta = (i / pasos) * TAU;
        const x0 = Math.cos(theta) * anillo;
        const z0 = Math.sin(theta) * anillo;
        const y1 = altura - z0 * sinI * 0.55;
        const z1 = z0 * cosI;
        const x2 = x0 * cosG - z1 * sinG;
        const z2 = x0 * sinG + z1 * cosG;
        const prof = (z2 / R + 1) / 2;
        if (progreso != null) {
          const marca = ((theta / TAU) - progreso + 1) % 1;
          if (marca < 0.75) continue;
        }
        ctx.beginPath();
        ctx.arc(cx + x2, cy + y1, 0.5 + prof * 1.5, 0, TAU);
        ctx.fillStyle = rgba(brillo * (0.25 + prof * 0.9));
        ctx.fill();
      }
    }
  }

  function dibujarEstrella(now, cx, cy, R, estado) {
    const fuerza = estado === "executing" ? 1.35
      : estado === "speaking" ? 1.1
        : estado === "thinking" ? 0.95
          : estado === "downloading" ? 0.8
            : 0.72;
    const giro = now * 0.00016;
    for (let k = 0; k < RAYOS.length; k++) {
      const rayo = RAYOS[k];
      const a = rayo.ang + giro;
      const pulso = 0.82 + 0.18 * Math.sin(now * 0.0022 + rayo.fase);
      const largo = R * 0.62 * rayo.largo * fuerza * pulso;
      const ancho = rayo.fino ? 0.7 : 1.35;
      const grad = ctx.createLinearGradient(cx, cy, cx + Math.cos(a) * largo, cy + Math.sin(a) * largo);
      grad.addColorStop(0, "rgba(255,255,255,0.8)");
      grad.addColorStop(0.25, rgba(0.5));
      grad.addColorStop(1, rgba(0));
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * R * 0.04, cy + Math.sin(a) * R * 0.04);
      ctx.lineTo(cx + Math.cos(a) * largo, cy + Math.sin(a) * largo);
      ctx.strokeStyle = grad;
      ctx.lineWidth = ancho;
      ctx.stroke();
    }
    for (let k = 0; k < 3; k++) {
      const a = now * 0.0009 + k * 2.1;
      const rr = R * (0.28 + 0.06 * k);
      ctx.beginPath();
      ctx.arc(cx + Math.cos(a) * rr * 0.35, cy + Math.sin(a) * rr * 0.35, 1.2, 0, TAU);
      ctx.fillStyle = "rgba(255,255,255,0.75)";
      ctx.fill();
    }
  }

  /* hebras del ovillo: arcos de círculo máximo con grosor y brillo por profundidad */
  function dibujarHebras(now, cx, cy, R, cosY, sinY, cosX, sinX, estado) {
    const pulso = estado === "speaking"
      ? 1 + 0.14 * Math.sin(now * 0.012)
      : estado === "listening"
        ? 1 + 0.05 * Math.sin(now * 0.006)
        : 1;
    const tramos = 4;
    const cubosH = [new Path2D(), new Path2D(), new Path2D(), new Path2D()];
    const cubosBloom = [new Path2D(), new Path2D(), new Path2D(), new Path2D()];
    const chispasH = [];
    for (let h = 0; h < hebras.length; h++) {
      if ((h % 100) / 100 > calidad) continue;
      const hebra = hebras[h];
      const pts = hebra.pts;
      const proj = new Array(pts.length);
      const resp = 1 + 0.02 * Math.sin(now * 0.0016 + hebra.fase);
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        const x1 = p[0] * cosY - p[2] * sinY;
        const z1 = p[0] * sinY + p[2] * cosY;
        const y2 = p[1] * cosX - z1 * sinX;
        const z2 = p[1] * sinX + z1 * cosX;
        proj[i] = [cx + x1 * R * resp, cy + y2 * R * resp, (z2 + 1) / 2];
      }
      for (let t = 0; t < tramos; t++) {
        if ((h * 3 + t * 5) % 13 === 0) continue;
        const desde = Math.floor((t / tramos) * (proj.length - 1));
        const hasta = Math.floor(((t + 1) / tramos) * (proj.length - 1));
        let prof = 0;
        for (let i = desde; i <= hasta; i++) prof += proj[i][2];
        prof /= Math.max(1, hasta - desde + 1);
        const qx = proj[Math.floor((desde + hasta) / 2)][0];
        const qy = proj[Math.floor((desde + hasta) / 2)][1];
        const centro = Math.max(0, 1 - Math.hypot(qx - cx, qy - cy) / (R * 1.08));
        const nivel = Math.min(0.999, (0.3 + 0.7 * prof) * (0.45 + 0.55 * centro) * hebra.brillo);
        const cn = Math.max(0, Math.min(3, Math.floor(nivel * 4)));
        const cubo = cubosH[cn];
        cubo.moveTo(proj[desde][0], proj[desde][1]);
        for (let i = desde + 1; i <= hasta; i++) cubo.lineTo(proj[i][0], proj[i][1]);
        const bloom = cubosBloom[cn];
        bloom.moveTo(proj[desde][0], proj[desde][1]);
        for (let i = desde + 1; i <= hasta; i++) bloom.lineTo(proj[i][0], proj[i][1]);
      }
      if (h % 7 === 0) {
        const t = (now * 0.00022 + hebra.fase / TAU) % 1;
        const idx = Math.min(proj.length - 1, Math.floor(t * (proj.length - 1)));
        const q = proj[idx];
        if (q[2] > 0.4) chispasH.push(q);
      }
    }
    /* primero la bruma ancha de todos los tramos, después el hilo nítido encima */
    for (let cb = 0; cb < 4; cb++) {
      const pb = (cb + 0.5) / 4;
      const alpha = (0.16 + Math.pow(pb, 1.2) * 0.8) * pulso;
      ctx.strokeStyle = rgbaH(alpha * 0.22);
      ctx.lineWidth = 3.5 + pb * 5;
      ctx.stroke(cubosBloom[cb]);
    }
    for (let cb = 0; cb < 4; cb++) {
      const pb = (cb + 0.5) / 4;
      const alpha = (0.16 + Math.pow(pb, 1.2) * 0.8) * pulso;
      ctx.strokeStyle = rgbaH(alpha);
      ctx.lineWidth = 0.5 + pb * pb * 1.9;
      ctx.stroke(cubosH[cb]);
    }
    for (let i = 0; i < chispasH.length; i++) {
      const q = chispasH[i];
      ctx.beginPath();
      ctx.arc(q[0], q[1], 1.2 + q[2] * 1.1, 0, TAU);
      ctx.fillStyle = rgbaH(0.75 * q[2]);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(q[0], q[1], 3.5 + q[2] * 3, 0, TAU);
      ctx.fillStyle = rgbaH(0.07 * q[2]);
      ctx.fill();
    }
  }

  /* polvo y esquirlas que flotan en la superficie y fuera de ella */
  function dibujarMotas(now, cx, cy, R, cosY, sinY, cosX, sinX) {
    const cubosM = [new Path2D(), new Path2D(), new Path2D(), new Path2D()];
    const cuboMHalo = new Path2D();
    for (let i = 0; i < motas.length; i++) {
      if ((i % 100) / 100 > calidad) continue;
      const m = motas[i];
      const x1 = m.x * cosY - m.z * sinY;
      const z1 = m.x * sinY + m.z * cosY;
      const y2 = m.y * cosX - z1 * sinX;
      const z2 = m.y * sinX + z1 * cosX;
      const prof = (z2 + 1) / 2;
      const deriva = 1 + 0.02 * Math.sin(now * 0.0007 + m.ph);
      const px = cx + x1 * R * deriva;
      const py = cy + y2 * R * deriva;
      const tam = m.s * (0.45 + prof * 1.1);
      const cubo = cubosM[Math.max(0, Math.min(3, Math.floor(prof * 4)))];
      cubo.moveTo(px + tam, py);
      cubo.arc(px, py, tam, 0, TAU);
      if (prof > 0.85 && m.s > 1.1) {
        cuboMHalo.moveTo(px + m.s * 3.2, py);
        cuboMHalo.arc(px, py, m.s * 3.2, 0, TAU);
      }
    }
    for (let cb = 0; cb < 4; cb++) {
      const pb = (cb + 0.5) / 4;
      ctx.fillStyle = rgbaH(0.06 + pb * 0.7);
      ctx.fill(cubosM[cb]);
    }
    ctx.fillStyle = rgbaH(0.035);
    ctx.fill(cuboMHalo);
  }

  /* destello de cámara: rayos largos que atraviesan el ovillo */
  function dibujarFogonazo(now, cx, cy, R, estado) {
    if (estado === "offline") return;
    const fuerza = estado === "speaking" ? 1.15
      : estado === "executing" ? 1.1
        : estado === "error" ? 1.2
          : 1;
    const base = -0.62 + Math.sin(now * 0.00018) * 0.22;
    const lx = cx - R * 0.045;
    const ly = cy - R * 0.035;
    const bloom = ctx.createRadialGradient(lx, ly, 0, lx, ly, R * 0.95);
    bloom.addColorStop(0, "rgba(255,255,255,0.5)");
    bloom.addColorStop(0.12, "rgba(255,255,255,0.3)");
    bloom.addColorStop(0.34, "rgba(255,255,255,0.11)");
    bloom.addColorStop(0.66, "rgba(255,255,255,0.03)");
    bloom.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = bloom;
    ctx.fillRect(lx - R, ly - R, R * 2, R * 2);
    const rayos = [
      { a: base, l: 1.5, w: 2.2, al: 0.62 },
      { a: base + Math.PI, l: 1.22, w: 1.4, al: 0.42 },
      { a: base + 2.35, l: 1.0, w: 0.9, al: 0.3 },
      { a: base - 1.35, l: 0.9, w: 0.8, al: 0.24 },
    ];
    for (let k = 0; k < rayos.length; k++) {
      const rayo = rayos[k];
      const a = rayo.a + Math.sin(now * 0.0009 + k * 1.7) * 0.03;
      const largo = R * rayo.l * fuerza * (0.92 + 0.08 * Math.sin(now * 0.0016 + k));
      const finX = lx + Math.cos(a) * largo;
      const finY = ly + Math.sin(a) * largo;
      const nx = -Math.sin(a);
      const ny = Math.cos(a);
      const grad = ctx.createLinearGradient(lx, ly, finX, finY);
      grad.addColorStop(0, `rgba(255,255,255,${rayo.al})`);
      grad.addColorStop(0.22, `rgba(255,255,255,${rayo.al * 0.4})`);
      grad.addColorStop(1, "rgba(255,255,255,0)");
      ctx.beginPath();
      ctx.moveTo(lx + nx * rayo.w, ly + ny * rayo.w);
      ctx.lineTo(lx - nx * rayo.w, ly - ny * rayo.w);
      ctx.lineTo(finX, finY);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      /* haz ancho y tenue: la bruma del destello */
      ctx.beginPath();
      ctx.moveTo(lx + nx * rayo.w * 2.6, ly + ny * rayo.w * 2.6);
      ctx.lineTo(lx - nx * rayo.w * 2.6, ly - ny * rayo.w * 2.6);
      ctx.lineTo(finX, finY);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.globalAlpha = 0.14;
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  }

  const PICOS = Array.from({ length: 16 }, (_, i) => {
    const azar = Math.abs(Math.sin(i * 12.9898 + 78.233) * 43758.5453) % 1;
    return { azar, giro: (i / 16) * TAU + (azar - 0.5) * 0.6 };
  });

  /* núcleo estelar: destello volumétrico con púas, como el centro del video */
  function dibujarNucleo(now, cx, cy, R, estado) {
    const fuerza = estado === "speaking" ? 1.2
      : estado === "executing" ? 1.12
        : estado === "thinking" ? 1.06
          : estado === "error" ? 1.35
            : 1;
    const respira = 0.94 + 0.06 * Math.sin(now * 0.0021);
    /* la fuente de luz no está en el centro geométrico: eso rompe la simetría */
    const lx = cx - R * 0.045;
    const ly = cy - R * 0.035;

    const halo = ctx.createRadialGradient(lx, ly, 0, lx, ly, R * 0.95);
    halo.addColorStop(0, "rgba(255,255,255,0.34)");
    halo.addColorStop(0.16, "rgba(255,255,255,0.18)");
    halo.addColorStop(0.42, rgba(0.075 * fuerza));
    halo.addColorStop(1, rgba(0));
    ctx.fillStyle = halo;
    ctx.fillRect(cx - R, cy - R, R * 2, R * 2);

    /* púas largas: una diagonal dominante y varias secundarias */
    for (let k = 0; k < PICOS.length; k++) {
      const pico = PICOS[k];
      const a = pico.giro + now * 0.00011 + Math.sin(now * 0.0007 + k * 2.1) * 0.09;
      const largo = R * fuerza * respira * (k < 3 ? 1.15 + pico.azar * 0.6 : 0.2 + pico.azar * 0.7);
      const ancho = (k < 3 ? 2.2 : 0.9) + pico.azar * 2.4;
      const finX = lx + Math.cos(a) * largo;
      const finY = ly + Math.sin(a) * largo;
      const nx = -Math.sin(a);
      const ny = Math.cos(a);
      const grad = ctx.createLinearGradient(lx, ly, finX, finY);
      grad.addColorStop(0, "rgba(255,255,255,0.95)");
      grad.addColorStop(0.28, "rgba(255,255,255,0.5)");
      grad.addColorStop(1, rgba(0));
      ctx.beginPath();
      ctx.moveTo(lx + nx * ancho, ly + ny * ancho);
      ctx.lineTo(lx - nx * ancho, ly - ny * ancho);
      ctx.lineTo(finX, finY);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
    }

    const nucleo = ctx.createRadialGradient(lx, ly, 0, lx, ly, R * 0.55);
    nucleo.addColorStop(0, "rgba(255,255,255,0.96)");
    nucleo.addColorStop(0.1, "rgba(255,255,255,0.82)");
    nucleo.addColorStop(0.32, "rgba(255,255,255,0.4)");
    nucleo.addColorStop(0.65, rgba(0.1));
    nucleo.addColorStop(1, rgba(0));
    ctx.fillStyle = nucleo;
    ctx.fillRect(lx - R * 0.57, ly - R * 0.57, R * 1.14, R * 1.14);

    const chispa = ctx.createRadialGradient(lx, ly, 0, lx, ly, R * 0.15);
    chispa.addColorStop(0, "rgba(255,255,255,1)");
    chispa.addColorStop(0.35, "rgba(255,255,255,0.8)");
    chispa.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = chispa;
    ctx.fillRect(lx - R * 0.16, ly - R * 0.16, R * 0.32, R * 0.32);
  }

  function dibujar(now) {
    const t0 = performance.now();
    const estado = document.body.dataset.state || "idle";
    mezclar(color, COLORES[estado] || COLORES.idle, 0.08);
    const blanco = estado === "error" ? 0.3 : estado === "alert" ? 0.45 : 0.7;
    colorHebra[0] = color[0] + (255 - color[0]) * blanco;
    colorHebra[1] = color[1] + (255 - color[1]) * blanco;
    colorHebra[2] = color[2] + (255 - color[2]) * blanco;

    const { cx, cy, R } = geometriaOrbe();
    const esFilamento = ui.estilo === "esfera";
    const pulso = estado === "speaking"
      ? 1 + 0.04 * Math.sin(now * 0.013)
      : estado === "alert"
        ? 1 + 0.03 * Math.sin(now * 0.009)
        : 1 + 0.012 * Math.sin(now * 0.0016);

    ctx.clearRect(0, 0, W, H);

    const halo = ctx.createRadialGradient(cx, cy, R * 0.05, cx, cy, R * 2.8);
    halo.addColorStop(0, rgba(esFilamento ? 0.14 : 0.11));
    halo.addColorStop(0.4, rgba(esFilamento ? 0.05 : 0.035));
    halo.addColorStop(1, rgba(0));
    ctx.fillStyle = halo;
    ctx.fillRect(cx - R * 2.8, cy - R * 2.8, R * 5.6, R * 5.6);

    const vel = estado === "thinking" ? 0.0007
      : estado === "listening" ? 0.00036
        : estado === "executing" ? 0.0005
          : estado === "downloading" ? 0.00042
            : 0.00022;
    const ry = now * vel;
    const rx = Math.sin(now * 0.00007) * 0.35 + (ui.estilo === "anillo" ? 0.35 : 0.12);
    const cosY = Math.cos(ry), sinY = Math.sin(ry);
    const cosX = Math.cos(rx), sinX = Math.sin(rx);
    const proyectados = new Array(puntos.length);
    const jitter = estado === "error" ? 2.5 : 0;

    ctx.globalCompositeOperation = "lighter";

    /* los puntos y la malla se agrupan en cubos de profundidad y se pintan de una vez:
       mismo ovillo, muchas menos llamadas de dibujo en una PC de 2 núcleos */
    const cubosPuntos = esFilamento
      ? [new Path2D(), new Path2D(), new Path2D(), new Path2D()]
      : null;
    const cuboBrillo = esFilamento ? new Path2D() : null;
    const cuboHalo = esFilamento ? new Path2D() : null;

    for (let i = 0; i < puntos.length; i++) {
      const p = puntos[i];
      p.bx += (p.tx - p.bx) * 0.055;
      p.by += (p.ty - p.by) * 0.055;
      p.bz += (p.tz - p.bz) * 0.055;
      p.imp *= 0.93;

      const x1 = p.bx * cosY - p.bz * sinY;
      const z1 = p.bx * sinY + p.bz * cosY;
      const y2 = p.by * cosX - z1 * sinX;
      const z2 = p.by * sinX + z1 * cosX;
      const temblor = estado === "thinking" ? 0.02 * Math.sin(now * 0.005 + p.ph) : 0;
      const radio = 1 + 0.03 * Math.sin(now * 0.0011 + p.ph * 2 + p.by * 3) + temblor;
      const impulso = p.imp * R * 0.32;
      const nx = x1 * R * radio * pulso;
      const ny = y2 * R * radio * pulso;
      const largo = Math.hypot(nx, ny) || 1;
      const jx = jitter ? (Math.random() - 0.5) * jitter : 0;
      const jy = jitter ? (Math.random() - 0.5) * jitter : 0;
      const px = cx + nx + (nx / largo) * impulso + jx;
      const py = cy + ny + (ny / largo) * impulso + jy;
      const prof = (z2 + 1) / 2;
      proyectados[i] = [px, py, prof];

      const alpha = esFilamento
        ? 0.05 + prof * prof * 0.78 + (i % 7 === 0 ? 0.2 : 0)
        : 0.12 + prof * 0.62;
      const tam = esFilamento
        ? p.s * (0.3 + prof * 0.75) + (i % 7 === 0 ? 0.25 : 0)
        : p.s * (0.5 + prof * 1.25);
      if (esFilamento) {
        const cubo = cubosPuntos[Math.max(0, Math.min(3, Math.floor(prof * 4)))];
        cubo.moveTo(px + tam, py);
        cubo.arc(px, py, tam, 0, TAU);
        if (i % 7 === 0) {
          cuboBrillo.moveTo(px + tam * 1.5, py);
          cuboBrillo.arc(px, py, tam * 1.5, 0, TAU);
        }
        if (prof > 0.88) {
          cuboHalo.moveTo(px + tam * 3.2, py);
          cuboHalo.arc(px, py, tam * 3.2, 0, TAU);
        }
      } else {
        ctx.beginPath();
        ctx.arc(px, py, tam, 0, TAU);
        ctx.fillStyle = rgba(alpha);
        ctx.fill();

        if (prof > 0.88) {
          ctx.beginPath();
          ctx.arc(px, py, tam * 2.7, 0, TAU);
          ctx.fillStyle = rgba(0.04);
          ctx.fill();
        }
      }
    }

    if (esFilamento) {
      for (let cb = 0; cb < 4; cb++) {
        const pb = (cb + 0.5) / 4;
        ctx.fillStyle = rgbaH(0.06 + pb * pb * 0.85);
        ctx.fill(cubosPuntos[cb]);
      }
      ctx.fillStyle = rgbaH(0.85);
      ctx.fill(cuboBrillo);
      ctx.fillStyle = rgbaH(0.03);
      ctx.fill(cuboHalo);
    }

    /* uniones: la malla de la esfera y del anillo */
    ctx.lineWidth = 0.62;
    const cubosMalla = esFilamento
      ? [new Path2D(), new Path2D(), new Path2D(), new Path2D()]
      : null;
    const cuboNudos = esFilamento ? new Path2D() : null;
    const chispasMalla = esFilamento ? [] : null;
    for (let k = 0; k < pares.length; k++) {
      if (esFilamento && (k % 100) / 100 > calidad) continue;
      const [ia, ib, curva, azar] = pares[k];
      const a = proyectados[ia];
      const b = proyectados[ib];
      if (!a || !b) continue;
      const prof = (a[2] + b[2]) * 0.5;
      if (esFilamento) {
        /* hilos curvos que se hunden hacia el centro: ovillo, no esfera de puntos */
        const dx = b[0] - a[0];
        const dy = b[1] - a[1];
        const len = Math.hypot(dx, dy) || 1;
        const nx = -dy / len;
        const ny = dx / len;
        const off = (curva || 0) * len * (0.08 + 0.3 * (azar || 0.5));
        const mx = (a[0] + b[0]) * 0.5;
        const my = (a[1] + b[1]) * 0.5;
        const ctrlX = mx + nx * off - (mx - cx) * 0.14;
        const ctrlY = my + ny * off - (my - cy) * 0.14;
        const cubo = cubosMalla[Math.max(0, Math.min(3, Math.floor(prof * 4)))];
        cubo.moveTo(a[0], a[1]);
        cubo.quadraticCurveTo(ctrlX, ctrlY, b[0], b[1]);
        if (k % 29 === 0) {
          const tam = 0.5 + prof * 0.9;
          cuboNudos.moveTo(mx + tam, my);
          cuboNudos.arc(mx, my, tam, 0, TAU);
        }
        if (k % 43 === 0) {
          const t = ((now * 0.0006 + k * 0.13) % 1);
          chispasMalla.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 0.5 * (1 - Math.abs(0.5 - t) * 2)]);
        }
      } else {
        const alpha = (ui.estilo === "cinta" ? 0.06 : 0.03) + prof * (ui.estilo === "cinta" ? 0.12 : 0.08);
        if (alpha < 0.02) continue;
        ctx.beginPath();
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(b[0], b[1]);
        ctx.strokeStyle = rgba(alpha);
        ctx.stroke();
        if (k % 19 === 0) {
          const mx = (a[0] + b[0]) * 0.5;
          const my = (a[1] + b[1]) * 0.5;
          ctx.beginPath();
          ctx.arc(mx, my, 0.9 + prof * 1.1, 0, TAU);
          ctx.fillStyle = rgba(0.2 + prof * 0.25);
          ctx.fill();
        }
        if (k % 31 === 0) {
          const t = ((now * 0.0006 + k * 0.13) % 1);
          const px = a[0] + (b[0] - a[0]) * t;
          const py = a[1] + (b[1] - a[1]) * t;
          ctx.beginPath();
          ctx.arc(px, py, 1.2, 0, TAU);
          ctx.fillStyle = rgba(0.5 * (1 - Math.abs(0.5 - t) * 2));
          ctx.fill();
        }
      }
    }

    if (esFilamento) {
      for (let cb = 0; cb < 4; cb++) {
        const pb = (cb + 0.5) / 4;
        ctx.strokeStyle = rgbaH(0.016 + pb * pb * 0.34);
        ctx.lineWidth = 0.4 + pb * 0.9;
        ctx.stroke(cubosMalla[cb]);
      }
      ctx.fillStyle = rgbaH(0.55);
      ctx.fill(cuboNudos);
      for (let i = 0; i < chispasMalla.length; i++) {
        const ch = chispasMalla[i];
        ctx.beginPath();
        ctx.arc(ch[0], ch[1], 1.2, 0, TAU);
        ctx.fillStyle = rgbaH(ch[2]);
        ctx.fill();
      }
    }

    if (esFilamento) {
      dibujarHebras(now, cx, cy, R, cosY, sinY, cosX, sinX, estado);
      dibujarMotas(now, cx, cy, R, cosY, sinY, cosX, sinX);
      const bruma = ctx.createRadialGradient(cx, cy, R * 0.12, cx, cy, R * 1.28);
      bruma.addColorStop(0, "rgba(255,255,255,0.05)");
      bruma.addColorStop(0.62, "rgba(255,255,255,0.026)");
      bruma.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = bruma;
      ctx.fillRect(cx - R * 1.3, cy - R * 1.3, R * 2.6, R * 2.6);
    } else {
      dibujarArcos(now, cx, cy, R, estado);
      dibujarPlasma(now, cx, cy, R, estado);
    }
    dibujarToro(now, cx, cy, R, estado);

    /* núcleo */
    if (esFilamento) {
      dibujarNucleo(now, cx, cy, R, estado);
      dibujarFogonazo(now, cx, cy, R, estado);
    } else {
      const nucleo = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.52);
      nucleo.addColorStop(0, "rgba(255,255,255,0.95)");
      nucleo.addColorStop(0.06, rgba(0.8));
      nucleo.addColorStop(0.2, rgba(0.15));
      nucleo.addColorStop(1, rgba(0));
      ctx.fillStyle = nucleo;
      ctx.fillRect(cx - R * 0.55, cy - R * 0.55, R * 1.1, R * 1.1);
      dibujarEstrella(now, cx, cy, R, estado);
    }

    /* estados sobre el orbe */
    if (estado === "speaking") {
      ctx.beginPath();
      for (let i = 0; i <= 90; i++) {
        const a = (i / 90) * TAU;
        const onda = 1 + 0.045 * Math.sin(a * 7 + now * 0.012);
        const rr = R * 1.06 * onda;
        const px = cx + Math.cos(a) * rr;
        const py = cy + Math.sin(a) * rr;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.strokeStyle = rgba(0.26);
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    if (estado === "thinking") {
      for (let k = 0; k < 2; k++) {
        const inicio = now * 0.002 + k * Math.PI;
        ctx.beginPath();
        ctx.arc(cx, cy, R * 1.16, inicio, inicio + 0.9);
        ctx.strokeStyle = rgba(0.4);
        ctx.lineWidth = 1.6;
        ctx.stroke();
      }
    }
    if (estado === "listening") {
      const fase = (now % 1600) / 1600;
      for (let k = 0; k < 2; k++) {
        const f = (fase + k * 0.5) % 1;
        ctx.beginPath();
        ctx.arc(cx, cy, R * (1.08 + f * 0.7), 0, TAU);
        ctx.strokeStyle = rgba(0.24 * (1 - f));
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }
    }
    if (estado === "executing") {
      const inicio = now * 0.0018;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.14, inicio, inicio + 0.55);
      ctx.strokeStyle = rgba(0.62);
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.14, inicio + Math.PI, inicio + Math.PI + 0.3);
      ctx.strokeStyle = rgba(0.3);
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    if (estado === "downloading") {
      const pct = ui.descargaPct == null ? (now % 2200) / 2200 : ui.descargaPct / 100;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.2, -Math.PI / 2, -Math.PI / 2 + pct * TAU);
      ctx.strokeStyle = rgba(0.55);
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    if (estado === "alert") {
      const f = (now % 900) / 900;
      ctx.beginPath();
      ctx.arc(cx, cy, R * (1.15 + f * 0.5), 0, TAU);
      ctx.strokeStyle = rgba(0.28 * (1 - f));
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    /* ráfaga de ejecución, como el portal del video */
    if (burst) {
      const f = (now - burst.t0) / 1250;
      if (f >= 1) {
        burst = null;
      } else {
        const ease = 1 - Math.pow(1 - f, 3);
        for (let k = 0; k < 2; k++) {
          const ff = Math.max(0, ease - k * 0.12);
          if (ff <= 0) continue;
          ctx.beginPath();
          ctx.arc(cx, cy, R * (0.9 + ff * 1.55), 0, TAU);
          ctx.strokeStyle = rgba((1 - f) * (k === 0 ? 0.42 : 0.18));
          ctx.lineWidth = k === 0 ? 1.8 : 1;
          ctx.stroke();
        }
        for (let k = 0; k < 22; k++) {
          const a = (k / 22) * TAU + now * 0.0004;
          const r1 = R * (0.95 + ease * 0.6);
          const r2 = r1 + R * 0.08 * (1 - f);
          ctx.beginPath();
          ctx.moveTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
          ctx.lineTo(cx + Math.cos(a) * r2, cy + Math.sin(a) * r2);
          ctx.strokeStyle = rgba((1 - f) * 0.38);
          ctx.lineWidth = 1;
          ctx.stroke();
        }
        const flash = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * (1.1 + ease));
        flash.addColorStop(0, rgba(0.1 * (1 - f)));
        flash.addColorStop(1, rgba(0));
        ctx.fillStyle = flash;
        ctx.fillRect(cx - R * 2.2, cy - R * 2.2, R * 4.4, R * 4.4);
      }
    }

    const brillo = estado === "speaking" ? 0.55 + 0.2 * Math.sin(now * 0.012) : 0.45;
    ctx.beginPath();
    ctx.arc(cx, cy, R * (0.05 + brillo * 0.02), 0, TAU);
    ctx.fillStyle = `rgba(255,255,255,${0.7 + 0.2 * Math.sin(now * 0.002)})`;
    ctx.fill();

    ctx.globalCompositeOperation = "source-over";

    /* calidad adaptativa: en una PC de 2 núcleos el ovillo cede densidad antes que FPS */
    const costo = performance.now() - t0;
    costoMedio += (costo - costoMedio) * 0.05;
    if (costoMedio > 27 && calidad > 0.6) calidad = 0.7;
    else if (costoMedio < 16 && calidad < 1) calidad = 1;
  }

  function bucle(now) {
    requestAnimationFrame(bucle);
    if (!visible) return;
    const fps = reducido ? 12 : 30;
    if (now - ultimoFrame < 1000 / fps) return;
    ultimoFrame = now;
    dibujar(now);
  }

  document.addEventListener("visibilitychange", () => {
    visible = !document.hidden;
    if (visible) ultimoFrame = 0;
  });

  window.addEventListener("resize", redimensionar);
  redimensionar();
  requestAnimationFrame(bucle);
})();
