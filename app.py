import streamlit as st
import pandas as pd
import os
import re
import unicodedata
from io import StringIO
import streamlit.components.v1 as components

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Generador de Informes Merco",
    page_icon="📊",
    layout="wide"
)

# --- FUNCIÓN DE NORMALIZACIÓN ---
def normalize_text(text):
    """Limpia y estandariza el texto para hacer comparaciones robustas."""
    if not isinstance(text, str):
        return ""
    
    # Quitar tildes y caracteres especiales
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.lower()
    
    # Eliminar palabras corporativas comunes y contenido entre paréntesis
    words_to_remove = [
        r'\bgrupo\b', r'\bcomercializadora\b', r'\borganizacion\b', r'\bs\.a\.s\b', 
        r'\bsas\b', r'\bs\.a\b', r'\bltda\b', r'\bcompany\b', r'\binternational\b', 
        r'\bessity\b', r'\(.*?\)'
    ]
    for word_regex in words_to_remove:
        text = re.sub(word_regex, '', text, flags=re.IGNORECASE)
    
    # Quitar todo lo que no sea letra o número
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Eliminar espacios extra
    return ' '.join(text.split()).strip()

# --- Funciones de Carga y Parseo ---
@st.cache_data
def parse_general_ranking(file_path):
    """Parsea archivos de ranking generales y normaliza las columnas."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        df_list = pd.read_html(StringIO(content))
        if not df_list: return None
        
        df = df_list[0]
        df.columns = [normalize_text(str(col)) for col in df.columns]

        if 'lider' in df.columns:
            temp_df = df['lider'].str.split('<em>', expand=True, n=1)
            df['lider_nombre'] = temp_df[0]
            df['empresa'] = temp_df[1].str.replace(r'</em>', '', regex=True).str.strip() if temp_df.shape[1] > 1 else ''
            df = df.drop(columns=['lider'])
        
        if 'empresa' in df.columns:
            df['empresa_normalized'] = df['empresa'].apply(normalize_text)
        
        if 'posicion' in df.columns:
            df['posicion'] = pd.to_numeric(df['posicion'], errors='coerce')

        return df
    except (FileNotFoundError, IndexError, ValueError):
        st.error(f"Error procesando el archivo: {file_path}. Verifique que el archivo exista y tenga el formato correcto.")
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
        st.error(f"No se encontró el archivo: {file_path}. Asegúrese de que esté en la carpeta 'data'.")
        return {}

# --- Funciones de Búsqueda ---
def find_company_in_df_robust(df, normalized_query):
    if df is None or 'empresa_normalized' not in df.columns or not normalized_query:
        return None, None

    match = df[df['empresa_normalized'] == normalized_query]
    if match.empty:
        match = df[df['empresa_normalized'].str.contains(normalized_query, na=False)]
    
    if not match.empty:
        pos = match.iloc[0].get('posicion')
        original_name = match.iloc[0].get('empresa')
        return (int(pos) if pd.notna(pos) else None), original_name
        
    return None, None

def find_company_in_sectors_robust(sector_data, normalized_query):
    if not sector_data:
        return None, None, None
    
    for sector, df in sector_data.items():
        if df is None or 'empresa_normalized' not in df.columns:
            continue
        
        match = df[df['empresa_normalized'] == normalized_query]
        if match.empty:
            match = df[df['empresa_normalized'].str.contains(normalized_query, na=False)]

        if not match.empty:
            pos = match.iloc[0].get('posicion')
            original_name = match.iloc[0].get('empresa')
            return sector, (int(pos) if pd.notna(pos) else None), original_name

    return None, None, None

def select_and_copy_text(element_id):
    """Función para seleccionar todo el texto de un elemento y copiarlo automáticamente"""
    components.html(
        f"""
        <script>
        function selectAndCopy() {{
            const element = window.parent.document.getElementById('{element_id}');
            if (element) {{
                const range = document.createRange();
                range.selectNode(element);
                const selection = window.parent.window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
                
                try {{
                    window.parent.document.execCommand('copy');
                    console.log('Texto copiado');
                }} catch (err) {{
                    console.error('Error al copiar:', err);
                }}
            }}
        }}
        selectAndCopy();
        </script>
        """,
        height=0
    )

# --- Interfaz de Usuario y Lógica Principal ---

st.title("📊 Generador de Informes de Reputación - Ranking Merco")
st.markdown("Esta herramienta recupera la posición de una empresa en los rankings Merco 2025 y 2024 y genera un informe comparativo.")

INTRO_TEXT = """
En el ámbito empresarial contemporáneo, la medición de la reputación es una piedra angular para garantizar el éxito sostenible de cualquier empresa. En GlobalNews Group Colombia, somos conscientes de la inestimable naturaleza de la reputación empresarial y, como resultado, proporcionamos una mirada detallada al análisis reputacional.

