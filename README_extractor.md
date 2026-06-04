# Extractor SAS EG — Guía de uso

Convierte cualquier proyecto SAS Enterprise Guide (`.egp`) en archivos `.txt`
organizados por flujo y ordenados en orden de ejecución real. Cada archivo
contiene el código SAS y el log de cada nodo intercalados, listos para usarse
como entrada al generador de notebooks CP4D.

**Sin instalaciones extra. Sin credenciales. Solo Python (ya disponible con CP4D).**

---

## Archivos del toolkit

| Archivo | Función |
|---|---|
| `extract_egp.bat` | Entry point — drag & drop o doble clic |
| `extract_egp.py` | Lógica de extracción (no editar) |
| `README_extractor.md` | Este documento |

Los tres archivos deben estar en la **misma carpeta**.

---

## Uso

### Opción A — Drag & drop (lo más rápido)
Arrastra el `.egp` directamente sobre `extract_egp.bat`. Solo código, sin logs.

### Opción B — Doble clic
Doble clic sobre `extract_egp.bat` y pega la ruta cuando la pida.

### Opción C — Línea de comandos, solo código
```cmd
extract_egp.bat "C:\proyectos\MiProyecto.egp"
```

### Opción D — Con logs incluidos (recomendado para migración)
```cmd
extract_egp.bat "C:\proyectos\MiProyecto.egp" --logs
```

### Opción E — Carpeta ya descomprimida
```cmd
extract_egp.bat "C:\proyectos\MiProyecto_extracted" --logs
```

### Opción F — Carpeta de salida personalizada
```cmd
extract_egp.bat "C:\proyectos\MiProyecto.egp" --output "C:\salida" --logs
```

---

## Qué produce

Un único `.txt` por flujo en `<input>_extracted\flujos_extraidos\`, nombrado con
prefijo numérico con zero-padding para garantizar ordenación correcta en cualquier
explorador de archivos o herramienta de línea de comandos:

```
flujos_extraidos\
├── flujo00_Identificacion_cohorte.txt
├── flujo01_Medidas_SIA.txt
├── flujo02_Preparacion_cohorte_final.txt
├── flujo03_SIA.txt
├── flujo04_Interconsultas_AP.txt
├── ...
├── flujo12_Hemorragias.txt
└── _summary.json
```

El número del prefijo refleja el **orden real del árbol del proyecto en SAS EG**,
no el orden alfabético ni el orden interno del XML. Los flujos sin prefijo numérico
en el nombre se ordenan según el árbol de SAS EG igualmente.

### Estructura interna de cada `.txt`

Código y log de cada nodo van juntos, en **orden de ejecución real** (topológico):

```
/* ========================================================
   Flujo      : 5.Farmacia_Receta
   Container  : ProcessFlowContainer-I7DQjnqCYTXYdXGp
   Nodos      : 20
   Ordenacion : topologica (orden de ejecucion SAS)
   ======================================================== */


/* NOTA: Nodos reordenados por dependencias de datos
   Orden original (XML) : ['ImportTask-WFj...', 'Query-fxc...', ...]
   Orden ejecucion      : ['ImportTask-WFj...', 'Query-buY...', ...]
   */


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

La nota de reordenación solo aparece cuando el script detecta que el orden XML
difería del orden de ejecución. Si el orden ya era correcto, no se escribe.

Si un nodo no tiene log (no ejecutado, o sin `--logs`):
```
/* --- LOG: no encontrado para Query-XXX --- */
```

---

## Cómo funciona internamente

El `.egp` es un `.zip` disfrazado. Contiene un `project.xml` (UTF-16) con todo
el código embebido y ~370 subcarpetas con los logs de ejecución. El script:

1. **Descomprime** el `.egp` a `<nombre>_extracted/`
2. **Lee** `project.xml` detectando la codificación automáticamente
3. **Ordena los flujos** según el árbol real del proyecto SAS EG, extraído de la
   sección `<Containers>` del XML (la misma secuencia que ve el usuario en el panel
   de SAS EG). Fallback a natural sort numérico por nombre si esa sección no existe.
4. **Construye** el mapa `ShortCutToData-ID → task_id_productor` para toda la
   estructura de dependencias del proyecto (una sola pasada por el XML).
5. **Construye** el mapa `task_id → flujo` desde dos fuentes:
   - `Code` elements (`<InputIDs>`) → cubre Query, AppendTask, ImportTask
   - `Log` elements (`<InputIDs>`) → cubre CodeTask sin Code wrapper
6. **Extrae** el código SAS de `<TaskCode>` para cada nodo; para CodeTask busca
   también el `.sas` físico en su subcarpeta dentro del zip.
