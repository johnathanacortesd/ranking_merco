import streamlit as st
import pandas as pd
import os
import re

# Configuración de la página
st.set_page_config(page_title="Ranking MERCO 2025", layout="wide")

# Función para parsear el archivo TXT del ranking
def parse_merco_data(txt_content):
    data = []
    lines = txt_content.strip().split('\n')
    
    posicion = None
    lider = None
    empresa = None
    puntuacion = None
    anterior = None
    
    for line in lines:
        # Buscar patrones de posición
        if '<td><span class="badge-pos-1' in line:
            pos_match = re.search(r'>(\d+)</span>', line)
            if pos_match:
                posicion = int(pos_match.group(1))
        
        # Extraer nombre y empresa
        elif '<td>' in line and '<em>' in line and '</em></td>' in line:
            name_match = re.search(r'<td>(.*?)<em>(.*?)</em></td>', line)
            if name_match:
                lider = name_match.group(1).strip()
                empresa = name_match.group(2).strip()
        
        # Extraer puntuación
        elif 'f-monospace' in line and posicion is not None:
            score_match = re.search(r'>(\d+)</td>', line)
            if score_match:
                puntuacion = int(score_match.group(1))
        
        # Extraer posición anterior y guardar registro
        elif 'title="Posición 2024"' in line or 'title="Posición 2023"' in line:
            ant_match = re.search(r'badge-pos-2.*?>(\d+)</span>', line)
            if ant_match:
                anterior = int(ant_match.group(1))
            else:
                anterior = None
            
            # Guardar registro
            if posicion and lider and empresa and puntuacion:
                data.append({
                    'posicion': posicion,
                    'lider': lider,
                    'empresa': empresa,
                    'puntuacion': puntuacion,
                    'anterior': anterior if anterior else posicion
                })
            
            # Reset variables
            posicion = None
            lider = None
            empresa = None
            puntuacion = None
            anterior = None
        
        # Caso cuando mantiene posición
        elif 'evol-eq' in line and posicion is not None:
            if posicion and lider and empresa and puntuacion:
                data.append({
                    'posicion': posicion,
                    'lider': lider,
                    'empresa': empresa,
                    'puntuacion': puntuacion,
                    'anterior': posicion
                })
            
            # Reset variables
            posicion = None
            lider = None
            empresa = None
            puntuacion = None
            anterior = None
        
        # Caso cuando es nueva entrada (sin posición anterior)
        elif 'title=""' in line and '</td>' in line and posicion is not None:
            if posicion and lider and empresa and puntuacion:
                data.append({
                    'posicion': posicion,
                    'lider': lider,
                    'empresa': empresa,
                    'puntuacion': puntuacion,
                    'anterior': None
                })
            
            # Reset variables
            posicion = None
            lider = None
            empresa = None
            puntuacion = None
            anterior = None
    
    return pd.DataFrame(data)

# Función para cargar archivos desde el repositorio
def cargar_datos_repo(ano, tipo_ranking):
    """Intenta cargar datos desde archivos en el repositorio"""
    try:
        filename = f"data/merco_{tipo_ranking.lower()}_{ano}.txt"
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            return parse_merco_data(content)
    except Exception as e:
        st.error(f"Error al cargar {filename}: {str(e)}")
    return None

