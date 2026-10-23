import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
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
.stApp { background-color: #FAF8F6; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 920px; padding-top: 2rem; padding-bottom: 3rem; }
.app-header { background: linear-gradient(135deg, #FFFFFF 0%, #FBF2EA 100%); border: 1px solid #EAE0D2; border-radius: 18px; padding: 28px 32px; margin-bottom: 24px; box-shadow: 0 4px 18px rgba(90, 55, 25, 0.06); }
.app-header h1 { font-size: 29px; font-weight: 800; color: #221C15; margin: 0 0 6px 0; letter-spacing: -0.02em; }
.app-header p { font-size: 16px; color: #6E6257; margin: 0; line-height: 1.55; }
.result-card { background: #FFFFFF; border: 1px solid #E9E1D4; border-left: 5px solid #C4562C; border-radius: 14px; padding: 18px 22px; margin: 12px 0 16px 0; box-shadow: 0 2px 10px rgba(90, 55, 25, 0.05); font-size: 16.5px; line-height: 1.6; color: #26221D; }
.result-card .chip { display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; color: #B34A24; background: #F9E9DF; border-radius: 999px; padding: 3px 11px; margin-bottom: 9px; }
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
# --- Clientes frecuentes (lista del usuario en data/clientes_merco.txt) ---
CLIENTES_FRECUENTES = []
_clientes_path = os.path.join("data", "clientes_merco.txt")
if os.path.exists(_clientes_path):
    with open(_clientes_path, encoding="utf-8") as _f:
        CLIENTES_FRECUENTES = [l.strip() for l in _f if l.strip()]
# El selector conserva el orden exacto del archivo del usuario (sin reordenar).

# Sector de cada cliente frecuente, para mostrar su tabla sectorial aunque
# el cliente no aparezca en los rankings.
CLIENTE_SECTORES = {
    "Alcaldía de Cartagena": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Carnaval de Barranquilla": "ENTRETENIMIENTO",
    "Colpensiones": "FONDOS DE PENSIONES Y CESANTÍAS",
    "Corferias": "ENTRETENIMIENTO",
    "Financiera de Desarrollo Territorial": "FINANCIERO",
    "Universidad de la Salle": "EDUCACIÓN-UNIVERSIDADES",
    "Universidad Pontificia Bolivariana": "EDUCACIÓN-UNIVERSIDADES",
    "Universidad Santo Tomás": "EDUCACIÓN-UNIVERSIDADES",
    "Agencia Nacional de Seguridad Vial": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Banco de Crédito de Perú": "FINANCIERO",
    "Federación Colombiana de Fútbol": "ENTRETENIMIENTO",
    "Instituto Nacional de Cancerología": "SALUD",
    "Seguros Mundial": "ASEGURADORAS",
    "Universidad EIA": "EDUCACIÓN-UNIVERSIDADES",
    "Universidad Nacional Abierta y a Distancia": "EDUCACIÓN-UNIVERSIDADES",
    "Armada Nacional de Colombia": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Deloitte": "AUDITORÍA Y CONSULTORÍA",
    "División Mayor del Fútbol Colombiano": "ENTRETENIMIENTO",
    "Editorial Planeta": "MEDIOS DE COMUNICACIÓN",
    "Gobernación de Sucre": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Organización Internacional para las Migraciones": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Triple A": "ENERGÍA, GAS Y AGUA",
    "Universidad Jorge Tadeo Lozano": "EDUCACIÓN-UNIVERSIDADES",
    "Alcaldía de Barranquilla": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Cusezar": "CONSTRUCCIÓN E INFRAESTRUCTURA",
    "On Vacation": "ENTRETENIMIENTO",
    "Penguin Random House": "MEDIOS DE COMUNICACIÓN",
    "Positiva Compañía de Seguros": "ASEGURADORAS",
    "Procolombia": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Universidad de Antioquia": "EDUCACIÓN-UNIVERSIDADES",
    "Consejo Superior de la Judicatura": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Coosalud": "SALUD",
    "Fundación Cardio Infantil": "SALUD",
    "Genus PLC": "AGROINDUSTRIAL",
    "Nueva EPS": "SALUD",
    "Petrobras": "PETROLERAS Y DISTRIBUCIÓN DE HIDROCARBUROS",
    "Universidad Minuto de Dios": "EDUCACIÓN-UNIVERSIDADES",
    "Yawa": "ENTRETENIMIENTO",
    "Asociación Bancaria y de Entidades Financieras de Colombia": "FINANCIERO",
    "Constructora Jaramillo Mora": "CONSTRUCCIÓN E INFRAESTRUCTURA",
    "Defensoría del Pueblo": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Federación Colombiana de Golf": "ENTRETENIMIENTO",
    "Savia Salud EPS": "SALUD",
    "Tecnoquímicas S.A": "FARMACÉUTICO",
    "Unidad para la Atención y Reparación Integral a las Víctimas": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Unión Europea": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Agrosavia": "AGROINDUSTRIAL",
    "Alcaldía de Santa Marta": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Asociación Colombiana de Agencias de Viajes y Turismo": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Ban100": "FINANCIERO",
    "Federación Colombiana de Municipios": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Sanofi": "FARMACÉUTICO",
    "Secretaría General de la Alcaldía de Bogotá": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "Tigo": "TELECOMUNICACIONES",
    "FUNDACIÓN PARA EL FUTURO DE COLOMBIA": "EDUCACIÓN-UNIVERSIDADES",
    "COTELCO": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "WWF COLOMBIA": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "REGISTRADURÍA NACIONAL DEL ESTADO CIVIL": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "UNIVERSIDAD AUTÓNOMA DE OCCIDENTE": "EDUCACIÓN-UNIVERSIDADES",
    "UNIVERSIDAD DE LA COSTA": "EDUCACIÓN-UNIVERSIDADES",
    "AGENCIA NACIONAL DE CONTRATACIÓN PÚBLICA": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "HOLCIM COLOMBIA": "CEMENTERAS",
    "UNIDAD NACIONAL PARA LA GESTIÓN DE RIESGOS Y DESASTRES": "ASOCIACIONES, CORPORACIONES, FUNDACIONES",
    "COMFENALCO VALLE": "CAJAS DE COMPENSACIÓN",
    "FUNDACIÓN SANTA FE DE BOGOTÁ": "SALUD",
    "NISSAN": "AUTOMOTRIZ",
    "CHANGAN - DEEPAL": "AUTOMOTRIZ",
    "SIEMENS HEALTHINEERS": "SALUD",
    "FEDERACIÓN NACIONAL DE AVICULTORES DE COLOMBIA": "AGROINDUSTRIAL",
    "UNIVERSIDAD SIMÓN BOLÍVAR": "EDUCACIÓN-UNIVERSIDADES",
    "UNIVERSIDAD TECNOLÓGICA DE BOLÍVAR": "EDUCACIÓN-UNIVERSIDADES",
    "DROPI": "COMERCIO ELECTRÓNICO Y DISTRIBUCIÓN",
}
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

    textos_informe = []

    def mostrar_tarjeta(etiqueta, texto_md):
        """Muestra el resultado en una tarjeta y lo acumula para el informe completo."""
        textos_informe.append(texto_md)
        html_txt = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', texto_md)
        html_txt = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_txt)
        st.markdown(f'<div class="result-card"><span class="chip">{etiqueta}</span><br>{html_txt}</div>', unsafe_allow_html=True)

    def boton_copiar(texto):
        """Botón grande y visible que copia el texto al portapapeles."""
        payload = json.dumps(texto)
        components.html(
            """
            <button id="btnCopiarInforme" style="width:100%; background:#C4562C; color:#FFFFFF; border:none; border-radius:12px; padding:14px 22px; font-family:Inter, system-ui, sans-serif; font-size:17px; font-weight:700; cursor:pointer; box-shadow:0 3px 10px rgba(90,55,25,.25);">&#128203; Copiar el informe completo</button>
            <script>
            const TEXTO_INFORME = __PAYLOAD__;
            const btn = document.getElementById('btnCopiarInforme');
            btn.addEventListener('click', async () => {
              try { await navigator.clipboard.writeText(TEXTO_INFORME); }
              catch (e) {
                const ta = document.createElement('textarea');
                ta.value = TEXTO_INFORME;
                ta.style.position = 'fixed'; ta.style.opacity = '0';
                document.body.appendChild(ta); ta.select();
                document.execCommand('copy'); document.body.removeChild(ta);
              }
              btn.textContent = '\u2705 \u00a1Copiado! Ya puedes pegarlo donde lo necesites';
              setTimeout(() => { btn.textContent = '📋 Copiar el informe completo'; }, 3000);
            });
            </script>
            """.replace("__PAYLOAD__", payload),
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
        """'FRANCISCO JOSÉ BARBERI OSPINA' -> 'Francisco José Barberi Ospina'."""
        return " ".join(w.capitalize() for w in str(nombre).lower().split())

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
        if not datos: continue
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

    sector_mostrado = False
    if all(f"merco_sectores_{y}" in files for y in YEARS):
        datos_sec = {}
        for year in YEARS:
            sectores = parse_sector_ranking(files[f"merco_sectores_{year}"])
            sector, pos, nombre = find_company_in_sectors_robust(sectores, normalized_input)
            if pos: datos_sec[year] = (sector, pos, nombre)
        if datos_sec:
            found_any = True
            sector_mostrado = True
            pos = {y: (datos_sec[y][1] if y in datos_sec else None) for y in YEARS}
            anio_ref = next(y for y in YEARS if y in datos_sec)
            sector_ref, _, nombre = datos_sec[anio_ref]
            nombre = formato_empresa(nombre)
            if pos[2026]:
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

    def mostrar_tabla_sector(nombre_sector, df_sec, nota):
        st.markdown(f"**Merco Sectores 2026 · {nombre_sector}**")
        st.caption(nota)
        tabla = df_sec[['posicion', 'empresa']].rename(columns={'posicion': 'Posición', 'empresa': 'Empresa'})
        tabla['Empresa'] = tabla['Empresa'].apply(formato_empresa)
        st.dataframe(tabla, use_container_width=True, hide_index=True)

    sector_sugerido = None
    if not sector_mostrado and "merco_sectores_2026" in files:
        sec_prob = None
        if cliente_actual and normalize_text(cliente_actual) in _CLIENTE_SECTORES_NORM:
            sec_prob = _CLIENTE_SECTORES_NORM[normalize_text(cliente_actual)]
        if not sec_prob:
            sec_prob = sector_probable(nombre_empresa or company_name_input)
        if sec_prob:
            sectores_2026 = parse_sector_ranking(files["merco_sectores_2026"])
            if sec_prob in sectores_2026:
                sector_sugerido = (sec_prob, sectores_2026[sec_prob])

    if not found_any:
        st.warning(f"La empresa '{company_name_input}' no fue encontrada en ninguno de los rankings Merco de 2024, 2025 o 2026.")
        top_10 = None
        if "merco_empresas_2026" in files:
            df_empresas_2026 = parse_general_ranking(files["merco_empresas_2026"])
            if df_empresas_2026 is not None and all(c in df_empresas_2026.columns for c in ['posicion', 'empresa', 'puntuacion']):
                top_10 = df_empresas_2026.head(10)[['posicion', 'empresa', 'puntuacion']].copy()
                top_10['empresa'] = top_10['empresa'].apply(formato_empresa)
        if "merco_empresas_2026" in files:
            if sector_sugerido and top_10 is not None:
                col_top, col_sector = st.columns(2)
                with col_top:
                    st.markdown("**Top 10 · Merco Empresas 2026**")
                    st.caption("Referencia del ranking general.")
                    st.dataframe(top_10, use_container_width=True, hide_index=True)
                with col_sector:
                    mostrar_tabla_sector(
                        sector_sugerido[0], sector_sugerido[1],
                        "La empresa buscada no figura en los rankings; por su nombre, este es su sector probable y las empresas que sí aparecen en él en 2026."
                    )
            elif top_10 is not None:
                st.info("A continuación, se muestra el Top 10 del ranking general 'Merco Empresas 2026' como referencia.")
                st.dataframe(top_10, use_container_width=True, hide_index=True)
        # El informe para copiar tiene la MISMA estructura que cuando la empresa
        # sí aparece (intro + contenido + outro); el contenido son las tablas.
        cuerpo_no = [
            f"{_base_input} no aparece en los rankings Merco Empresas, Talento, Líderes y Sectores de las ediciones 2024, 2025 y 2026."
        ]
        if sector_sugerido:
            filas_sec = "\n".join(
                f"{f.posicion}\t{formato_empresa(f.empresa)}" for f in sector_sugerido[1].itertuples(index=False)
            )
            cuerpo_no.append(f"Tabla del sector {sector_sugerido[0]} · Merco Sectores 2026:\nPosición\tEmpresa\n{filas_sec}")
        if top_10 is not None:
            filas_top = "\n".join(
                f"{f.posicion}\t{f.empresa}\t{f.puntuacion}" for f in top_10.itertuples(index=False)
            )
            cuerpo_no.append(f"Top 10 · Merco Empresas 2026:\nPosición\tEmpresa\tPuntuación\n{filas_top}")
        informe_no_encontrado = (
            INTRO_TEXT.strip()
            + "\n\n" + "\n\n".join(cuerpo_no)
            + "\n\n" + OUTRO_TEXT.replace("---", "").strip()
        )
        st.markdown("---")
        boton_copiar(informe_no_encontrado)
        st.subheader("📋 Informe completo para copiar")
        st.caption("El bloque reúne la introducción, el aviso con las tablas y el texto de cierre, en texto plano y sin formato. También puedes copiarlo con el ícono en la esquina superior derecha del bloque.")
        st.code(informe_no_encontrado, language=None)
    elif sector_sugerido:
        st.markdown("---")
        st.subheader("🧭 Sector probable de la empresa")
        mostrar_tabla_sector(
            sector_sugerido[0], sector_sugerido[1],
            "La empresa no figura en el ranking sectorial 2026; por su nombre, este es su sector probable y las empresas que sí aparecen en él."
        )

    if textos_informe:
        informe_completo = (
            INTRO_TEXT.strip()
            + "\n\n" + "\n\n".join(t.replace("**", "").replace("*", "") for t in textos_informe)
            + "\n\n" + OUTRO_TEXT.replace("---", "").strip()
        )
        st.markdown("---")
        boton_copiar(informe_completo)
        st.subheader("📋 Informe completo para copiar")
        st.caption("El bloque reúne la introducción, los resultados y el texto de cierre, en texto plano y sin formato. También puedes copiarlo con el ícono en la esquina superior derecha del bloque.")
        st.code(informe_completo, language=None)

    st.markdown(OUTRO_TEXT)
else:
    st.info("Por favor, ingrese el nombre de una empresa para comenzar el análisis.")

st.markdown("---")

