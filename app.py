import streamlit as st
import pandas as pd
import os
import re
import unicodedata
from io import StringIO
from itertools import cycle

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
div[data-testid="stTextInput"] input { border-radius: 12px; border: 1.5px solid #DCD1BF; background: #FFFFFF; padding: 12px 16px; font-size: 17px; }
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
@st.cache_data
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
</div>
""", unsafe_allow_html=True)

INTRO_TEXT = """
En el ámbito empresarial contemporáneo, la medición de la reputación es una piedra angular para garantizar el éxito sostenible de cualquier empresa. En GlobalNews Group Colombia, somos conscientes de la inestimable naturaleza de la reputación empresarial y, como resultado, proporcionamos una mirada detallada al análisis reputacional.

Nuestro informe de reputación trasciende la mera recolección de datos, ofreciendo un valor agregado de alta relevancia. Para este mes, hemos integrado el posicionamiento en el ranking Merco en nuestro análisis. Esta herramienta exhaustiva evalúa la reputación de las empresas en Colombia a través de una metodología multistakeholder que engloba seis evaluaciones y más de veinte fuentes de información. La posición obtenida en este ranking refleja directamente el reconocimiento que la empresa ha logrado entre una amplia gama de grupos de interés. Es importante destacar que la metodología utilizada por Merco Empresas es completamente pública y accesible en su sitio web.
"""
OUTRO_TEXT = """
---
¿Está listo para elevar su estrategia de gestión de la reputación al próximo nivel? Esto es solo el principio, ya que en GlobalNews Group Colombia ofrecemos una variedad de herramientas avanzadas para fortalecer su capacidad de monitoreo de noticias, ya sea en medios tradicionales o en plataformas de redes sociales. ¡Descubra cómo podemos ayudarle a medir, gestionar y mejorar su reputación empresarial de manera efectiva y precisa!
"""
company_name_input = st.text_input("Introduce el nombre de la empresa a consultar:", placeholder="Ej: EPM, Nutresa, Crepes & Waffles").strip()

if company_name_input:
    normalized_input = normalize_text(company_name_input)
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

    textos_informe = []

    def mostrar_tarjeta(etiqueta, texto_md):
        """Muestra el resultado en una tarjeta y lo acumula para el informe completo."""
        textos_informe.append(texto_md)
        html_txt = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', texto_md)
        st.markdown(f'<div class="result-card"><span class="chip">{etiqueta}</span><br>{html_txt}</div>', unsafe_allow_html=True)

    # --- Redacción del informe comparativo 2026 / 2025 / 2024 (solo datos, sin juicios de valor) ---
    def frase_cambio(pos_ref, pos_new, anio_ref):
        """Describe el cambio entre dos puestos solo con cifras."""
        diff = pos_ref - pos_new
        if diff > 0: return f"subió {diff} puesto{'s' if diff != 1 else ''} frente a {anio_ref}"
        if diff < 0: return f"bajó {abs(diff)} puesto{'s' if diff != -1 else ''} frente a {anio_ref}"
        return f"se mantuvo en el mismo puesto que en {anio_ref}"

    def historial(pos):
        """Frases de historial según en qué años aparece (pos: {2026, 2025, 2024} -> puesto o None)."""
        p26, p25, p24 = pos[2026], pos[2025], pos[2024]
        if p26:
            if p25 and p24:
                return (f" En 2025 ocupó el puesto **{p25}** y en 2024 el puesto **{p24}**: "
                        f"{frase_cambio(p25, p26, 2025)} y {frase_cambio(p24, p26, 2024)}.")
            if p25:
                return (f" En 2025 ocupó el puesto **{p25}**: {frase_cambio(p25, p26, 2025)}. "
                        f"En 2024 no figuraba en este ranking.")
            if p24:
                return (f" No figuró en la edición de 2025. En 2024 ocupó el puesto **{p24}**: "
                        f"{frase_cambio(p24, p26, 2024)}.")
            return " No figuró en las ediciones de 2025 ni de 2024."
        # Sin aparición en 2026
        if p25 and p24:
            return (f" Su registro más reciente corresponde a 2025, cuando ocupó el puesto **{p25}**; "
                    f"en 2024 se ubicó en el puesto **{p24}**.")
        if p25:
            return f" En 2025 ocupó el puesto **{p25}**; en 2024 tampoco figuraba en este ranking."
        return f" Su única aparición de los últimos tres años fue en 2024, en el puesto **{p24}**; tampoco figuró en 2025."

    opening_phrases = cycle([
        "En el ranking **{rank} 2026**, la empresa **{nombre}** ocupa la posición **{pos}**.",
        "En **{rank} 2026**, la empresa **{nombre}** se ubica en el puesto **{pos}**.",
        "La empresa **{nombre}** registra la posición **{pos}** en el ranking **{rank} 2026**."
    ])

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

        if rank_name == "Merco Líderes":
            anio_ref = next(y for y in YEARS if y in datos)
            lider_ref = datos[anio_ref][2]
            if pos[2026]:
                texto = (f"En el ranking **Merco Líderes 2026**, **{lider_ref}**, de la empresa **{nombre}**, "
                         f"ocupa la posición **{pos[2026]}**.")
            else:
                texto = (f"En la edición 2026 del ranking **Merco Líderes**, la empresa **{nombre}** no aparece en la clasificación.")
            texto += historial(pos)
        elif pos[2026]:
            texto = next(opening_phrases).format(nombre=nombre, pos=pos[2026], rank=rank_name) + historial(pos)
        else:
            texto = (f"En la edición 2026 del ranking **{rank_name}**, la empresa **{nombre}** no aparece en la clasificación."
                     + historial(pos))
        mostrar_tarjeta(rank_name.upper(), texto)

    if all(f"merco_sectores_{y}" in files for y in YEARS):
        datos_sec = {}
        for year in YEARS:
            sectores = parse_sector_ranking(files[f"merco_sectores_{year}"])
            sector, pos, nombre = find_company_in_sectors_robust(sectores, normalized_input)
            if pos: datos_sec[year] = (sector, pos, nombre)
        if datos_sec:
            found_any = True
            pos = {y: (datos_sec[y][1] if y in datos_sec else None) for y in YEARS}
            anio_ref = next(y for y in YEARS if y in datos_sec)
            sector_ref, _, nombre = datos_sec[anio_ref]
            if pos[2026]:
                texto = (f"Adicionalmente, en el ranking **Merco Sectores 2026**, la empresa **{nombre}** ocupa "
                         f"la posición **{pos[2026]}** dentro del sector **{sector_ref}**.")
            else:
                texto = (f"Adicionalmente, en el ranking **Merco Sectores 2026**, la empresa **{nombre}** no aparece "
                         f"en la clasificación (en {anio_ref} figuró en el sector **{sector_ref}**).")
            texto += historial(pos)
            mostrar_tarjeta("MERCO SECTORES", texto)

    if not found_any:
        st.warning(f"La empresa '{company_name_input}' no fue encontrada en ninguno de los rankings Merco de 2024, 2025 o 2026.")
        st.info("A continuación, se muestra el Top 10 del ranking general 'Merco Empresas 2026' como referencia.")
        if "merco_empresas_2026" in files:
            df_empresas_2026 = parse_general_ranking(files["merco_empresas_2026"])
            if df_empresas_2026 is not None and all(c in df_empresas_2026.columns for c in ['posicion', 'empresa', 'puntuacion']):
                top_10 = df_empresas_2026.head(10)[['posicion', 'empresa', 'puntuacion']]
                st.dataframe(top_10, use_container_width=True, hide_index=True)

    if textos_informe:
        informe_completo = (
            INTRO_TEXT.strip()
            + "\n\n" + "\n\n".join(t.replace("**", "") for t in textos_informe)
            + "\n\n" + OUTRO_TEXT.replace("---", "").strip()
        )
        st.markdown("---")
        st.subheader("📋 Informe completo para copiar")
        st.caption("El bloque reúne la introducción, los resultados y el texto de cierre. Botón de copiar en la esquina superior derecha del bloque.")
        st.code(informe_completo, language=None)
        st.download_button(
            "⬇️ Descargar el informe en .txt",
            data=informe_completo,
            file_name=f"informe_merco_{normalized_input.replace(' ', '_')}.txt",
            mime="text/plain"
        )

    st.markdown(OUTRO_TEXT)
else:
    st.info("Por favor, ingrese el nombre de una empresa para comenzar el análisis.")

st.markdown("---")
st.markdown("<div style='text-align: center; color: grey;'>Creada con 🤖 por Johnathan Cortés</div>", unsafe_allow_html=True)