# Función para generar el texto del informe con comparativo
def generar_informe(empresa_buscar, ranking_type, df_2025, df_2024):
    empresa_buscar_norm = empresa_buscar.upper().strip()
    
    # Buscar empresa en ranking 2025
    empresa_2025 = None
    for idx, row in df_2025.iterrows():
        if empresa_buscar_norm in row['empresa'].upper() or empresa_buscar_norm in row['lider'].upper():
            empresa_2025 = row
            break
    
    # Buscar empresa en ranking 2024
    empresa_2024 = None
    if df_2024 is not None:
        for idx, row in df_2024.iterrows():
            if empresa_buscar_norm in row['empresa'].upper() or empresa_buscar_norm in row['lider'].upper():
                empresa_2024 = row
                break
    
    # Texto base
    intro = f"""# RANKING MERCO

En el ámbito empresarial contemporáneo, la medición de la reputación es una piedra angular para garantizar el éxito sostenible de cualquier empresa. En GlobalNews Group Colombia, somos conscientes de la inestimable naturaleza de la reputación empresarial y, como resultado, proporcionamos una mirada detallada al análisis reputacional.

Nuestro informe de reputación trasciende la mera recolección de datos, ofreciendo un valor agregado de alta relevancia. Para este mes, hemos integrado el posicionamiento en el prestigioso ranking Merco en nuestro análisis.

Esta herramienta exhaustiva evalúa la reputación de las empresas en Colombia a través de una metodología multistakeholder que engloba seis evaluaciones y más de veinte fuentes de información. La posición obtenida en este ranking refleja directamente el reconocimiento que la empresa ha logrado entre una amplia gama de grupos de interés. Es importante destacar que la metodología utilizada por Merco Empresas es completamente pública y accesible en su sitio web.

"""
    
    if empresa_2025 is not None:
        # Caso 1: Empresa encontrada en 2025
        posicion_2025 = int(empresa_2025['posicion'])
        puntuacion_2025 = int(empresa_2025['puntuacion'])
        
        # Determinar posición 2024
        if empresa_2024 is not None:
            posicion_2024 = int(empresa_2024['posicion'])
            puntuacion_2024 = int(empresa_2024['puntuacion'])
        elif empresa_2025['anterior'] is not None and not pd.isna(empresa_2025['anterior']):
            posicion_2024 = int(empresa_2025['anterior'])
            puntuacion_2024 = None
        else:
            posicion_2024 = None
            puntuacion_2024 = None
        
        resultado = f"""**Este mes, nos complace informar que la empresa {empresa_2025['empresa']} ha alcanzado la posición {posicion_2025} en el ranking Merco {ranking_type} 2025.**
"""
        
        if posicion_2024 is not None:
            if posicion_2025 < posicion_2024:
                cambio = f"subió desde la posición {posicion_2024}"
                emoji = "📈"
            elif posicion_2025 > posicion_2024:
                cambio = f"bajó desde la posición {posicion_2024}"
                emoji = "📉"
            else:
                cambio = f"mantuvo la posición {posicion_2024}"
                emoji = "➡️"
            
            resultado += f"\n**Comparativamente, en 2024 ocupó el puesto {posicion_2024}.** {emoji}\n"
            
            if puntuacion_2024:
                dif_puntos = puntuacion_2025 - puntuacion_2024
                if dif_puntos > 0:
                    resultado += f"\n*Puntuación 2025: {puntuacion_2025} puntos (+{dif_puntos} vs 2024: {puntuacion_2024})*"
                elif dif_puntos < 0:
                    resultado += f"\n*Puntuación 2025: {puntuacion_2025} puntos ({dif_puntos} vs 2024: {puntuacion_2024})*"
                else:
                    resultado += f"\n*Puntuación 2025: {puntuacion_2025} puntos (sin cambio vs 2024)*"
        else:
            resultado += f"\n*Esta empresa es nueva en el ranking 2025 con {puntuacion_2025} puntos.* ⭐\n"
        
    else:
        # Caso 2: Empresa NO encontrada - Mostrar top 10 comparativo
        resultado = f"""**En relación a su sector, el ranking se distribuyó de la siguiente manera:**

### Top 10 Merco {ranking_type} - Comparativo 2024 vs 2025

"""
        top_10_2025 = df_2025.head(10)
        
        for idx, row in top_10_2025.iterrows():
            pos_2025 = int(row['posicion'])
            empresa_nombre = row['empresa']
            lider_nombre = row['lider']
            puntos_2025 = int(row['puntuacion'])
            
            # Buscar posición en 2024
            pos_2024 = None
            if df_2024 is not None:
                for idx_24, row_24 in df_2024.iterrows():
                    if row['empresa'].upper() in row_24['empresa'].upper() or row_24['empresa'].upper() in row['empresa'].upper():
                        pos_2024 = int(row_24['posicion'])
                        break
            
            if pos_2024 is None and row['anterior'] is not None and not pd.isna(row['anterior']):
                pos_2024 = int(row['anterior'])
            
            # Indicador de cambio
            if pos_2024:
                if pos_2025 < pos_2024:
                    indicador = f"↑ (↑{pos_2024 - pos_2025})"
                elif pos_2025 > pos_2024:
                    indicador = f"↓ (↓{pos_2025 - pos_2024})"
                else:
                    indicador = "="
                resultado += f"**{pos_2025}.** {lider_nombre} - *{empresa_nombre}* | {puntos_2025} pts | 2024: #{pos_2024} {indicador}\n\n"
            else:
                resultado += f"**{pos_2025}.** {lider_nombre} - *{empresa_nombre}* | {puntos_2025} pts | **NUEVO** ⭐\n\n"
    
    conclusion = """

---

### ¿Está listo para elevar su estrategia de gestión de la reputación al próximo nivel?

Esto es solo el principio, ya que en GlobalNews Group Colombia ofrecemos una variedad de herramientas avanzadas para fortalecer su capacidad de monitoreo de noticias, ya sea en medios tradicionales o en plataformas de redes sociales. 

**¡Descubra cómo podemos ayudarle a medir, gestionar y mejorar su reputación empresarial de manera efectiva y precisa!**
"""
    
    return intro + resultado + conclusion

