# 📊 Generador de Informes de Reputación - Ranking Merco

Esta aplicación web, desarrollada con Streamlit, automatiza la creación de informes de reputación basados en los prestigiosos rankings Merco. Permite a los usuarios consultar rápidamente la posición de cualquier empresa en Colombia para los años 2024, 2025 y 2026, generando un texto comparativo con la trayectoria de los tres años, listo para ser utilizado en reportes, correos electrónicos o presentaciones.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ranking-merco.streamlit.app/)  <!-- Reemplaza con la URL de tu app desplegada -->

<img width="1789" height="814" alt="image" src="https://github.com/user-attachments/assets/71e1aa48-bc73-4e59-bcfe-6be46e2553d7" />



## 🚀 Ventajas Clave

Esta herramienta fue diseñada para ser rápida, precisa y fácil de usar, superando los desafíos comunes al trabajar con datos de múltiples fuentes.

###  Búsqueda Inteligente y Flexible

El corazón de la aplicación es su **motor de búsqueda normalizado**, que garantiza encontrar la empresa correcta sin importar cómo se escriba:

*   **Insensible a Mayúsculas y Minúsculas:** Buscar `epm` encuentra `EPM`.
*   **Ignora Tildes y Caracteres Especiales:** Una búsqueda de `Crepes & Waffles` o `crepes y waffles` funciona perfectamente.
*   **Elimina "Ruido" Corporativo:** La búsqueda entiende que `Grupo Nutresa` y `Nutresa` son la misma entidad, ignorando palabras como "Grupo", "Organización", "S.A.S.", etc.
*   **Manejo de Abreviaturas:** Funciona con nombres cortos (ej. `Bancolombia`) y nombres largos (`Banco de Colombia`).

### Generación de Texto Dinámico y Contextual

La aplicación no solo recupera datos, sino que los presenta en un formato narrativo coherente y profesional.

*   **Redacción Variada:** Utiliza diferentes frases de apertura para evitar la monotonía en los informes.
*   **Análisis Comparativo Automático a Tres Años, sin juicios de valor:** El informe presenta las posiciones 2024 → 2025 → 2026 y los cambios solo en cifras (`subió 6 puestos frente a 2025`, `se mantuvo en el mismo puesto`), sin calificativos. Contempla todos los casos: si la empresa no tuvo datos en 2025 compara 2024 con 2026, si no apareció en 2026 lo indica con su historial, si no figuró en 2025 ni en 2024 lo señala, y si no estuvo en 2024 también lo dice.
*   **Informe Completo para Copiar:** Al final de los resultados, un botón grande y visible copia el informe completo (introducción, resultados y cierre, en texto plano); debajo queda el mismo texto en un bloque como respaldo.
*   **Sector Probable Inteligente:** Si la empresa no tiene datos en el ranking sectorial (o no aparece en ningún ranking), la app infiere su sector por el nombre (ej. una universidad → Educación-Universidades, una clínica → Salud, un banco → Financiero) y muestra la tabla 2026 de ese sector: junto al Top 10 general cuando no hay ningún dato, o como sección propia cuando sí hay resultados en otros rankings.
*   **Interfaz Moderna:** Tema claro, resultados en tarjetas por ranking y tipografía amplia y legible.
*   **Redacción Adaptativa:** El formato del texto cambia automáticamente si el resultado pertenece al ranking de **Merco Líderes**, enfocándose en la persona y su empresa.

### Eficiencia y Rendimiento

*   **Carga Perezosa (Lazy Loading):** La aplicación se inicia casi instantáneamente porque los datos solo se cargan cuando se realiza una búsqueda, optimizando el uso de memoria.
*   **Caché Inteligente:** Los archivos de datos se procesan una sola vez por sesión, haciendo que las búsquedas sucesivas sean inmediatas.

---

## 🛠️ Estructura del Proyecto

El repositorio está organizado de la siguiente manera para un despliegue sencillo en Streamlit Cloud:

```
.
├── data/
│   ├── merco_empresas_2024.txt
│   ├── merco_empresas_2025.txt
│   ├── merco_empresas_2026.txt
│   ├── merco_lideres_2024.txt
│   ├── merco_lideres_2025.txt
│   ├── merco_lideres_2026.txt
│   ├── merco_sectores_2024.txt
│   ├── merco_sectores_2025.txt
│   ├── merco_sectores_2026.txt
│   ├── merco_talento_2024.txt
│   ├── merco_talento_2025.txt
│   └── merco_talento_2026.txt
├── app.py
└── requirements.txt
```

---

## ⚙️ Cómo Funciona

La aplicación sigue un enfoque de **Recuperación y Generación Aumentada (RAG)**:

1.  **Recuperación (Retrieval):** Cuando un usuario ingresa un nombre de empresa, la aplicación lo "normaliza" (limpia, convierte a minúsculas, etc.). Luego, busca este nombre normalizado en los archivos de datos `.txt`, que han sido previamente parseados y normalizados.
2.  **Generación Aumentada (Augmented Generation):** Una vez que se recuperan los datos (posición actual, posición anterior, nombre del ranking, etc.), estos se inyectan en plantillas de texto predefinidas para generar un informe coherente y bien redactado.

Si no se encuentra ninguna coincidencia para el año 2026, la aplicación informa al usuario y, como recurso útil, muestra el Top 10 del ranking general `Merco Empresas`.

---

## 💻 Instalación y Uso Local

Para ejecutar esta aplicación en tu máquina local:

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/tu-usuario/tu-repositorio.git
    cd tu-repositorio
    ```

2.  **Crea un entorno virtual (recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Ejecuta la aplicación:**
    ```bash
    streamlit run app.py
    ```

---

## 📜 Créditos

Esta aplicación fue creada con 🤖 por **Johnathan Cortés**.
