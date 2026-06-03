# Extractor SAS EG — Guía de uso

Convierte cualquier proyecto SAS Enterprise Guide (`.egp`) en archivos `.txt`
organizados por flujo. Cada archivo contiene el código SAS y el log de ejecución
de cada nodo intercalados, listos para usarse como entrada al generador de notebooks CP4D.

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

Un único `.txt` por flujo en `<input>_extracted\flujos_extraidos\`:

```
flujos_extraidos\
├── 0.Identificacion_cohorte.txt
├── 1.Medidas_SIA.txt
├── 2.Preparacion_cohorte_final.txt
├── ...
├── 11. Hemorragias.txt
└── _summary.json
```

### Estructura interna de cada `.txt`

Código y log de cada nodo van juntos, en orden de aparición en el flujo:

```
/* ========================================================
   Flujo     : 5.Farmacia_Receta
   Container : ProcessFlowContainer-I7DQjnqCYTXYdXGp
   Nodos     : 20
   ======================================================== */


/* ========== NODO 1: Código  [ImportTask-WFjWkHBxMx9sywto]  ========== */

/* --- CÓDIGO --- */

DATA WORK.HIPOLIPEMIANTES_TRAT_0000;
    LENGTH CODPRINATC $ 7 ...
    ...

/* --- LOG --- */

NOTE: Table WORK.HIPOLIPEMIANTES_TRAT_0000 created, with 37 rows and 12 columns.
NOTE: DATA statement used (Total process time): ...


/* ========== NODO 2: Query_ver_edispensacion  [Query-FC2IkerHgHfsfmD2]  ========== */

/* --- CÓDIGO --- */

PROC SQL;
CREATE TABLE WORK.QUERY_FOR_VER_EDISPENSACION AS
SELECT ...

/* --- LOG --- */

NOTE: Table WORK.QUERY_FOR_VER_EDISPENSACION created, with 248990 rows and 6 columns.
...
```

Si un nodo no tiene log (no se ejecutó o se pasa sin `--logs`) aparece:
```
/* --- LOG: no encontrado para Query-XXX --- */
```

---

## Cómo funciona internamente

El `.egp` es un `.zip` disfrazado. Contiene un `project.xml` (UTF-16) con todo
el código embebido y ~370 subcarpetas con los logs de ejecución. El script:

1. Descomprime el `.egp` a `<nombre>_extracted/`
2. Lee `project.xml` detectando la codificación automáticamente
3. Extrae los `ProcessFlowContainer` → nombre e ID de cada flujo
4. Construye un mapa `task_id → flujo` desde dos fuentes:
   - `Code` elements (`<InputIDs>`) → cubre Query, AppendTask, ImportTask (159 tareas)
   - `Log` elements (`<InputIDs>`) → cubre CodeTask sin Code wrapper (14 tareas adicionales)
5. Extrae el código SAS de `<TaskCode>` para cada nodo; para CodeTask busca también el `.sas` físico en su subcarpeta
6. Si se usa `--logs`, localiza `<project_root>/<task_id>/result.log` para cada nodo
7. Escribe un único `.txt` por flujo con código + log de cada nodo intercalados
8. Genera `_summary.json` con el recuento de nodos y logs por flujo

No hardcodea ningún nombre de flujo, ID ni ruta. Funciona con cualquier `.egp`
de SAS Enterprise Guide 8.x del IIS La Fe.

---

## Notas técnicas

- **Código embebido en XML**: el código SAS real está en `<TaskCode>` dentro del
  `project.xml`, no en los archivos `.sas` físicos del zip. Estos últimos son
  artefactos de exportaciones manuales anteriores (solo relevantes para CodeTask).
- **Logs en subcarpetas**: cada tarea ejecutada genera una subcarpeta
  `<task_id>/result.log` en el zip. Los task_ids son del tipo `Query-XXX`,
  `CodeTask-XXX`, `AppendTask-XXX`, `ImportTask-XXX`.
- **Sin `--logs`**: el script solo extrae código. Los marcadores
  `/* --- LOG: no encontrado --- */` no aparecen.
- **Nodos sin log**: si un nodo nunca se ejecutó en SAS (o se pasó sin `--logs`),
  se marca como no encontrado y no interrumpe la extracción.
- **Versiones SAS EG**: probado con EGVersion="8.2". Si falla con una versión
  distinta, compartir un fragmento de `project.xml` para adaptar el parser.

---

## Pipeline completo de migración

```
1. [AUTOMÁTICO]  extract_egp.bat "proyecto.egp" --logs
                   → <flujo>.txt por cada flujo (código + logs intercalados)

2. [AUTOMÁTICO]  generate_notebook.py  (script separado, pendiente)
                   → <flujo>.ipynb con estructura CP4D, helpers, SQL traducido

3. [MANUAL]      Subir .ipynb a CP4D, revisar SQL Presto, ajustar queries

4. [MANUAL]      Ejecutar, corregir errores, validar contra referencias SAS

5. Repetir pasos 3-4 para cada flujo en orden de dependencia
```

Los pasos 1 y 2 son automatizables. Los pasos 3-5 requieren criterio humano
y no se pueden eliminar sin sacrificar la calidad de la migración.