7. **Ordena los nodos** de cada flujo en orden de ejecución correcto mediante sort
   topológico (algoritmo de Kahn) usando el grafo de dependencias explícito del XML:
   - Cada tarea declara sus datos de entrada como `ShortCutToData-XXX` en `<InputIDs>`
   - Cada `ShortCutToData` apunta a la tarea que lo produjo (su `<InputIDs>`)
   - Si la tarea B consume datos producidos por la tarea A, A → B en el grafo
   - Los empates (nodos sin dependencia entre sí) mantienen el orden relativo XML
8. **Localiza logs** en `<project_root>/<task_id>/result.log` (solo con `--logs`)
9. **Escribe** un único `.txt` por flujo con código + log de cada nodo intercalados,
   incluyendo nota de reordenación si el orden XML difería del de ejecución
10. **Genera** `_summary.json` con el recuento de nodos y logs por flujo

No hardcodea ningún nombre de flujo, ID ni ruta de carpeta.
Funciona con cualquier `.egp` de SAS Enterprise Guide 8.x del IIS La Fe.

---

## Notas técnicas

**Ordenación de flujos**
El orden del árbol de SAS EG se extrae de la sección `<Containers>` del `project.xml`.
Esta sección lista los `ProcessFlowContainer-XXX` IDs en el mismo orden en que
aparecen en el panel izquierdo de SAS EG. El orden de los elementos en el XML
es el orden de creación y NO refleja el orden del árbol — no son equivalentes.

**Ficheros nombrados con zero-padding**
El prefijo `flujo00_`, `flujo01_`, ..., `flujo12_` garantiza que cualquier
sort textual (ls, git, cmd) devuelva el orden correcto. Sin padding, `flujo10`
aparecería antes que `flujo2` en sorts puramente alfabéticos.

**Proyectos sin flujos numerados**
Si los flujos no tienen prefijo numérico (e.g., `Identificacion MM`, `Fármacos`),
el orden se extrae igualmente del árbol SAS EG vía `<Containers>`. No es necesario
renombrar los flujos en SAS EG para que el script funcione correctamente.

**Sort topológico de nodos dentro de cada flujo**
El orden de los nodos en el XML es el orden en que se crearon en SAS EG, no el
de ejecución. El script reordena aplicando sort topológico sobre el grafo de
dependencias de datos:
- `ShortCutToData` con `InputIDs=Task-Y` → Task-Y produce ese ShortCut
- `Task-Z` con `InputIDs` conteniendo ese `ShortCutToData-X` → Task-Z consume lo que produjo Task-Y
- Arco resultante: Task-Y → Task-Z (Y antes que Z)

En el SCA (13 flujos, 159 nodos), 12 de 13 flujos tenían nodos en orden incorrecto
en el XML. El sort topológico los reordenó automáticamente.

**Código embebido en XML**
El código SAS real está en `<TaskCode>` dentro del `project.xml`, no en los
archivos `.sas` físicos del zip. Los `.sas` físicos son artefactos de exportaciones
manuales y solo son relevantes para CodeTask (código escrito a mano por el usuario).

**Logs en subcarpetas**
Cada tarea ejecutada genera una subcarpeta `<task_id>/result.log` en el zip.
Los task_ids son del tipo `Query-XXX`, `CodeTask-XXX`, `AppendTask-XXX`,
`ImportTask-XXX`. Los logs del project-level están en `ProjectLog-XXX/result.log`
y NO se incluyen (solo son relevantes para el diagnóstico de SAS EG, no para la migración).

**Versiones SAS EG**
Probado con EGVersion="8.2". Si falla con una versión distinta, compartir un
fragmento de `project.xml` para adaptar el parser.

---

## Pipeline completo de migración

```
1. [AUTOMÁTICO]  extract_egp.bat "proyecto.egp" --logs
                   → flujo00_xxx.txt ... flujo{N}_yyy.txt
                     (flujos en orden árbol SAS EG, nodos en orden de ejecución)

2. [AUTOMÁTICO]  generate_notebook.py  (script separado)
                   → flujo00_xxx.ipynb con estructura CP4D, helpers, SQL a revisar

3. [MANUAL]      Subir .ipynb a CP4D, revisar SQL Presto, ajustar queries

4. [MANUAL]      Ejecutar, corregir errores, validar contra referencias SAS del LOG

5. Repetir pasos 3-4 para cada flujo en orden (respetando dependencias entre flujos)
```

Los pasos 1 y 2 son automatizables. Los pasos 3-5 requieren criterio humano
y no se pueden eliminar sin sacrificar la calidad de la migración.
