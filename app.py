import streamlit as st
import pandas as pd
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

# --- FUNCIÓN DE NORMALIZACIÓN (LA CLAVE DE LA MEJORA) ---
def normalize_text(text):
    """Limpia y estandariza el texto para hacer comparaciones robustas."""
    if not isinstance(text, str):
        return ""
    
    # 1. Quitar tildes y caracteres especiales
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')
    # 2. Convertir a minúsculas
    text = text.lower()
    
    # 3. Eliminar palabras corporativas comunes y caracteres no alfanuméricos
    # Usamos \b para asegurar que sean palabras completas
    words_to_remove = [r'\bgrupo\b', r'\bcomercializadora\b', r'\bs\.a\.s\b', r'\bsas\b', r'\bs\.a\b', r'\bltda\b', r'\bcompany\b', r'\binternational\b', r'\bessity\b']
    for word_regex in words_to_remove:
        text = re.sub(word_regex, '', text)
    
    # 4. Quitar todo lo que no sea letra o número
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # 5. Eliminar espacios extra
    text = ' '.join(text.split())
    return text.strip()


# --- Funciones de Carga y Parseo (Modificadas para incluir normalización) ---
@st.cache_data
def parse_general_ranking(file_path):
    """Parsea archivos de ranking generales y añade una columna normalizada."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        df_list = pd.read_html(StringIO(content))
        if not df_list: return None
        
        df = df_list[0]
        df.columns = [str(col) for col in df.columns]

        if 'Lider' in df.columns:
            df[['Lider_Nombre', 'Empresa']] = df['Lider'].str.split('<em>', expand=True, n=1)
            df['Empresa'] = df['Empresa'].str.replace(r'</em>', '', regex=True).str.strip()
            df = df.drop(columns=['Lider'])
        
        if 'Empresa' in df.columns:
            df['Empresa_normalized'] = df['Empresa'].apply(normalize_text)
        
        if 'Posicion' in df.columns:
            df['Posicion'] = pd.to_numeric(df['Posicion'], errors='coerce')

        return df
    except (FileNotFoundError, IndexError):
        return None

@st.cache_data
def parse_sector_ranking(file_path):
    """Parsea el archivo de ranking por sectores y añade columna normalizada."""
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
                df.columns = [str(col) for col in df.columns]
                if 'Empresa' in df.columns:
                    df['Empresa_normalized'] = df['Empresa'].apply(normalize_text)
                if 'Posición' in df.columns:
                    df['Posición'] = pd.to_numeric(df['Posición'], errors='coerce')
                sector_data[sector_name] = df
        
        return sector_data
    except FileNotFoundError:
        return {}

# --- Funciones de Búsqueda (Actualizadas para usar la columna normalizada) ---
def find_company_in_df_robust(df, normalized_query):
    """Busca una empresa comparando los nombres normalizados."""
    if df is None or 'Empresa_normalized' not in df.columns or not normalized_query:
        return None, None

    # Buscar una coincidencia exacta en el nombre normalizado
    exact_match = df[df['Empresa_normalized'] == normalized_query]
    if not exact_match.empty:
        pos = exact_match.iloc[0].get('Posicion')
        original_name = exact_match.iloc[0].get('Empresa')
        return int(pos) if pd.notna(pos) else None, original_name

    # Si no hay coincidencia exacta, buscar si la consulta está contenida
    partial_match = df[df['Empresa_normalized'].str.contains(normalized_query, na=False)]
    if not partial_match.empty:
        pos = partial_match.iloc[0].get('Posicion')
        original_name = partial_match.iloc[0].get('Empresa')
        return int(pos) if pd.notna(pos) else None, original_name
        
    return None, None

def find_company_in_sectors_robust(sector_data, normalized_query):
    if not sector_data:
        return None, None, None
    
    for sector, df in sector_data.items():
        if df is None or 'Empresa_normalized' not in df.columns:
            continue
        
        # Lógica de búsqueda mejorada (primero exacta, luego parcial)
        exact_match = df[df['Empresa_normalized'] == normalized_query]
        if not exact_match.empty:
            pos = exact_match.iloc[0].get('Posición')
            original_name = exact_match.iloc[0].get('Empresa')
            return sector, (int(pos) if pd.notna(pos) else None), original_name

        partial_match = df[df['Empresa_normalized'].str.contains(normalized_query, na=False)]
        if not partial_match.empty:
            pos = partial_match.iloc[0].get('Posición')
            original_name = partial_match.iloc[0].get('Empresa')
            return sector, (int(pos) if pd.notna(pos) else None), original_name

    return None, None, None


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
    # NORMALIZAR la entrada del usuario UNA SOLA VEZ
    normalized_input = normalize_text(company_name_input)
    
    # Carga perezosa de datos
    DATA_DIR = "data"
    files = {
        "empresas_2025": os.path.join(DATA_DIR, "merco_empresas_2025.txt"),
        "empresas_2024": os.path.join(DATA_DIR, "merco_empresas_2024.txt"),
        "talento_2025": os.path.join(DATA_DIR, "merco_talento_2025.txt"),
        "talento_2024": os.path.join(DATA_DIR, "merco_talento_2024.txt"),
        "lideres_2025": os.path.join(DATA_DIR, "merco_lideres_2025.txt"),
        "lideres_2024": os.path.join(DATA_DIR, "merco_lideres_2024.txt"),
        "sectores_2025": os.path.join(DATA_DIR, "merco_sectores_2025.txt"),
        "sectores_2024": os.path.join(DATA_DIR, "merco_sectores_2024.txt"),
    }
    
    st.markdown("---")
    st.subheader(f"Análisis Reputacional para: **{company_name_input}**")
    st.markdown(INTRO_TEXT)
    
    found_any = False
    
    # Búsqueda en Rankings Generales
    RANKINGS_CONFIG = { "Merco Empresas": ("empresas_2025", "empresas_2024"), "Merco Talento": ("talento_2025", "talento_2024"), "Merco Líderes": ("lideres_2025", "lideres_2024") }
    for rank_name, (file_2025, file_2024) in RANKINGS_CONFIG.items():
        df_2025 = parse_general_ranking(files[file_2025])
        pos_2025, original_name_2025 = find_company_in_df_robust(df_2025, normalized_input)
        
        if pos_2025:
            found_any = True
            df_2024 = parse_general_ranking(files[file_2024])
            pos_2024, _ = find_company_in_df_robust(df_2024, normalized_input)
            
            report_text = f"Este mes, nos complace informar que la empresa **{original_name_2025}** ha alcanzado la posición **{pos_2025}** en el ranking **{rank_name} 2025**."
            
            if pos_2024:
                report_text += f" Comparativamente, en 2024 ocupó el puesto **{pos_2024}**."
            else:
                report_text += " En 2024 no figuraba en este ranking."
            st.success(report_text)

    # Búsqueda en Ranking Sectorial
    sectors_2025 = parse_sector_ranking(files["sectores_2025"])
    sector_2025, pos_2025, original_name_2025 = find_company_in_sectors_robust(sectors_2025, normalized_input)

    if sector_2025 and pos_2025:
        found_any = True
        sectors_2024 = parse_sector_ranking(files["sectores_2024"])
        sector_2024, pos_2024, _ = find_company_in_sectors_robust(sectors_2024, normalized_input)

        report_text = f"En el ranking **Merco Sectores 2025**, la empresa **{original_name_2025}** se posiciona en el puesto **{pos_2025}** dentro del sector **{sector_2025}**."
        
        if sector_2024 and pos_2024:
             report_text += f" Comparativamente, en 2024 ocupó el puesto **{pos_2024}** en el mismo sector."
        else:
            report_text += " En 2024 no figuraba en el ranking sectorial."
        st.success(report_text)
    
    # Manejo del caso "No Encontrado"
    if not found_any:
        st.warning(f"La empresa '{company_name_input}' no fue encontrada en ninguno de los rankings Merco para el año 2025.")
        st.info("A continuación, se muestra el Top 10 del ranking general 'Merco Empresas 2025' como referencia.")
        
        df_empresas_2025 = parse_general_ranking(files["empresas_2025"])
        if df_empresas_2025 is not None:
            display_columns = ['Posicion', 'Empresa', 'Puntuacion']
            existing_columns = [col for col in display_columns if col in df_empresas_2025.columns]
            top_10 = df_empresas_2025.head(10)[existing_columns]
            st.dataframe(top_10, use_container_width=True, hide_index=True)

    st.markdown(OUTRO_TEXT)
else:
    st.info("Por favor, ingrese el nombre de una empresa para comenzar el análisis.")
