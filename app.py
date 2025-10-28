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

# --- FUNCIÓN DE NORMALIZACIÓN ---
def normalize_text(text):
    if not isinstance(text, str): return ""
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
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'lideres' in os.path.basename(file_path):
            rows = re.findall(r'<tr>(.*?)</tr>', content, re.DOTALL)
            data_list = []
            for row_html in rows[1:]:
                pos_match = re.search(r'<span.*?>(.*?)</span>', row_html)
                # Modificado para capturar el líder y la empresa
                leader_company_match = re.search(r'<td>\s*(.*?)\s*<em>(.*?)</em></td>', row_html, re.DOTALL)
                
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
        leader_name = row.get('lidernombre') # Obtener el nombre del líder
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
st.title("📊 Generador de Informes de Reputación - Ranking Merco")
st.markdown("Esta herramienta recupera la posición de una empresa en los rankings Merco 2025 y 2024 y genera un informe comparativo.")

INTRO_TEXT = "..." # Mantenido igual
OUTRO_TEXT = "..." # Mantenido igual

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
    
    opening_phrases = cycle([
        "En el análisis de este mes, destacamos que la empresa **{original_name}** ha alcanzado la posición **{pos_2025}** en el ranking **{rank_name} 2025**.",
        "El informe actual resalta el desempeño de **{original_name}**, que se ubica en el puesto **{pos_2025}** del prestigioso ranking **{rank_name} 2025**.",
        "Para el período 2025, es notable que **{original_name}** ha logrado la posición **{pos_2025}** dentro de la clasificación **{rank_name}**."
    ])

    def get_comparison_text(pos_2024, pos_2025):
        if pos_2024:
            diff = pos_2024 - pos_2025
            if diff > 15: movement = "un notable avance"
            elif diff > 0: movement = "un avance"
            elif diff < -10: movement = "un gran retroceso"
            elif diff < 0: movement = "un ligero retroceso"
            else: movement = "una consolidación de su posición"
            return f" Este resultado representa {movement} frente al puesto **{pos_2024}** que ocupó en 2024."
        else:
            return " En la medición de 2024, la empresa no figuraba en este ranking."

    RANKINGS_CONFIG = {
        "Merco Empresas": ("merco_empresas_2025", "merco_empresas_2024"),
        "Merco Talento": ("merco_talento_2025", "merco_talento_2024"),
        "Merco Líderes": ("merco_lideres_2025", "merco_lideres_2024"),
    }

    for rank_name, (key_2025, key_2024) in RANKINGS_CONFIG.items():
        if key_2025 not in files or key_2024 not in files: continue
        
        df_2025 = parse_general_ranking(files[key_2025])
        pos_2025, original_name, leader_name = find_company_in_df_robust(df_2025, normalized_input)
        
        if pos_2025 and original_name:
            found_any = True
            df_2024 = parse_general_ranking(files[key_2024])
            pos_2024, _, _ = find_company_in_df_robust(df_2024, normalized_input)
            
            # ### CAMBIO CLAVE: Lógica de redacción específica para Líderes ###
            if rank_name == "Merco Líderes" and leader_name:
                report_text = f"En el ranking **Merco Líderes 2025**, **{leader_name}**, de la empresa **{original_name}**, ha obtenido la posición **{pos_2025}**."
                if pos_2024:
                    report_text += f" Para el año 2024, su posición fue la **{pos_2024}**."
                else:
                    report_text += " En 2024, no figuraba en este ranking."
            else:
                opening = next(opening_phrases).format(original_name=original_name, pos_2025=pos_2025, rank_name=rank_name)
                comparison = get_comparison_text(pos_2024, pos_2025)
                report_text = opening + comparison
            
            st.success(report_text)

    if "merco_sectores_2025" in files and "merco_sectores_2024" in files:
        sectors_2025 = parse_sector_ranking(files["merco_sectores_2025"])
        sector, pos_2025, original_name = find_company_in_sectors_robust(sectors_2025, normalized_input)
        if sector and pos_2025 and original_name:
            found_any = True
            sectors_2024 = parse_sector_ranking(files["merco_sectores_2024"])
            _, pos_2024, _ = find_company_in_sectors_robust(sectors_2024, normalized_input)
            report_text = f"Adicionalmente, en el ranking **Merco Sectores 2025**, la empresa **{original_name}** se destaca en la posición **{pos_2025}** dentro del sector **{sector}**."
            report_text += get_comparison_text(pos_2024, pos_2025)
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
else:
    st.info("Por favor, ingrese el nombre de una empresa para comenzar el análisis.")

st.markdown("---")
st.markdown("<div style='text-align: center; color: grey;'>Creada con 🤖 por Johnathan Cortés</div>", unsafe_allow_html=True)