Nuestro informe de reputación trasciende la mera recolección de datos, ofreciendo un valor agregado de alta relevancia. Para este mes, hemos integrado el posicionamiento en el prestigioso ranking Merco en nuestro análisis. Esta herramienta exhaustiva evalúa la reputación de las empresas en Colombia a través de una metodología multistakeholder que engloba seis evaluaciones y más de veinte fuentes de información. La posición obtenida en este ranking refleja directamente el reconocimiento que la empresa ha logrado entre una amplia gama de grupos de interés. Es importante destacar que la metodología utilizada por Merco Empresas es completamente pública y accesible en su sitio web.
"""

OUTRO_TEXT = """
---
¿Está listo para elevar su estrategia de gestión de la reputación al próximo nivel? Esto es solo el principio, ya que en GlobalNews Group Colombia ofrecemos una variedad de herramientas avanzadas para fortalecer su capacidad de monitoreo de noticias, ya sea en medios tradicionales o en plataformas de redes sociales. ¡Descubra cómo podemos ayudarle a medir, gestionar y mejorar su reputación empresarial de manera efectiva y precisa!
"""

company_name_input = st.text_input(
    "Introduce el nombre de la empresa a consultar:",
    placeholder="Ej: EPM, Nutresa, Crepes & Waffles"
).strip()

if company_name_input:
    normalized_input = normalize_text(company_name_input)
    
    DATA_DIR = "data"
    
    try:
        files = { 
            f.replace('.txt', '').replace(' ', '_'): os.path.join(DATA_DIR, f) 
            for f in os.listdir(DATA_DIR) if f.endswith('.txt') 
        }
    except FileNotFoundError:
        st.error(f"No se encontró la carpeta '{DATA_DIR}'. Asegúrate de que exista y contenga los archivos .txt.")
        st.stop()

    st.markdown("---")
    
    # Contenedor con ID para selección
    st.markdown('<div id="report-content">', unsafe_allow_html=True)
    
    st.subheader(f"Análisis Reputacional para: **{company_name_input}**")
    st.markdown(INTRO_TEXT)
    
    found_any = False
    
    RANKINGS_CONFIG = {
        "Merco Empresas": ("merco_empresas_2025", "merco_empresas_2024"),
        "Merco Talento": ("merco_talento_2025", "merco_talento_2024"),
        "Merco Líderes": ("merco_lideres_2025", "merco_lideres_2024"),
    }

    for rank_name, (key_2025, key_2024) in RANKINGS_CONFIG.items():
        if key_2025 not in files or key_2024 not in files:
            continue
        
        df_2025 = parse_general_ranking(files[key_2025])
        pos_2025, original_name = find_company_in_df_robust(df_2025, normalized_input)
        
        if pos_2025 and original_name:
            found_any = True
            df_2024 = parse_general_ranking(files[key_2024])
            pos_2024, _ = find_company_in_df_robust(df_2024, normalized_input)
            
            report_text = f"Este mes, nos complace informar que la empresa **{original_name}** ha alcanzado la posición **{pos_2025}** en el ranking **{rank_name} 2025**."
            
            if pos_2024:
                report_text += f" Comparativamente, en 2024 ocupó el puesto **{pos_2024}**."
            else:
                report_text += " En 2024 no figuraba en este ranking."
            st.success(report_text)

    if "merco_sectores_2025" in files and "merco_sectores_2024" in files:
        sectors_2025 = parse_sector_ranking(files["merco_sectores_2025"])
        sector, pos_2025, original_name = find_company_in_sectors_robust(sectors_2025, normalized_input)

        if sector and pos_2025 and original_name:
            found_any = True
            sectors_2024 = parse_sector_ranking(files["merco_sectores_2024"])
            _, pos_2024, _ = find_company_in_sectors_robust(sectors_2024, normalized_input)

            report_text = f"En el ranking **Merco Sectores 2025**, la empresa **{original_name}** se posiciona en el puesto **{pos_2025}** dentro del sector **{sector}**."
            
            if pos_2024:
                 report_text += f" Comparativamente, en 2024 ocupó el puesto **{pos_2024}** en el mismo sector."
            else:
                report_text += " En 2024 no figuraba en el ranking sectorial."
            st.success(report_text)
    
    if not found_any:
        st.warning(f"La empresa '{company_name_input}' no fue encontrada en ninguno de los rankings Merco para el año 2025.")
        st.info("A continuación, se muestra el Top 10 del ranking general 'Merco Empresas 2025' como referencia.")
        
        if "merco_empresas_2025" in files:
            df_empresas_2025 = parse_general_ranking(files["merco_empresas_2025"])
            if df_empresas_2025 is not None and all(c in df_empresas_2025.columns for c in ['posicion', 'empresa', 'puntuacion']):
                top_10 = df_empresas_2025.head(10)[['posicion', 'empresa', 'puntuacion']]
                st.dataframe(top_10, use_container_width=True, hide_index=True)

    st.markdown(OUTRO_TEXT)
    
    # Cerrar contenedor
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Botón para seleccionar y copiar
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📋 Seleccionar Todo y Copiar", use_container_width=True, type="primary", key="copy_btn"):
            select_and_copy_text("report-content")
            st.success("✅ ¡Texto seleccionado y copiado! Presiona Ctrl+C si no se copió automáticamente.")
else:
    st.info("Por favor, ingrese el nombre de una empresa para comenzar el análisis.")

# --- Créditos al final de la página ---
st.markdown("---")
st.markdown("<div style='text-align: center; color: grey;'>Creada con 🤖 por Johnathan Cortés</div>", unsafe_allow_html=True)
