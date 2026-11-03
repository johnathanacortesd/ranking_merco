import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import csv
import html
import json
import os
import re
import unicodedata
from io import StringIO

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Generador de Informes Merco",
    page_icon="📊",
    layout="wide"
)

# --- Estilos de la interfaz (tema claro moderno) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.stApp { background-color: #FFFFFF; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 920px; padding-top: 2rem; padding-bottom: 3rem; }
/* Todo el contenido se puede seleccionar y copiar; tarjetas, chips y tablas
   no tienen fondo para que al pegarlos (Word, correo, PowerPoint) salgan
   transparentes. */
.stApp, .stApp * { -webkit-user-select: text; user-select: text; }
.app-header { background: transparent; border: 1px solid #EAE0D2; border-radius: 18px; padding: 28px 32px; margin-bottom: 24px; }
.app-header h1 { font-size: 29px; font-weight: 800; color: #221C15; margin: 0 0 6px 0; letter-spacing: -0.02em; }
.app-header p { font-size: 16px; color: #6E6257; margin: 0; line-height: 1.55; }
.result-card { background: transparent; border: 1px solid #E9E1D4; border-left: 5px solid #C4562C; border-radius: 14px; padding: 18px 22px; margin: 12px 0 16px 0; font-size: 16.5px; line-height: 1.6; color: #26221D; }
.result-card .chip { display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; color: #B34A24; background: transparent; padding: 0; margin-bottom: 6px; }
table.tabla-merco { border-collapse: collapse; width: 100%; background: transparent; margin: 6px 0 18px 0; font-size: 15.5px; color: #26221D; }
table.tabla-merco th, table.tabla-merco td { background: transparent; border: 1px solid #D9CFC0; padding: 7px 12px; text-align: left; }
table.tabla-merco th { font-weight: 700; }
table.tabla-merco td.num, table.tabla-merco th.num { text-align: center; width: 90px; }
table.tabla-merco tr.destacada td { font-weight: 700; }
.titulo-tabla { font-weight: 700; font-size: 16.5px; margin: 14px 0 2px 0; color: #221C15; }
.nota-tabla { font-size: 14px; color: #6E6257; margin: 0 0 6px 0; }
div[data-testid="stTextInput"] input { border-radius: 12px; border: 1.5px solid #DCD1BF; background: #FFFFFF; padding: 12px 16px; font-size: 17px; color: #26221D !important; caret-color: #B34A24; -webkit-text-fill-color: #26221D; }
div[data-testid="stTextInput"] input::placeholder { color: #A2937F !important; opacity: 1; -webkit-text-fill-color: #A2937F; }
div[data-testid="stTextInput"] label p { color: #3A342C !important; font-weight: 600; font-size: 16px; }
div[data-testid="stTextInput"] input:focus { border-color: #C4562C; box-shadow: 0 0 0 3px rgba(196, 86, 44, 0.15); }
div[data-testid="stCodeBlock"] { border-radius: 12px; border: 1px solid #E9E1D4; }
p, li { font-size: 16px; line-height: 1.65; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIÓN DE NORMALIZACIÓN ---
def normalize_text(text):
    """Limpia y estandariza el texto para hacer comparaciones robustas."""
    if not isinstance(text, str):
        return ""
    
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.lower()
    
    words_to_remove = [
        r'\bgrupo\b', r'\bcomercializadora\b', r'\borganizacion\b', r'\bs\.a\.s\b', 
        r'\bsas\b', r'\bs\.a\b', r'\bltda\b', r'\bcompany\b', r'\binternational\b', 
        r'\bessity\b', r'\(.*?\)'
    ]
    for word_regex in words_to_remove:
        text = re.sub(word_regex, '', text, flags=re.IGNORECASE)
    
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return ' '.join(text.split()).strip()

# --- Funciones de Carga y Parseo ---
_PARTICULAS_NOMBRE = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "a"}
# Siglas que se conservan en mayúscula (no son palabras: EIA, WWF, EPM...).
_SIGLAS_NOMBRE = {"eia": "EIA", "eafit": "EAFIT", "wwf": "WWF", "epm": "EPM",
                  "isa": "ISA", "s.a": "S.A", "s.a.s": "S.A.S"}

def formato_empresa(nombre):
    """Formato de exhibición de los nombres de empresa (regla del usuario):
    solo la primera letra de la primera palabra en mayúscula y el resto en
    minúscula, PERO van en formato capital: la palabra que sigue a "de"/"del",
    la última palabra del nombre y los segmentos "Santa/Santo + nombre".
    Las universidades van en formato capital completo (cada palabra
    significativa con mayúscula inicial y las partículas en minúscula).
    Las siglas conocidas se conservan en mayúscula."""
    s = " ".join(str(nombre).split())
    if not s:
        return s
    if "universidad" in normalize_text(s):
        palabras = s.lower().split()
        out = " ".join(
            w if (i > 0 and w in _PARTICULAS_NOMBRE) else w.capitalize()
            for i, w in enumerate(palabras)
        )
    else:
        palabras = s.lower().split()
        n = len(palabras)
        cap = [False] * n
        cap[0] = True
        cap[n - 1] = True  # la última palabra va en capital
        for i, w in enumerate(palabras):
            if w in ("de", "del"):
                j = i + 1
                if j < n and palabras[j] in ("la", "el", "los", "las"):
                    j += 1  # el artículo queda en minúscula; capital la siguiente
                if j < n:
                    cap[j] = True
            if w in ("santa", "santo"):
                cap[i] = True
                if i + 1 < n:
                    cap[i + 1] = True
        out = " ".join(w.capitalize() if cap[i] else w for i, w in enumerate(palabras))
    return " ".join(_SIGLAS_NOMBRE.get(w.lower(), w) for w in out.split())

def parse_general_ranking(file_path):
    """Parsea archivos de ranking, con lógica especial para 'Líderes'."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'lideres' in os.path.basename(file_path):
            rows = re.findall(r'<tr>(.*?)</tr>', content, re.DOTALL)
            data_list = []
            for row_html in rows[1:]:
                cells = re.findall(r'<td>(.*?)</td>', row_html, re.DOTALL)
                if len(cells) > 1:
                    pos_match = re.search(r'<span.*?>(.*?)</span>', cells[0])
                    # ### CAMBIO CLAVE: Regex más precisa para líder y empresa ###
                    leader_company_match = re.search(r'([^<]*)<em>(.*?)</em>', cells[1])
                    
                    if pos_match and leader_company_match:
                        pos = pos_match.group(1).strip()
                        leader = leader_company_match.group(1).strip()
                        company = leader_company_match.group(2).strip()
                        data_list.append({'posicion': pos, 'lider_nombre': leader, 'empresa': company})
            
            if not data_list: return None
            df = pd.DataFrame(data_list)
        else:
            df_list = pd.read_html(StringIO(content))
            if not df_list: return None
            df = df_list[0]

        df.columns = [normalize_text(str(col)) for col in df.columns]
        
        if 'empresa' in df.columns:
            df['empresa_normalized'] = df['empresa'].apply(normalize_text)
        
        if 'posicion' in df.columns:
            df['posicion'] = pd.to_numeric(df['posicion'], errors='coerce')

        return df
    except (FileNotFoundError, IndexError, ValueError):
        st.error(f"Error procesando el archivo: {file_path}. Verifique el formato.")
        return None

@st.cache_data
def parse_sector_ranking(file_path):
    """Parsea el archivo de ranking por sectores y normaliza columnas."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sector_tables = re.findall(r'<h3.*?>(.*?)</h3>.*?<table(.*?)</table>', content, re.DOTALL)
        sector_data = {}
        for sector_name, table_html in sector_tables:
            sector_name = sector_name.strip()
            full_table_html = f"<table{table_html}>"
            df_list = pd.read_html(StringIO(full_table_html))
            if df_list:
                df = df_list[0]
                df.columns = [normalize_text(str(col)) for col in df.columns]
                
                if 'empresa' in df.columns:
                    df['empresa_normalized'] = df['empresa'].apply(normalize_text)
                if 'posicion' in df.columns:
                    df['posicion'] = pd.to_numeric(df['posicion'], errors='coerce')
                sector_data[sector_name] = df
        
        return sector_data
    except FileNotFoundError:
        st.error(f"No se encontró el archivo: {file_path}.")
        return {}

# --- Funciones de Búsqueda ---
def find_company_in_df_robust(df, normalized_query):
    if df is None or 'empresa_normalized' not in df.columns or not normalized_query: return None, None, None
    match = df[df['empresa_normalized'] == normalized_query]
    if match.empty:
        match = df[df['empresa_normalized'].str.contains(normalized_query, na=False)]
    if not match.empty:
        row = match.iloc[0]
        pos = row.get('posicion')
        original_name = row.get('empresa')
        leader_name = row.get('lidernombre')
        return (int(pos) if pd.notna(pos) else None), original_name, leader_name
    return None, None, None

def find_company_in_sectors_robust(sector_data, normalized_query):
    if not sector_data: return None, None, None
    for sector, df in sector_data.items():
        if df is None or 'empresa_normalized' not in df.columns: continue
        match = df[df['empresa_normalized'] == normalized_query]
        if match.empty:
            match = df[df['empresa_normalized'].str.contains(normalized_query, na=False)]
        if not match.empty:
            pos = match.iloc[0].get('posicion')
            original_name = match.iloc[0].get('empresa')
            return sector, (int(pos) if pd.notna(pos) else None), original_name
    return None, None, None

# --- Interfaz de Usuario y Lógica Principal ---
st.markdown("""
<div class="app-header">
  <h1>📊 Generador de Informes de Reputación · Merco</h1>
  <p>Consulta la posición de una empresa en los rankings Merco Empresas, Talento, Líderes y Sectores de 2024, 2025 y 2026, y genera el texto comparativo listo para tu informe.</p>
  <p style="font-size:13px; opacity:0.85; margin-top:6px;">Creado por Johnathan Cortés</p>
</div>
""", unsafe_allow_html=True)

INTRO_TEXT = """
En el ámbito empresarial contemporáneo, la medición de la reputación es una piedra angular para garantizar el éxito sostenible de cualquier empresa. En GlobalNews Group, somos conscientes de la inestimable naturaleza de la reputación empresarial y, como resultado, proporcionamos una mirada detallada al análisis reputacional.

Nuestro informe de reputación trasciende la mera recolección de datos, ofreciendo un valor agregado de alta relevancia. Para este mes, hemos integrado el posicionamiento en el ranking Merco en nuestro análisis. Esta herramienta exhaustiva evalúa la reputación de las empresas en Colombia a través de una metodología multistakeholder que engloba seis evaluaciones y más de veinte fuentes de información. La posición obtenida en este ranking refleja directamente el reconocimiento que la empresa ha logrado entre una amplia gama de grupos de interés. Es importante destacar que la metodología utilizada por Merco Empresas es completamente pública y accesible en su sitio web.
"""
OUTRO_TEXT = """
---
¿Está listo para elevar su estrategia de gestión de la reputación al próximo nivel? Esto es solo el principio, ya que en GlobalNews Group ofrecemos una variedad de herramientas avanzadas para fortalecer su capacidad de monitoreo de noticias, ya sea en medios tradicionales o en plataformas de redes sociales. ¡Descubra cómo podemos ayudarle a medir, gestionar y mejorar su reputación empresarial de manera efectiva y precisa!
"""
# --- Clientes (lista del usuario en data/clientes_merco.csv) ---
# Cada fila: cliente, sector_merco. El sector es el de Merco Sectores 2026 que
# se muestra cuando la marca no figura en ese ranking. El selector conserva
# el orden exacto del archivo (sin reordenar).
CLIENTES_FRECUENTES = []
CLIENTE_SECTORES = {}
_clientes_path = os.path.join("data", "clientes_merco.csv")
if os.path.exists(_clientes_path):
    with open(_clientes_path, encoding="utf-8-sig", newline="") as _f:
        for _row in csv.DictReader(_f):
            _cli = (_row.get("cliente") or "").strip()
            if not _cli:
                continue
            CLIENTES_FRECUENTES.append(_cli)
            _sec = (_row.get("sector_merco") or "").strip()
            if _sec:
                CLIENTE_SECTORES[_cli] = _sec
# Lookup por nombre normalizado: el mapa manda sin importar mayúsculas/tildes.
_CLIENTE_SECTORES_NORM = {}
for _k, _v in CLIENTE_SECTORES.items():
    _CLIENTE_SECTORES_NORM.setdefault(normalize_text(_k), _v)

# Buscador manual y lista de clientes frecuentes: manda el control que el
# usuario tocó de último (sin tener que borrar el otro). Los on_change
# registran la fuente más reciente en la sesión.
def _fuente_manual():
    st.session_state["ultima_fuente"] = "manual"

def _fuente_lista():
    st.session_state["ultima_fuente"] = "lista"

company_name_input = st.text_input(
    "Introduce el nombre de la empresa a consultar:",
    placeholder="Ej: EPM, Nutresa, Crepes & Waffles",
    key="busqueda_manual", on_change=_fuente_manual,
).strip()

cliente_elegido = ""
if CLIENTES_FRECUENTES:
    cliente_elegido = st.selectbox(
        "…o elige uno de los clientes frecuentes:", [""] + [formato_empresa(c) for c in CLIENTES_FRECUENTES],
        key="cliente_lista", on_change=_fuente_lista,
    )

if st.session_state.get("ultima_fuente") == "lista" and cliente_elegido:
    company_name_input = cliente_elegido
elif not company_name_input and cliente_elegido:
    company_name_input = cliente_elegido

if company_name_input:
    normalized_input = normalize_text(company_name_input)
    # Las variantes ", Competencia(s)" de la lista buscan por el nombre base
    _base_input = re.sub(r',\s*competencias?$', '', company_name_input, flags=re.IGNORECASE).strip()
    if _base_input != company_name_input:
        normalized_input = normalize_text(_base_input)
    # Alias: nombres de cliente que en Merco figuran con otro nombre
    ALIAS_MERCO = {
        "fundacion cardio infantil": "LACARDIO",
        "fundacion cardioinfantil": "LACARDIO",
        "la cardio": "LACARDIO",
        "unal": "UNIVERSIDAD NACIONAL DE COLOMBIA",
        "holcim colombia": "HOLCIM",
    }
    if normalized_input in ALIAS_MERCO:
        normalized_input = normalize_text(ALIAS_MERCO[normalized_input])

    # Vocero ACTUAL de cada cliente para el ranking Líderes (lo define el
    # usuario). El párrafo de Líderes sigue al vocero, pero los puestos de
    # años anteriores se atribuyen SIEMPRE a la persona que los obtuvo
    # según la data: un puesto histórico jamás se traslada a otra persona.
    VOCEROS_LIDERES = {
        "universidad nacional de colombia": "JOSÉ ISMAEL PEÑA REYES",
        "tigo": "CARLOS BLANCO",
        "universidad eia": "JUAN MANUEL RESTREPO CADAVID",
        "deloitte": "FRANCISCO O'BONAGA",
    }

    cliente_actual = None
    for _c in CLIENTES_FRECUENTES:
        _c_base = re.sub(r',\s*competencias?$', '', _c, flags=re.IGNORECASE).strip()
        if normalize_text(_c) == normalized_input or normalize_text(_c_base) == normalized_input:
            cliente_actual = _c
            break
    DATA_DIR = "data"
    try:
        files = {f.replace('.txt', '').replace(' ', '_'): os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith('.txt')}
    except FileNotFoundError:
        st.error(f"No se encontró la carpeta '{DATA_DIR}'.")
        st.stop()

    st.markdown("---")
    st.subheader(f"Análisis Reputacional para: **{company_name_input}**")
    st.markdown(INTRO_TEXT)
    
    found_any = False
    nombre_empresa = None

    # Cada bloque del informe guarda su versión en texto plano (para pegar
    # sin formato) y en HTML sin fondo (para pegar con negritas y tablas).
    informe_bloques = []

    def _md_a_html(texto_md):
        t = html.escape(texto_md, quote=False)
        t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
        return re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)

    def _md_a_plano(texto_md):
        return texto_md.replace("**", "").replace("*", "")

    def agregar_al_informe(texto_md):
        informe_bloques.append((_md_a_plano(texto_md), f"<p>{_md_a_html(texto_md)}</p>"))

    def mostrar_tarjeta(etiqueta, texto_md):
        """Muestra el resultado en una tarjeta (sin fondo) y lo acumula para el informe."""
        agregar_al_informe(texto_md)
        st.markdown(f'<div class="result-card"><span class="chip">{etiqueta}</span><br>{_md_a_html(texto_md)}</div>',
                    unsafe_allow_html=True)

    # Estilos en línea: al copiar y pegar la tabla conserva bordes y negritas,
    # pero sin color de fondo.
    _TD = "border:1px solid #D9CFC0; padding:6px 12px; background:transparent; text-align:left;"
    _TD_NUM = "border:1px solid #D9CFC0; padding:6px 12px; background:transparent; text-align:center;"

    def tabla_html(columnas, filas, destacar=None):
        """Tabla HTML transparente; `destacar` es el índice de una fila a resaltar."""
        cab = "".join(
            f'<th class="{"num" if i == 0 else ""}" style="{_TD_NUM if i == 0 else _TD} font-weight:700;">{html.escape(str(c))}</th>'
            for i, c in enumerate(columnas))
        cuerpo = []
        for r, fila in enumerate(filas):
            peso = " font-weight:700;" if r == destacar else ""
            celdas = "".join(
                f'<td class="{"num" if i == 0 else ""}" style="{_TD_NUM if i == 0 else _TD}{peso}">{html.escape(str(v))}</td>'
                for i, v in enumerate(fila))
            cuerpo.append(f'<tr class="{"destacada" if r == destacar else ""}">{celdas}</tr>')
        return ('<table class="tabla-merco" style="border-collapse:collapse; background:transparent;">'
                f'<thead><tr>{cab}</tr></thead><tbody>{"".join(cuerpo)}</tbody></table>')

    def mostrar_tabla(titulo, columnas, filas, nota=None, destacar=None):
        """Muestra una tabla copiable y transparente y la agrega al informe."""
        t_html = tabla_html(columnas, filas, destacar)
        nota_html = f'<p class="nota-tabla">{html.escape(nota)}</p>' if nota else ""
        st.markdown(f'<p class="titulo-tabla">{html.escape(titulo)}</p>{nota_html}{t_html}',
                    unsafe_allow_html=True)
        plano = "\n".join(["\t".join(map(str, columnas))] + ["\t".join(map(str, f)) for f in filas])
        informe_bloques.append((f"{titulo}:\n{plano}", f"<p><strong>{html.escape(titulo)}</strong></p>{t_html}"))

    def boton_copiar(texto, texto_html):
        """Botón que copia el informe con formato (HTML sin fondo) y en texto plano."""
        components.html(
            """
            <button id="btnCopiarInforme" style="width:100%; background:#C4562C; color:#FFFFFF; border:none; border-radius:12px; padding:14px 22px; font-family:Inter, system-ui, sans-serif; font-size:17px; font-weight:700; cursor:pointer;">&#128203; Copiar el informe completo</button>
            <script>
            const TEXTO_INFORME = __PAYLOAD__;
            const HTML_INFORME = __PAYLOAD_HTML__;
            const btn = document.getElementById('btnCopiarInforme');
            function copiaRespaldo() {
              const div = document.createElement('div');
              div.contentEditable = 'true';
              div.innerHTML = HTML_INFORME;
              div.style.position = 'fixed'; div.style.left = '-9999px'; div.style.background = 'transparent';
              document.body.appendChild(div);
              const rango = document.createRange(); rango.selectNodeContents(div);
              const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(rango);
              const ok = document.execCommand('copy');
              sel.removeAllRanges(); document.body.removeChild(div);
              return ok;
            }
            btn.addEventListener('click', async () => {
              try {
                await navigator.clipboard.write([new ClipboardItem({
                  'text/html': new Blob([HTML_INFORME], {type: 'text/html'}),
                  'text/plain': new Blob([TEXTO_INFORME], {type: 'text/plain'})
                })]);
              } catch (e) {
                if (!copiaRespaldo()) {
                  try { await navigator.clipboard.writeText(TEXTO_INFORME); } catch (e2) {}
                }
              }
              btn.textContent = '✅ ¡Copiado! Ya puedes pegarlo donde lo necesites';
              setTimeout(() => { btn.innerHTML = '&#128203; Copiar el informe completo'; }, 3000);
            });
            </script>
            """.replace("__PAYLOAD_HTML__", json.dumps(texto_html)).replace("__PAYLOAD__", json.dumps(texto)),
            height=62
        )

    # --- Redacción del informe comparativo 2026 / 2025 / 2024 ---
    # Especificación del usuario: tono neutro y claro; estructura fija por párrafo
    # (ranking y año -> posición actual -> comparación con 2025 -> comparación con
    # 2024); las comparaciones son siempre de 2026 contra cada año anterior, con
    # el puesto de ese año entre paréntesis; verbos subir/bajar/mantenerse.
    def _posiciones_txt(d):
        return f"{d} posición" if d == 1 else f"{d} posiciones"

    def verbo_cambio(p_ref, p_new):
        """Verbo y magnitud del cambio de 2026 contra un año anterior."""
        d = p_ref - p_new
        if d > 0: return f"subió {_posiciones_txt(d)}"
        if d < 0: return f"bajó {_posiciones_txt(-d)}"
        return "se mantuvo en la misma posición"

    def comparacion(anio, p_ref, p_new):
        """Comparación de 2026 contra un año anterior (puesto menor = mejor)."""
        return f"En comparación con {anio} (puesto **{p_ref}**), {verbo_cambio(p_ref, p_new)}."

    def historial(pos):
        """Comparaciones de 2026 contra 2025 y contra 2024, en ese orden.
        Si 2025 y 2024 tienen el mismo puesto, la comparación es una sola
        (mismo cambio frente a ambos años, sin repetir la frase).
        Sin 2026 no hay comparaciones: solo el dato de cada año."""
        p26, p25, p24 = pos[2026], pos[2025], pos[2024]
        if p26:
            if not p25 and not p24:
                return " No figuró en el ranking en 2025 ni en 2024."
            if p25 and p24 and p25 == p24:
                return (f" En comparación con 2025 (puesto **{p25}**) y 2024 (puesto **{p24}**), "
                        f"{verbo_cambio(p25, p26)}.")
            partes = []
            for anio, p in ((2025, p25), (2024, p24)):
                if p: partes.append(comparacion(anio, p, p26))
                else: partes.append(f"En {anio} no figuró en el ranking.")
            return " " + " ".join(partes)
        partes = []
        for anio, p in ((2025, p25), (2024, p24)):
            if p: partes.append(f"En {anio} ocupó el puesto **{p}**.")
            else: partes.append(f"En {anio} no figuró en el ranking.")
        return " " + " ".join(partes)

    def nombre_titulo(nombre):
        """'FRANCISCO JOSÉ BARBERI OSPINA' -> 'Francisco José Barberi Ospina'.
        La letra después de un apóstrofo también va en mayúscula: O'Bonaga."""
        base = " ".join(w.capitalize() for w in str(nombre).lower().split())
        return re.sub(r"'([a-záéíóúñ])", lambda m: "'" + m.group(1).upper(), base)

    RANKINGS_CONFIG = {
        "Merco Empresas": ("merco_empresas_2026", "merco_empresas_2025", "merco_empresas_2024"),
        "Merco Talento": ("merco_talento_2026", "merco_talento_2025", "merco_talento_2024"),
        "Merco Líderes": ("merco_lideres_2026", "merco_lideres_2025", "merco_lideres_2024"),
    }
    YEARS = (2026, 2025, 2024)

    for rank_name, keys in RANKINGS_CONFIG.items():
        datos = {}
        for year, key in zip(YEARS, keys):
            if key not in files: continue
            df = parse_general_ranking(files[key])
            if df is None: continue
            pos, nombre, lider = find_company_in_df_robust(df, normalized_input)
            if pos: datos[year] = (pos, nombre, lider)
        if not datos:
            if rank_name == "Merco Líderes" and normalized_input in VOCEROS_LIDERES:
                # El cliente no tiene registros en Líderes, pero tiene vocero
                # definido: el párrafo sigue al vocero (no figura en ningún año).
                _voc = nombre_titulo(VOCEROS_LIDERES[normalized_input])
                texto = (f"En el ranking **Merco Líderes 2026**, **{_voc}** no figura en el ranking."
                         " En 2025 no figuró en el ranking. En 2024 no figuró en el ranking.")
                mostrar_tarjeta(rank_name.upper(), texto)
                found_any = True
            continue
        found_any = True

        pos = {y: (datos[y][0] if y in datos else None) for y in YEARS}
        nombre = next(datos[y][1] for y in YEARS if y in datos)
        if nombre_empresa is None: nombre_empresa = nombre
        nombre = formato_empresa(nombre)

        if rank_name == "Merco Líderes":
            anio_ref = next(y for y in YEARS if y in datos)
            lider_ref = nombre_titulo(datos[anio_ref][2])
            empresa_ref = datos[anio_ref][1]
            _emp_base = normalize_text(empresa_ref)
            if _emp_base.startswith("ex "):
                _emp_base = _emp_base[3:]
            vocero = VOCEROS_LIDERES.get(_emp_base)
            if vocero:
                vocero_t = nombre_titulo(vocero)

                def _lider_de(anio):
                    return nombre_titulo(datos[anio][2]) if anio in datos else None

                p26_vocero = pos[2026] if (2026 in datos and _lider_de(2026) == vocero_t) else None
                if p26_vocero:
                    texto = (f"En el ranking **Merco Líderes 2026**, **{vocero_t}**, de la empresa "
                             f"**{nombre}**, ocupa la posición **{p26_vocero}**.")
                else:
                    texto = f"En el ranking **Merco Líderes 2026**, **{vocero_t}** no figura en el ranking."
                frases = []
                for anio in (2025, 2024):
                    if anio not in datos:
                        frases.append(f"En {anio} no figuró en el ranking.")
                    elif _lider_de(anio) == vocero_t:
                        if p26_vocero:
                            frases.append(comparacion(anio, pos[anio], p26_vocero))
                        else:
                            frases.append(f"En {anio}, ocupó el puesto **{pos[anio]}**.")
                    else:
                        frases.append(f"En {anio}, *{_lider_de(anio)}* ocupó el puesto **{pos[anio]}**.")
                texto += " " + " ".join(frases)
                mostrar_tarjeta(rank_name.upper(), texto)
                continue
            if normalize_text(empresa_ref).startswith("ex "):
                # La empresa del registro es "EX - ...": no se nombra la ex empresa;
                # el párrafo es sobre la PERSONA (el líder), como dictó el usuario.
                if pos[2026]:
                    texto = (f"En el ranking **Merco Líderes 2026**, **{lider_ref}** "
                             f"ocupa la posición **{pos[2026]}**.") + historial(pos)
                else:
                    texto = f"En el ranking **Merco Líderes 2026**, **{lider_ref}** no figura en el ranking."
                    frases = []
                    for anio in (2025, 2024):
                        if pos[anio]:
                            frases.append(f"En {anio}, ocupó el puesto **{pos[anio]}**.")
                        else:
                            frases.append(f"En {anio} no figuró en el ranking.")
                    texto += " " + " ".join(frases)
                mostrar_tarjeta(rank_name.upper(), texto)
                continue
            if pos[2026]:
                texto = (f"En el ranking **Merco Líderes 2026**, **{lider_ref}**, de la empresa **{nombre}**, "
                         f"ocupa la posición **{pos[2026]}**.") + historial(pos)
            else:
                texto = f"En el ranking **Merco Líderes 2026**, la empresa **{nombre}** no figura en el ranking."
                frases = []
                for anio in (2025, 2024):
                    if pos[anio]:
                        if anio == anio_ref:
                            frases.append(f"En {anio}, su líder **{lider_ref}** ocupó el puesto **{pos[anio]}**.")
                        else:
                            frases.append(f"En {anio} ocupó el puesto **{pos[anio]}**.")
                    else:
                        frases.append(f"En {anio} no figuró en el ranking.")
                texto += " " + " ".join(frases)
        elif pos[2026]:
            texto = (f"En el ranking **{rank_name} 2026**, la empresa **{nombre}** ocupa la posición **{pos[2026]}**."
                     + historial(pos))
        else:
            texto = (f"En el ranking **{rank_name} 2026**, la empresa **{nombre}** no figura en el ranking."
                     + historial(pos))
        mostrar_tarjeta(rank_name.upper(), texto)

    # La marca figura en Merco Sectores 2026: no hace falta la tabla del sector.
    en_sectores_2026 = False
    datos_sec = {}
    if all(f"merco_sectores_{y}" in files for y in YEARS):
        for year in YEARS:
            sectores = parse_sector_ranking(files[f"merco_sectores_{year}"])
            sector, pos, nombre = find_company_in_sectors_robust(sectores, normalized_input)
            if pos: datos_sec[year] = (sector, pos, nombre)
        if datos_sec:
            found_any = True
            pos = {y: (datos_sec[y][1] if y in datos_sec else None) for y in YEARS}
            anio_ref = next(y for y in YEARS if y in datos_sec)
            sector_ref, _, nombre = datos_sec[anio_ref]
            nombre = formato_empresa(nombre)
            if pos[2026]:
                en_sectores_2026 = True
                texto = (f"En el ranking **Merco Sectores 2026**, la empresa **{nombre}** ocupa la posición **{pos[2026]}** "
                         f"dentro del sector **{sector_ref}**.") + historial(pos)
                notas = [f"En {anio} figuró en el sector **{datos_sec[anio][0]}**."
                         for anio in (2025, 2024)
                         if anio in datos_sec and datos_sec[anio][0] != sector_ref]
                if notas: texto += " " + " ".join(notas)
            else:
                texto = (f"En el ranking **Merco Sectores 2026**, la empresa **{nombre}** no figura en el ranking."
                         + historial(pos)
                         + f" En {anio_ref} figuró en el sector **{sector_ref}**.")
            mostrar_tarjeta("MERCO SECTORES", texto)

    # --- Sector probable cuando el cliente no tiene data en el ranking sectorial ---
    SECTORES_POR_PALABRA = [
        ("universidad", "EDUCACIÓN-UNIVERSIDADES"), ("universitaria", "EDUCACIÓN-UNIVERSIDADES"),
        ("clinica", "SALUD"), ("hospital", "SALUD"),
        ("banco", "FINANCIERO"), ("financiera", "FINANCIERO"),
        ("seguros", "ASEGURADORAS"), ("aseguradora", "ASEGURADORAS"),
        ("caja de compensacion", "CAJAS DE COMPENSACIÓN"), ("compensacion familiar", "CAJAS DE COMPENSACIÓN"),
        ("pensiones y cesantias", "FONDOS DE PENSIONES Y CESANTÍAS"), ("fondo de pensiones", "FONDOS DE PENSIONES Y CESANTÍAS"),
        ("constructora", "CONSTRUCCIÓN E INFRAESTRUCTURA"), ("construccion", "CONSTRUCCIÓN E INFRAESTRUCTURA"),
        ("petrolera", "PETROLERAS Y DISTRIBUCIÓN DE HIDROCARBUROS"), ("petroleo", "PETROLERAS Y DISTRIBUCIÓN DE HIDROCARBUROS"),
        ("energia", "ENERGÍA, GAS Y AGUA"), ("electrica", "ENERGÍA, GAS Y AGUA"), ("acueducto", "ENERGÍA, GAS Y AGUA"),
        ("minera", "MINERÍA"), ("mineria", "MINERÍA"),
        ("farmaceutica", "FARMACÉUTICO"), ("laboratorio", "FARMACÉUTICO"),
        ("restaurante", "RESTAURANTES Y CAFÉS"), ("cafe", "RESTAURANTES Y CAFÉS"),
        ("agroindustrial", "AGROINDUSTRIAL"), ("ingenio", "AGROINDUSTRIAL"), ("agropecuaria", "AGROINDUSTRIAL"),
        ("cementera", "CEMENTERAS"), ("cemento", "CEMENTERAS"),
        ("auditoria", "AUDITORÍA Y CONSULTORÍA"), ("consultoria", "AUDITORÍA Y CONSULTORÍA"),
        ("automotriz", "AUTOMOTRIZ"), ("vehiculos", "AUTOMOTRIZ"),
        ("bebidas", "BEBIDAS"), ("cerveceria", "BEBIDAS"),
        ("telecomunicaciones", "TELECOMUNICACIONES"),
        ("aerolinea", "TRANSPORTE DE VIAJEROS"), ("aviacion", "TRANSPORTE DE VIAJEROS"),
        ("supermercado", "GRANDES SUPERFICIES, RETAIL"), ("retail", "GRANDES SUPERFICIES, RETAIL"),
        ("internet", "SERVICIOS INTERNET"),
        ("confeccion", "CONFECCIÓN Y MARROQUINERÍA"), ("textil", "CONFECCIÓN Y MARROQUINERÍA"),
        ("electrodomesticos", "ELECTRODOMÉSTICOS Y EQUIPAMIENTO"),
        ("fundacion", "ASOCIACIONES, CORPORACIONES, FUNDACIONES"), ("asociacion", "ASOCIACIONES, CORPORACIONES, FUNDACIONES"), ("corporacion", "ASOCIACIONES, CORPORACIONES, FUNDACIONES"),
        ("alimentos", "ALIMENTOS"),
        ("entretenimiento", "ENTRETENIMIENTO"),
        ("industrial", "INDUSTRIAL"),
    ]

    def sector_probable(texto):
        if not texto: return None
        t = normalize_text(texto)
        for clave, sector in SECTORES_POR_PALABRA:
            if clave in t: return sector
        return None

    # --- Merco Sectores 2026 del sector de la marca cuando la marca no sale ---
    # Prioridad: 1) sector asignado al cliente en data/clientes_merco.csv;
    # 2) sector en el que la marca figuró en años anteriores; 3) sector
    # inferido por palabras del nombre (universidad, clínica, banco...).
    sector_sugerido = None
    if not en_sectores_2026 and "merco_sectores_2026" in files:
        sectores_2026 = parse_sector_ranking(files["merco_sectores_2026"])
        candidatos = []
        for _clave in (cliente_actual, _base_input, company_name_input):
            if _clave:
                candidatos.append(_CLIENTE_SECTORES_NORM.get(normalize_text(_clave)))
        candidatos += [datos_sec[y][0] for y in YEARS if y in datos_sec]
        candidatos += [sector_probable(nombre_empresa), sector_probable(_base_input)]
        sec_norm = {normalize_text(k): k for k in sectores_2026}
        for cand in candidatos:
            if cand and normalize_text(cand) in sec_norm:
                _sec = sec_norm[normalize_text(cand)]
                sector_sugerido = (_sec, sectores_2026[_sec])
                break

    nombre_marca = formato_empresa(nombre_empresa or _base_input)

    def mostrar_tabla_sector(nota):
        nombre_sector, df_sec = sector_sugerido
        filas = [(int(f.posicion) if pd.notna(f.posicion) else "", formato_empresa(f.empresa))
                 for f in df_sec.itertuples(index=False)]
        mostrar_tabla(f"Merco Sectores 2026 · {nombre_sector}", ["Posición", "Empresa"], filas, nota=nota)

    if not found_any:
        st.warning(f"La empresa '{company_name_input}' no fue encontrada en ninguno de los rankings Merco de 2024, 2025 o 2026.")
        agregar_al_informe(
            f"**{nombre_marca}** no aparece en los rankings Merco Empresas, Talento, Líderes y Sectores "
            "de las ediciones 2024, 2025 y 2026."
            + (f" A continuación se presenta el ranking **Merco Sectores 2026** del sector "
               f"**{sector_sugerido[0]}**, al que pertenece la marca." if sector_sugerido else "")
        )
        if sector_sugerido:
            mostrar_tabla_sector("Empresas que figuran en 2026 en el sector de la marca.")
        if "merco_empresas_2026" in files:
            df_empresas_2026 = parse_general_ranking(files["merco_empresas_2026"])
            if df_empresas_2026 is not None and all(c in df_empresas_2026.columns for c in ['posicion', 'empresa', 'puntuacion']):
                top_10 = df_empresas_2026.head(10)
                filas_top = [(int(f.posicion) if pd.notna(f.posicion) else "", formato_empresa(f.empresa), f.puntuacion)
                             for f in top_10.itertuples(index=False)]
                mostrar_tabla("Top 10 · Merco Empresas 2026", ["Posición", "Empresa", "Puntuación"], filas_top,
                              nota="Referencia del ranking general.")
    elif sector_sugerido:
        # Si hubo data en años anteriores, la tarjeta de Merco Sectores ya
        # dijo que no figura en 2026; si no, se agrega esa tarjeta.
        if not datos_sec:
            mostrar_tarjeta(
                "MERCO SECTORES",
                f"En el ranking **Merco Sectores 2026**, la empresa **{nombre_marca}** no figura en el ranking. "
                f"A continuación se presenta el ranking del sector **{sector_sugerido[0]}**, al que pertenece la marca."
            )
        st.markdown("---")
        st.subheader("🧭 Merco Sectores 2026 del sector de la marca")
        mostrar_tabla_sector("Empresas que figuran en 2026 en el sector de la marca.")

    if informe_bloques:
        intro = INTRO_TEXT.strip()
        outro = OUTRO_TEXT.replace("---", "").strip()
        informe_completo = intro + "\n\n" + "\n\n".join(t for t, _ in informe_bloques) + "\n\n" + outro
        _p = lambda t: "".join(f"<p>{html.escape(x.strip())}</p>" for x in t.split("\n\n") if x.strip())
        informe_html = (
            '<div style="background:transparent; font-family:Arial, sans-serif; font-size:11pt; color:#000000;">'
            + _p(intro) + "".join(h for _, h in informe_bloques) + _p(outro) + "</div>"
        )
        st.markdown("---")
        boton_copiar(informe_completo, informe_html)
        st.subheader("📋 Informe completo para copiar")
        st.caption("El botón copia el informe con negritas y tablas, sin fondo, listo para pegar en Word, correo o PowerPoint. "
                   "El bloque de abajo es la versión en texto plano (cópiala con el ícono de su esquina superior derecha).")
        st.code(informe_completo, language=None, wrap_lines=True)

    st.markdown(OUTRO_TEXT)
else:
    st.info("Por favor, ingrese el nombre de una empresa para comenzar el análisis.")

st.markdown("---")

