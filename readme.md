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
*   **Informe Completo para Copiar:** Al final de los resultados, un botón grande y visible copia el informe completo (introducción, resultados, tablas y cierre); debajo queda el mismo texto plano en un bloque como respaldo.
*   **Clientes Frecuentes:** Un selector con los clientes habituales (lista en [`data/clientes_merco.csv`](data/clientes_merco.csv)) ejecuta el informe con un clic. Las variantes ", Competencia(s)" buscan por el nombre base.
*   **Merco Sectores 2026 cuando la marca no sale:** Si la marca no figura en Merco Sectores 2026, la app muestra (y agrega al informe) la tabla 2026 de su sector: una universidad ve el ranking de **EDUCACIÓN-UNIVERSIDADES**, una EPS el de **SALUD**, una aseguradora el de **ASEGURADORAS**, etc. El sector se elige en este orden: 1) el asignado al cliente en `data/clientes_merco.csv`; 2) el sector en el que la marca figuró en 2025 o 2024; 3) el inferido por el nombre (universidad, clínica, banco, seguros...).
*   **Texto y tablas copiables, sin fondo:** Las tarjetas, chips y tablas no tienen fondo y todo el texto se puede seleccionar. Las tablas son HTML (no una grilla), así que se copian con el mouse. El botón "Copiar el informe completo" copia el informe (solo texto, sin tablas) con negritas en formato enriquecido transparente (para Word, correo o PowerPoint) y también en texto plano.
*   **Trayectoria en Merco:** Cuando la marca figura en al menos un ranking, una tabla resumen muestra una fila por ranking (Empresas, Talento, Líderes, Sectores) y su puesto en 2024, 2025 y 2026 ("—" si no figuró). En Líderes se nombra a la persona que obtuvo cada puesto. Se puede copiar como imagen PNG aparte.
*   **Tablas lado a lado y como imagen:** En toda búsqueda se muestran dos tablas, una al lado de la otra: Merco Sectores 2026 del sector de la marca y el Top 10 de Merco Empresas 2026. Si la marca figura en ellas aparece resaltada. El botón "Copiar tablas como imagen" las copia al portapapeles como PNG transparente en horizontal, con el estilo de la app (también se puede descargar el PNG).
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
│   ├── clientes_merco.csv      # listado de clientes y su sector Merco
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

## 👥 Listado de clientes

Los clientes que usa la app están en [`data/clientes_merco.csv`](data/clientes_merco.csv), con dos columnas:

| Columna | Contenido |
|---|---|
| `cliente` | Nombre del cliente tal como aparece en el selector (el orden del archivo es el orden del selector). |
| `sector_merco` | Sector de Merco Sectores 2026 que se muestra cuando la marca no figura en ese ranking. Debe escribirse igual que en Merco (ej. `EDUCACIÓN-UNIVERSIDADES`, `SALUD`, `FINANCIERO`); si contiene comas va entre comillas. |

Para agregar un cliente basta con añadir una fila al CSV (se puede editar en Excel o directamente en GitHub).

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
