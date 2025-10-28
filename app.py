import streamlit as st
import pandas as pd
import os
import re
from io import StringIO

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Generador de Informes Merco",
    page_icon="📊",
    layout="wide"
)

# --- Funciones de Carga y Parseo de Datos (con caché para optimización) ---

# Usamos st.cache_data para que los archivos no se lean y procesen cada vez que interactuamos con la app.
@st.cache_data
def parse_general_ranking(file_path):
    """Parsea archivos de ranking generales (Empresas, Talento, Líderes)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # pandas.read_html es excelente para extraer tablas de HTML
        df_list = pd.read_html(StringIO(content))
        if not df_list:
            return None
        
        df = df_list[0]
        # Limpieza de nombres de columnas
        df.columns = [col.replace('ó', 'o').replace('n', 'n') for col in df.columns] # Normalizar nombres de columna
        
        # Caso especial para el ranking de Lideres, donde la empresa está en la misma celda
        if 'Lider' in df.columns:
            # Extraer el nombre del líder y la empresa en columnas separadas
            df[['Lider_Nombre', 'Empresa']] = df['Lider'].str.split('<em>', expand=True)
            df['Empresa'] = df['Empresa'].str.replace(r'</em>', '', regex=True)
            df = df.drop(columns=['Lider']) # Quitamos la columna original
            df['Empresa'] = df['Empresa'].str.strip()

        return df
    except (FileNotFoundError, IndexError):
        # Si el archivo no existe o no tiene tablas, devuelve None
        return None

@st.cache_data
def parse_sector_ranking(file_path):
    """Parsea el archivo de ranking por sectores, que tiene múltiples tablas."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Usamos regex para encontrar cada título de sector (<h3>) y su tabla correspondiente (<table>)
        sector_tables = re.findall(r'<h3.*?>(.*?)</h3>.*?<table(.*?)</table>', content, re.DOTALL)
        
        sector_data = {}
        for sector_name, table_html in sector_tables:
            # Limpiamos el nombre del sector y leemos la tabla
            sector_name = sector_name.strip()
            full_table_html = f"<table{table_html}>"
            df_list = pd.read_html(StringIO(full_table_html))
            if df_list:
                sector_data[sector_name] = df_list[0]
        
        return sector_data
    except FileNotFoundError:
        return {}

# --- Funciones de Búsqueda ---

def find_company_in_df(df, company_name):
    """Busca una empresa en un DataFrame general y devuelve su posición."""
    if df is None or 'Empresa' not in df.columns:
        return None
    
    # Búsqueda insensible a mayúsculas/minúsculas
    result = df[df['Empresa'].str.contains(company_name, case=False, na=False)]
    if not result.empty:
        # Devuelve la primera coincidencia
        return result.iloc[0]['Posicion']
    return None

def find_company_in_sectors(sector_data, company_name):
    """Busca una empresa en los datos de sectores y devuelve el sector y la posición."""
    if not sector_data:
        return None, None
    
    for sector, df in sector_data.items():
        if df is None or 'Empresa' not in df.columns:
            continue
        result = df[df['Empresa'].str.contains(company_name, case=False, na=False)]
        if not result.empty:
            return sector, result.iloc[0]['Posición']
    return None, None


# --- Interfaz de Usuario de Streamlit ---

st.title("📊 Generador de Informes de Reputación - Ranking Merco")
st.markdown("Esta herramienta recupera la posición de una empresa en los rankings Merco 2025 y 2024 y genera un informe comparativo.")

# --- Textos de plantilla ---
INTRO_TEXT = """
En el ámbito empresarial contemporáneo, la medición de la reputación es una piedra angular para garantizar el éxito sostenible de cualquier empresa. En GlobalNews Group Colombia, somos conscientes de la inestimable naturaleza de la reputación empresarial y, como resultado, proporcionamos una mirada detallada al análisis reputacional.

Nuestro informe de reputación trasciende la mera recolección de datos, ofreciendo un valor agregado de alta relevancia. Para este mes, hemos integrado el posicionamiento en el prestigioso ranking Merco en nuestro análisis. Esta herramienta exhaustiva evalúa la reputación de las empresas en Colombia a través de una metodología multistakeholder que engloba seis evaluaciones y más de veinte fuentes de información. La posición obtenida en este ranking refleja directamente el reconocimiento que la empresa ha logrado entre una amplia gama de grupos de interés. Es importante destacar que la metodología utilizada por Merco Empresas es completamente pública y accesible en su sitio web.
"""