# Interfaz principal
st.title("🏆 Ranking MERCO - Análisis Comparativo 2024-2025")

# Sidebar para opciones
with st.sidebar:
    st.header("⚙️ Configuración")
    
    ranking_type = st.selectbox(
        "Tipo de Ranking:",
        ["Líderes", "Empresas", "Talento", "Sectores"]
    )
    
    st.markdown("---")
    st.markdown("### 📁 Fuente de Datos")
    
    fuente_datos = st.radio(
        "Seleccione la fuente:",
        ["Archivos del Repositorio", "Cargar Archivos Manualmente"]
    )
    
    df_2025 = None
    df_2024 = None
    
    if fuente_datos == "Archivos del Repositorio":
        st.info("📂 Estructura esperada:\n`data/merco_lideres_2025.txt`\n`data/merco_lideres_2024.txt`")
        
        if st.button("🔄 Cargar Datos del Repo"):
            with st.spinner('Cargando datos...'):
                df_2025 = cargar_datos_repo("2025", ranking_type)
                df_2024 = cargar_datos_repo("2024", ranking_type)
                
                if df_2025 is not None:
                    st.success(f"✅ 2025: {len(df_2025)} registros")
                    st.session_state.df_2025 = df_2025
                else:
                    st.warning("⚠️ No se encontró archivo 2025")
                
                if df_2024 is not None:
                    st.success(f"✅ 2024: {len(df_2024)} registros")
                    st.session_state.df_2024 = df_2024
                else:
                    st.warning("⚠️ No se encontró archivo 2024")
    
    else:
        st.markdown("#### Año 2025")
        file_2025 = st.file_uploader("Archivo TXT 2025", type=['txt'], key="2025")
        
        st.markdown("#### Año 2024")
        file_2024 = st.file_uploader("Archivo TXT 2024 (opcional)", type=['txt'], key="2024")
        
        if file_2025:
            txt_2025 = file_2025.read().decode('utf-8')
            df_2025 = parse_merco_data(txt_2025)
            st.session_state.df_2025 = df_2025
            st.success(f"✅ 2025: {len(df_2025)} registros")
        
        if file_2024:
            txt_2024 = file_2024.read().decode('utf-8')
            df_2024 = parse_merco_data(txt_2024)
            st.session_state.df_2024 = df_2024
            st.success(f"✅ 2024: {len(df_2024)} registros")

# Recuperar datos de session_state
if 'df_2025' in st.session_state:
    df_2025 = st.session_state.df_2025
if 'df_2024' in st.session_state:
    df_2024 = st.session_state.df_2024

# Contenido principal
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🔍 Búsqueda de Empresa")
    empresa_buscar = st.text_input("Nombre de la empresa o líder:", "")
    
    if df_2025 is not None and empresa_buscar:
        if st.button("📊 Generar Informe Comparativo", type="primary"):
            st.session_state.informe_generado = True
            st.session_state.informe_texto = generar_informe(
                empresa_buscar, 
                ranking_type, 
                df_2025, 
                df_2024
            )
    
    # Mostrar estadísticas
    if df_2025 is not None:
        st.markdown("---")
        st.markdown("### 📊 Estadísticas")
        st.metric("Total Empresas 2025", len(df_2025))
        if df_2024 is not None:
            st.metric("Total Empresas 2024", len(df_2024))

with col2:
    st.subheader("📄 Informe Comparativo Generado")
    
    if 'informe_generado' in st.session_state and st.session_state.informe_generado:
        st.markdown(st.session_state.informe_texto)
        
        # Botón de descarga
        st.download_button(
            label="💾 Descargar Informe",
            data=st.session_state.informe_texto,
            file_name=f"informe_merco_{empresa_buscar.replace(' ', '_')}_{ranking_type}_2024_2025.md",
            mime="text/markdown"
        )
    else:
        st.info("👈 Carga los datos y busca una empresa para generar el informe comparativo")

# Mostrar vista previa de datos
if df_2025 is not None:
    with st.expander("📋 Ver datos 2025"):
        st.dataframe(df_2025, use_container_width=True)

if df_2024 is not None:
    with st.expander("📋 Ver datos 2024"):
        st.dataframe(df_2024, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Desarrollado para GlobalNews Group Colombia | Ranking MERCO 2024-2025</p>
</div>
""", unsafe_allow_html=True)
