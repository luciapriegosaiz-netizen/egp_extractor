# Extractor de proyectos SAS Enterprise Guide (`extract_egp`)

Herramienta de línea de comandos que convierte un proyecto SAS Enterprise Guide
(`.egp`) en una colección de archivos `.txt` organizados por flujo, listos para
servir como entrada a generadores de notebooks Python (CP4D / Watson Studio).

Cada `.txt` contiene el código SAS y el log de ejecución de cada nodo intercalados,
en **orden de ejecución real** (ordenación topológica), y con un header
estandarizado que permite a las herramientas downstream parsear el contenido sin
ambigüedad.

> **Sin instalaciones extra. Sin credenciales. Solo Python 3.7+** (el `.bat`
> wrapper localiza Python automáticamente en Windows).

---

## Índice

1. [Archivos del toolkit](#1-archivos-del-toolkit)
2. [Instalación y requisitos](#2-instalación-y-requisitos)
3. [Uso rápido](#3-uso-rápido)
4. [Opciones de línea de comandos](#4-opciones-de-línea-de-comandos)
5. [Estructura de la salida](#5-estructura-de-la-salida)
6. [Lógica interna del extractor](#6-lógica-interna-del-extractor)
7. [Archivos JSON generados](#7-archivos-json-generados)
8. [Casos especiales y notas técnicas](#8-casos-especiales-y-notas-técnicas)
9. [Diagnóstico de errores](#9-diagnóstico-de-errores)
10. [Pipeline de migración](#10-pipeline-de-migración)

---

## 1. Archivos del toolkit

| Archivo | Función |
|---|---|
| `extract_egp.bat` | Wrapper Windows. Permite drag & drop, doble clic o invocación CLI. Localiza Python automáticamente. |
| `extract_egp.py` | Script principal. Toda la lógica de extracción y análisis. |
| `README_extractor.md` | Este documento. |

Los tres archivos deben estar en la **misma carpeta** para que el `.bat` encuentre
el `.py`. El script funciona también de forma independiente sin el `.bat`
(ver sección 4).

---

## 2. Instalación y requisitos

### Requisitos

- **Sistema operativo**: Windows 10/11 (para el `.bat`) o cualquier OS con Python (para el `.py`).
- **Python 3.7 o superior**. Solo se usan módulos de la librería estándar (`re`, `json`, `zipfile`, `shutil`, `argparse`, `html`, `collections`, `pathlib`).
- **Sin dependencias externas**. No requiere `pip install` nada.

### Instalación

1. Copia los tres archivos (`extract_egp.bat`, `extract_egp.py`, `README_extractor.md`) a una carpeta accesible (por ejemplo `C:\Tools\egp_extractor\`).
2. Verifica que Python está instalado:
   ```cmd
   python --version
   ```
   Si Python no se encuentra, el `.bat` también prueba con `py`, `python3`, y rutas típicas de instalación (`C:\Python311\python.exe`, etc.). Si ninguna funciona, instala Python desde [python.org](https://www.python.org/downloads/) marcando "Add Python to PATH".

---

## 3. Uso rápido

### Drag & drop (lo más cómodo)

Arrastra cualquier `.egp` o `.zip` sobre `extract_egp.bat`. Genera los `.txt` sin
logs en `<carpeta_del_egp>\<nombre>_extracted\flujos_extraidos\`.

### Doble clic

Doble clic sobre `extract_egp.bat`. Te pedirá la ruta del `.egp` por consola.

### Con logs (recomendado para migración)

```cmd
extract_egp.bat "C:\proyectos\MiProyecto.egp" --logs
```

### Carpeta personalizada de salida

```cmd
extract_egp.bat "C:\proyectos\MiProyecto.egp" --output "C:\salida" --logs
```

### Carpeta ya descomprimida

Si ya has extraído manualmente el `.egp` (o un `.zip` equivalente):

```cmd
extract_egp.bat "C:\proyectos\MiProyecto_extracted" --logs
```

El script detecta que es una carpeta y omite la descompresión.

---

## 4. Opciones de línea de comandos

Invocación directa del `.py` (útil en macOS/Linux o desde scripts):

```bash
python extract_egp.py <input> [--output OUTPUT] [--logs]
```

| Argumento | Descripción |
|---|---|
| `input` | Ruta al `.egp`, `.zip`, o carpeta ya descomprimida. **Obligatorio.** |
| `--output`, `-o` | Carpeta de salida. Por defecto: `<input>_extracted/flujos_extraidos/`. |
| `--logs`, `-l` | Incluye el log de ejecución de cada nodo junto al código. Sin esta opción solo se extrae el código SAS. |

### ¿Cuándo usar `--logs`?

**Recomendado siempre que sea posible**. Los logs aportan información clave para
las herramientas downstream:

- **Recuentos de filas reales** (`NOTE: Table WORK.X created, with 12345 rows...`) que sirven como referencias de validación.
- **Outputs de `ImportTask`**: el código de un nodo `ImportTask` no contiene `CREATE TABLE` — el nombre de la tabla solo aparece en el log. Sin `--logs`, el sort topológico no puede detectar estas dependencias y trabaja en modo "mejor esfuerzo".

Sin `--logs` el extractor sigue funcionando correctamente, pero las dependencias
detectadas son aproximadas en los flujos que usan `ImportTask`.

---

## 5. Estructura de la salida

Para un proyecto con N flujos, se genera en `<input>_extracted\flujos_extraidos\`:

```
flujos_extraidos/
├── flujo00_Identificacion_cohorte.txt
├── flujo01_Medidas_SIA.txt
├── flujo02_Preparacion_cohorte_final.txt
├── flujo03_SIA.txt
├── ...
├── flujo12_Hemorragias.txt
├── _summary.json
└── _dependencias_globales.json
```

### Nombres de archivo

Cada `.txt` recibe un prefijo `flujoNN_` con **zero-padding a dos dígitos**.
Esto garantiza:

1. Que el orden alfabético de los archivos en el explorador coincide con el orden de ejecución.
2. Que `flujo10_X` aparece después de `flujo09_X` (sin padding, los sorts textuales colocarían `flujo10` antes de `flujo2`).

El número refleja el **orden del árbol del proyecto en SAS EG**, no el orden alfabético
ni el orden interno del XML (que es el de creación, no el de ejecución).

### Estructura interna de cada `.txt`

```
/* ========================================================
   Flujo      : 5.Farmacia_Receta
   Container  : ProcessFlowContainer-I7DQjnqCYTXYdXGp
   Nodos      : 20
   Orden      : topologico-dfs (reordenado desde XML)
   Orden_XML  : ImportTask-WFj... -> Query-fxc... -> ...
   ======================================================== */


/* ========== NODO 1: Código  [ImportTask-WFjWkHBxMx9sywto]  ========== */

/* --- CÓDIGO --- */

DATA WORK.HIPOLIPEMIANTES_TRAT_0000;
    LENGTH CODPRINATC $ 7 ...

/* --- LOG --- */

NOTE: Table WORK.HIPOLIPEMIANTES_TRAT_0000 created, with 37 rows and 12 columns.


/* ========== NODO 2: Query_ver_edispensacion  [Query-FC2IkerHgHfsfmD2]  ========== */

/* --- CÓDIGO --- */

PROC SQL;
CREATE TABLE WORK.QUERY_FOR_VER_EDISPENSACION AS SELECT ...

/* --- LOG --- */

NOTE: Table WORK.QUERY_FOR_VER_EDISPENSACION created, with 248990 rows and 6 columns.
```

### Campos del header

| Campo | Significado |
|---|---|
| `Flujo` | Nombre del flujo tal como aparece en el árbol de SAS EG. |
| `Container` | Identificador interno del flujo en `project.xml` (referencia para debug). |
| `Nodos` | Número total de nodos del flujo con código. |
| `Orden` | `topologico-dfs (reordenado desde XML)` si el orden XML no coincidía con el de ejecución. `XML (coincide con dependencias)` si ya estaba correcto. |
| `Orden_XML` | Solo aparece si hubo reordenación. Lista los primeros 8 task_ids en orden XML original para auditar la transformación. |

### Cuando un nodo no tiene log

Si el nodo no se ejecutó o se pasó sin `--logs`, en lugar del bloque `LOG` aparece:

```
/* --- LOG: no encontrado para Query-XXX --- */
```

Esto no es un error — solo indica ausencia de log para ese nodo concreto.

---

## 6. Lógica interna del extractor

El `.egp` de SAS Enterprise Guide es un archivo `.zip` con una estructura
interna específica. El script realiza los siguientes pasos:

### Paso 1 — Descompresión

Si la entrada es `.egp` o `.zip`, se descomprime a `<nombre>_extracted/`. Para
`.egp` se hace una copia temporal como `.zip` (mismo formato, distinto nombre)
porque `zipfile` de Python espera la extensión `.zip`. Si la carpeta ya existe,
se omite la descompresión.

### Paso 2 — Lectura de `project.xml`

`project.xml` es el manifiesto del proyecto. Está en UTF-16 con BOM por defecto,
pero el script prueba secuencialmente UTF-16, UTF-16-LE, UTF-16-BE, UTF-8-SIG y
UTF-8 para tolerar variaciones entre versiones de SAS EG.

### Paso 3 — Detección de flujos

Cada flujo es un elemento del tipo `SAS.EG.ProjectElements.ProcessFlowContainer`
con un `<Label>` (nombre visible) y un `<ID>` (clave interna).

### Paso 4 — Orden de los flujos

Para conservar el orden del árbol que el usuario ve en SAS EG:

1. **Fuente primaria**: la sección `<Containers>` del XML contiene la lista
   ordenada de IDs de flujo tal como aparecen en el panel de proyecto. El script
   construye un mapa `{container_id: posición}` desde esta lista.
2. **Fallback**: si no existe esa sección, se aplica un *natural sort* sobre el
   nombre del flujo. Esto extrae el número inicial para que `0 < 1 < ... < 9 < 10 < 11`
   en vez del orden alfabético textual donde `"10" < "2"`. Soporta sufijos de
   letra: `3a` se ordena entre `3` y `4`.

### Paso 5 — Construcción del mapa `task_id → flujo`

Cada nodo de un flujo es una tarea ejecutable (`Query`, `CodeTask`, `AppendTask`,
`ImportTask`) con un `task_id` único. El mapa se construye desde dos fuentes:

| Fuente XML | Cubre |
|---|---|
| `Code` elements con `<InputIDs>` | Query, AppendTask, ImportTask (~159 tareas en SCA) |
| `Log` elements con `<InputIDs>` | CodeTask sin Code wrapper (~14 tareas adicionales) |

### Paso 6 — Extracción del código SAS

El código SAS se extrae de:

1. El XML, dentro de `<TaskCode>` (o `<Text>` como fallback). El contenido se
   procesa con `html.unescape()` para decodificar entidades HTML (`&amp;` →
   `&`, `&lt;` → `<`, etc.). Esto es crítico para los nodos que usan macro
   variables SAS como `&codes_column.`, que vendrían codificadas como
   `&amp;codes_column.` y romperían la sintaxis SAS.
2. Para los `CodeTask` cuyo código no está embebido en el XML, se busca el
   archivo `.sas` físico en la subcarpeta `<task_id>/` del proyecto.

### Paso 7 — Localización de logs (solo con `--logs`)

Cada tarea ejecutada genera una subcarpeta `<task_id>/result.log`. El script
construye un índice `{task_id: Path}` recorriendo las subcarpetas del proyecto.

### Paso 8 — Sort topológico de nodos dentro de cada flujo

El orden de los nodos en `project.xml` es el orden de **creación** en SAS EG, no
el de **ejecución**. Para que los `.txt` salgan en orden ejecutable:

1. **Detección de outputs** (función `extraer_tablas_salida_nodo`):
   - `PROC SQL: CREATE TABLE WORK.X AS`
   - `DATA WORK.X;`
   - `PROC SORT OUT=WORK.X` (también con `PROC IMPORT`)
   - `PROC SORT DATA=WORK.X` sin `OUT=` (modifica in-place)
   - `PROC APPEND BASE=WORK.X`
   - **LOG**: `NOTE: Table WORK.X created` (esencial para `ImportTask`, cuyo output **no** aparece en el código)

2. **Detección de inputs** (función `extraer_tablas_consumidas_nodo`):
   - Cualquier referencia a `WORK.X` en el código
   - `SET`, `MERGE`, `UPDATE` con o sin prefijo `WORK.`

3. **Construcción del grafo y sort DFS post-order**:
   - Si el nodo A produce `WORK.X` y el nodo B consume `WORK.X`, arco A → B.
   - Se aplica DFS post-order iterando en orden SAS original como tiebreak.
   - **Por qué DFS y no BFS**: BFS interleava cadenas paralelas; DFS mantiene
     bloques contiguos. Si un flujo tiene dos cadenas independientes que
     convergen en un nodo final, DFS escribe primero una cadena completa, luego
     la otra, luego la convergencia. Es mucho más legible en el `.txt` resultante.

### Paso 9 — Escritura de archivos `.txt`

Un único `.txt` por flujo con el header descrito en la sección 5 y los nodos
intercalados (código + log opcional).

### Paso 10 — Generación de los JSON de metadata

Ver sección siguiente.

---

## 7. Archivos JSON generados

Junto a los `.txt` se generan dos JSON con metadata estructurada:

### `_summary.json`

Inventario simple por flujo:

```json
[
  {
    "flujo"  : "0.Identificacion_cohorte",
    "nodos"  : 27,
    "con_log": 27
  },
  ...
]
```

### `_dependencias_globales.json`

Pre-cálculo de qué tablas WORK debe guardar cada flujo como CSV. Permite que
herramientas downstream (como un generador de notebooks) sepan inmediatamente
qué outputs son finales sin tener que releer todos los `.txt`.

```json
{
  "0": {
    "nombre"    : "0.Identificacion_cohorte",
    "a_guardar" : ["DIAGNOSTICOS_FINAL", "DIAG_TOTAL", "PACIENTES_SCAPREV"],
    "hojas"     : ["DIAGNOSTICOS_FINAL"],
    "promovidas": ["DIAG_TOTAL", "PACIENTES_SCAPREV"]
  },
  "2": {
    "nombre"    : "2.Preparacion_cohorte_final",
    "a_guardar" : ["EXITUS_SCA", "PACIENTES_SCA"],
    "hojas"     : [],
    "promovidas": ["EXITUS_SCA", "PACIENTES_SCA"]
  }
}
```

| Campo | Significado |
|---|---|
| `a_guardar` | Unión de `hojas` ∪ `promovidas`. Tablas que el flujo debe guardar como CSV. |
| `hojas` | Tablas producidas en este flujo que **ningún nodo del mismo flujo** consume — son los outputs finales del flujo. |
| `promovidas` | Tablas intermedias (producidas y consumidas dentro del mismo flujo) que **algún flujo posterior** necesita como input. Se guardan para que el flujo siguiente las pueda cargar. |

Las listas vienen en MAYÚSCULAS y ordenadas alfabéticamente.

> **Limitación sin `--logs`**: los outputs de `ImportTask` no se detectan en el
> código SAS (no usan `CREATE TABLE`). Sus tablas no aparecen en `a_guardar`.
> Si tu proyecto usa `ImportTask` para pasar datos entre flujos, ejecuta
> con `--logs` para que la detección sea exacta.

---

## 8. Casos especiales y notas técnicas

### Proyectos sin flujos numerados

Si los flujos no tienen prefijo numérico en el nombre (p. ej. `Identificación MM`,
`Fármacos`), el extractor usa la sección `<Containers>` del XML para conocer el
orden del árbol SAS EG. **No es necesario renombrar los flujos a mano**.

### `PROC SORT` in-place

```sas
PROC SORT DATA=WORK.MM NODUPKEY; BY sip; RUN;
```

El nodo aparece como **productor y consumidor** de `MM` a la vez. El sort
topológico detecta esta auto-referencia y la excluye del grafo (`j != i`).
El nodo se coloca según su orden SAS original entre los demás nodos.

### `PROC APPEND`

```sas
PROC APPEND BASE=WORK.RESULTADO DATA=WORK.NUEVOS;
```

- `BASE` → tabla modificada/producida.
- `DATA` → tabla consumida.

El nodo se coloca después del nodo que produce `NUEVOS`.

### `ImportTask`

El código SAS de un `ImportTask` no contiene `CREATE TABLE`. El nombre real de
la tabla solo aparece en el log:

```
NOTE: The data set WORK.DATOS_IMPORTADOS has 1234 observations and 5 variables.
```

Por eso `extraer_tablas_salida_nodo` también escanea el log cuando se le pasa.
**Requiere `--logs`** para detección exacta.

### Entidades HTML en el código SAS

El XML codifica caracteres especiales (`&`, `<`, `>`, `"`) como entidades HTML
(`&amp;`, `&lt;`, etc.). Esto afectaba especialmente a las macros SAS que usan
`&` para referenciar variables (`&codes_column.`). El extractor aplica
`html.unescape()` antes de devolver el código.

### Ciclos en el grafo (raro)

Si por algún motivo hay un ciclo de dependencias, los nodos del ciclo se añaden
al final en el orden en que el DFS los encuentre. El header del `.txt` muestra
el orden detectado para auditar.

### Versiones de SAS EG soportadas

Probado y verificado contra **SAS Enterprise Guide 8.x** (EGVersion="8.2") en el
IIS La Fe. Para versiones anteriores la estructura del XML puede diferir; si
falla, compartir un fragmento del `project.xml` para adaptar el parser.

---

## 9. Diagnóstico de errores

### "No se encuentra project.xml"

El `.egp` no se descomprimió correctamente o tiene una estructura inesperada.
Verifica que el archivo no esté corrupto abriéndolo en SAS EG.

### "No se encontraron flujos en project.xml"

La estructura `ProcessFlowContainer` no se localizó. Probable versión muy
antigua de SAS EG. Comparte un fragmento del XML para diagnosticar.

### "Python no encontrado en el PATH"

El `.bat` no localizó Python. Instala desde python.org marcando "Add Python to
PATH", o ejecuta el `.py` directamente con la ruta absoluta de Python.

### El sort topológico no parece correcto

- Verifica que ejecutaste con `--logs` si el flujo usa `ImportTask`.
- El header del `.txt` muestra el orden XML original (`Orden_XML`) para
  comparar con el orden actual.
- Si dos nodos no tienen dependencia entre sí (cadenas paralelas), el orden
  relativo se determina por el índice original SAS. Esto es esperado.

### Los `.txt` tienen `&amp;` o `&lt;` en el código

No debería ocurrir con la versión actual (el fix de `html.unescape` está
integrado). Si aparece, verifica que estás usando la última versión del `.py`.

---

## 10. Pipeline de migración

El extractor es el primer paso de un pipeline más amplio:

```
┌─────────────────────────┐
│  proyecto.egp           │  ← input
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  extract_egp.bat        │  ← este toolkit
│  --logs                 │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  flujos_extraidos/      │
│    flujo00_X.txt        │  ← código SAS + logs por flujo
│    flujo01_X.txt        │     (orden ejecución, entidades decodificadas)
│    ...                  │
│    _summary.json        │  ← inventario por flujo
│    _dependencias_       │  ← qué tablas guardar por flujo
│    globales.json        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  generate_notebook.py   │  ← genera notebooks CP4D
│  (script separado)      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  flujo00_X.ipynb        │  ← input para subir a CP4D
│  flujo01_X.ipynb        │
│  ...                    │
└─────────────────────────┘
```

Los pasos 1-2 son automatizables. Los siguientes pasos (subir a CP4D, revisar
SQL Presto, ajustar queries, validar contra referencias SAS) requieren criterio
humano y no se pueden eliminar sin sacrificar la calidad de la migración.
MDEOF
