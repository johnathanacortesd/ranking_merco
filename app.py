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

# --- Funciones de Carga y Parseo (SIN CAMBIOS, el caché sigue siendo clave) ---
@st.cache_data
def parse_general_ranking(file_path):
    """Parsea archivos de ranking generales (Empresas, Talento, Líderes)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        df_list = pd.read_html(StringIO(content))
        if not df_list:
            return None
        
        df = df_list[0]
        df.columns = [str(col) for col in df.columns]

        if 'Lider' in df.columns:
            df[['Lider_Nombre', 'Empresa']] = df['Lider'].str.split('<em>', expand=True, n=1)
            df['Empresa'] = df['Empresa'].str.replace(r'</em>', '', regex=True).str.strip()
            df = df.drop(columns=['Lider'])
            df['Empresa'] = df['Empresa'].str.strip()
        
        # Asegurarse que la columna Posicion sea numérica para evitar errores de tipo
        if 'Posicion' in df.columns:
            df['Posicion'] = pd.to_numeric(df['Posicion'], errors='coerce')

        return df
    except (FileNotFoundError, IndexError):
        return None

@st.cache_data
def parse_sector_ranking(file_path):
    """Parsea el archivo de ranking por sectores."""
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
                # Asegurarse que la columna Posición sea numérica
                if 'Posición' in df.columns:
                    df['Posición'] = pd.to_numeric(df['Posición'], errors='coerce')
                sector_data[sector_name] = df
        
        return sector_data
    except FileNotFoundError:
        return {}

# --- Funciones de Búsqueda (SIN CAMBIOS) ---
def find_company_in_df(df, company_name):
    """Busca una empresa en un DataFrame general y devuelve su posición."""
    if df is None or 'Empresa' not in df.columns:
        return None
    
    result = df[df['Empresa'].str.contains(company_name, case=False, na=False)]
    if not result.empty:
        pos = result.iloc[0].get('Posicion')
        # Convertir a entero si no es nulo
        return int(pos) if pd.notna(pos) else None
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
            pos = result.iloc[0].get('Posición')
            return sector, (int(pos) if pd.notna(pos) else None)
    return None, None

# --- Interfaz de Usuario de Streamlit ---

st.title("📊 Generador de Informes de Reputación - Ranking Merco")
st.markdown("Esta herramienta recupera la posición de una empresa en los rankings Merco 2025 y 2024 y genera un informe comparativo.")

INTRO_TEXT = "..." # Mantén tus textos aquí
OUTRO_TEXT = "..."

col1, col2 = st.columns([2, 1])

with col1:
    company_name_input = st.text_input(
        "Introduce el nombre de la empresa a consultar:",
        placeholder="Ej: Bancolombia"
    ).strip()

# --- LÓGICA PRINCIPAL DE LA APP ---
if company_name_input:
    # --- LAZY LOADING: Carga los datos SOLO cuando se hace una búsqueda ---
    DATA_DIR = "data"
    
    # Rutas a los archivos
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
    
    # 1. Búsqueda en Rankings Generales
    RANKINGS_CONFIG = {
        "Merco Empresas": ("empresas_2025", "empresas_2024"),
        "Merco Talento": ("talento_2025", "talento_2024"),
        "Merco Líderes": ("lideres_2025", "lideres_2024"),
    }

    for rank_name, (file_2025, file_2024) in RANKINGS_CONFIG.items():
        df_2025 = parse_general_ranking(files[file_2025])
        pos_2025 = find_company_in_df(df_2025, company_name_input)
        
        if pos_2025:
            found_any = True
            df_2024 = parse_general_ranking(files[file_2024])
            pos_2024 = find_company_in_df(df_2024, company_name_input)
            
            report_text = f"Este mes, nos complace informar que la empresa **{company_name_input}** ha alcanzado la posición **{pos_2025}** en el ranking **{rank_name} 2025**."
            
            if pos_2024:
                report_text += f" Comparativamente, en 2024 ocupó el puesto **{pos_2024}**."
            else:
                report_text += " En 2024 no figuraba en este ranking."
            
            st.success(report_text)

    # 2. Búsqueda en Ranking Sectorial
    sectors_2025 = parse_sector_ranking(files["sectores_2025"])
    sector_2025, pos_2025 = find_company_in_sectors(sectors_2025, company_name_input)

    if sector_2025 and pos_2025:
        found_any = True
        sectors_2024 = parse_sector_ranking(files["sectores_2024"])
        sector_2024, pos_2024 = find_company_in_sectors(sectors_2024, company_name_input)

        report_text = f"En el ranking **Merco Sectores 2025**, la empresa **{company_name_input}** se posiciona en el puesto **{pos_2025}** dentro del sector **{sector_2025}**."
        
        if sector_2024 and pos_2024:
             report_text += f" Comparativamente, en 2024 ocupó el puesto **{pos_2024}** en el mismo sector."
        else:
            report_text += " En 2024 no figuraba en el ranking sectorial."
            
        st.success(report_text)
    
    # 3. Manejo del caso "No Encontrado"
    if not found_any:
        st.warning(f"La empresa '{company_name_input}' no fue encontrada en ninguno de los rankings Merco para el año 2025.")
        st.info("A continuación, se muestra el Top 10 del ranking general 'Merco Empresas 2025' como referencia.")
        
        # Cargar solo el archivo necesario para mostrar el Top 10
        df_empresas_2025 = parse_general_ranking(files["empresas_2025"])
        if df_empresas_2025 is not None:
            top_10_columns = ['Posicion', 'Empresa', 'Puntuacion']
            # Asegurarnos de que las columnas existan antes de intentar mostrarlas
            display_columns = [col for col in top_10_columns if col in df_empresas_2025.columns]
            top_10 = df_empresas_2025.head(10)[display_columns]
            st.dataframe(top_10, use_container_width=True, hide_index=True)

    st.markdown(OUTRO_TEXT)
else:
    st.info("Por favor, ingrese el nombre de una empresa para comenzar el análisis.")