OUTRO_TEXT = """
---
¿Está listo para elevar su estrategia de gestión de la reputación al próximo nivel? Esto es solo el principio, ya que en GlobalNews Group Colombia ofrecemos una variedad de herramientas avanzadas para fortalecer su capacidad de monitoreo de noticias, ya sea en medios tradicionales o en plataformas de redes sociales. ¡Descubra cómo podemos ayudarle a medir, gestionar y mejorar su reputación empresarial de manera efectiva y precisa!
"""

# --- Columnas para la entrada y el logo ---
col1, col2 = st.columns([2, 1])

with col1:
    company_name_input = st.text_input(
        "Introduce el nombre de la empresa a consultar:",
        placeholder="Ej: Bancolombia"
    ).strip()

# --- Carga de datos ---
DATA_DIR = "data"
RANKINGS = {
    "Merco Empresas": "merco_empresas",
    "Merco Talento": "merco_talento",
    "Merco Líderes": "merco_lideres",
}
SECTOR_FILE_PREFIX = "merco_sectores"

if company_name_input:
    st.markdown("---")
    st.subheader(f"Análisis Reputacional para: **{company_name_input}**")

    st.markdown(INTRO_TEXT)
    
    found_any = False
    
    # 1. Búsqueda en Rankings Generales (Empresas, Talento, Líderes)
    for rank_name, file_prefix in RANKINGS.items():
        df_2025 = parse_general_ranking(os.path.join(DATA_DIR, f"{file_prefix}_2025.txt"))
        df_2024 = parse_general_ranking(os.path.join(DATA_DIR, f"{file_prefix}_2024.txt"))

        pos_2025 = find_company_in_df(df_2025, company_name_input)
        
        if pos_2025:
            found_any = True
            pos_2024 = find_company_in_df(df_2024, company_name_input)
            
            report_text = f"Este mes, nos complace informar que la empresa **{company_name_input}** ha alcanzado la posición **{pos_2025}** en el ranking **{rank_name} 2025**."
            
            if pos_2024:
                report_text += f" Comparativamente, en 2024 ocupó el puesto **{pos_2024}**."
            else:
                report_text += " En 2024 no figuraba en este ranking."
            
            st.success(report_text)

    # 2. Búsqueda en Ranking Sectorial
    sectors_2025 = parse_sector_ranking(os.path.join(DATA_DIR, f"{SECTOR_FILE_PREFIX}_2025.txt"))
    sectors_2024 = parse_sector_ranking(os.path.join(DATA_DIR, f"{SECTOR_FILE_PREFIX}_2024.txt"))
    
    sector_2025, pos_2025 = find_company_in_sectors(sectors_2025, company_name_input)

    if sector_2025 and pos_2025:
        found_any = True
        sector_2024, pos_2024 = find_company_in_sectors(sectors_2024, company_name_input)

        report_text = f"En el ranking **Merco Sectores 2025**, la empresa **{company_name_input}** se posiciona en el puesto **{pos_2025}** dentro del sector **{sector_2025}**."
        
        if sector_2024 and pos_2024:
             report_text += f" Comparativamente, en 2024 ocupó el puesto **{pos_2024}** en el mismo sector."
        else:
            report_text += " En 2024 no figuraba en el ranking sectorial."
            
        st.success(report_text)
    
    # --- Manejo del caso donde no se encuentra la empresa ---
    if not found_any:
        st.warning(f"La empresa '{company_name_input}' no fue encontrada en ninguno de los rankings principales de Merco para el año 2025.")
        st.info("A continuación, se muestra el Top 10 del ranking general 'Merco Empresas 2025' como referencia.")
        
        df_empresas_2025 = parse_general_ranking(os.path.join(DATA_DIR, "merco_empresas_2025.txt"))
        if df_empresas_2025 is not None:
            # Seleccionar y renombrar columnas para una mejor visualización
            top_10 = df_empresas_2025.head(10)[['Posicion', 'Empresa', 'Puntuacion']]
            st.dataframe(top_10, use_container_width=True, hide_index=True)

    st.markdown(OUTRO_TEXT)

else:
    st.info("Por favor, ingrese el nombre de una empresa para comenzar el análisis.")
