# 📊 Generador de Informes de Reputación - Ranking Merco

Esta aplicación web, desarrollada con Streamlit, automatiza la creación de informes de reputación basados en los prestigiosos rankings Merco. Permite a los usuarios consultar rápidamente la posición de cualquier empresa en Colombia para los años 2024 y 2025, generando un texto comparativo listo para ser utilizado en reportes, correos electrónicos o presentaciones.

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
*   **Análisis Comparativo Automático:** En lugar de solo mostrar dos números, el informe describe el cambio de un año a otro con frases como:
    *   `un notable avance` (si sube más de 15 puestos)
    *   `un avance` (si sube entre 1 y 15 puestos)
    *   `un retroceso` (si baja más de 10 puestos)
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
│   ├── merco_lideres_2024.txt
│   ├── merco_lideres_2025.txt
│   ├── merco_sectores_2024.txt
│   ├── merco_sectores_2025.txt
│   ├── merco_talento_2024.txt
│   └── merco_talento_2025.txt
├── app.py
└── requirements.txt
```

---

## ⚙️ Cómo Funciona

La aplicación sigue un enfoque de **Recuperación y Generación Aumentada (RAG)**:

1.  **Recuperación (Retrieval):** Cuando un usuario ingresa un nombre de empresa, la aplicación lo "normaliza" (limpia, convierte a minúsculas, etc.). Luego, busca este nombre normalizado en los archivos de datos `.txt`, que han sido previamente parseados y normalizados.
2.  **Generación Aumentada (Augmented Generation):** Una vez que se recuperan los datos (posición actual, posición anterior, nombre del ranking, etc.), estos se inyectan en plantillas de texto predefinidas para generar un informe coherente y bien redactado.

Si no se encuentra ninguna coincidencia para el año 2025, la aplicación informa al usuario y, como recurso útil, muestra el Top 10 del ranking general `Merco Empresas`.

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
