#!/usr/bin/env python3
"""
extract_egp.py  —  Extractor generalista de proyectos SAS Enterprise Guide (.egp)

Produce UN archivo .txt por flujo con código SAS y log de cada nodo intercalados.

Estructura interna verificada (SAS EG 8.x, IIS La Fe):
  project.xml (UTF-16)
    ProcessFlowContainer  →  define cada flujo
    Code                  →  código para Query/AppendTask/ImportTask  (<TaskCode> embebido)
    CodeTask              →  código escrito a mano  (archivo .sas físico en subcarpeta)
    Log                   →  metadata de logs (cubre CodeTask sin Code wrapper)

  Subcarpetas del .egp descomprimido (~370):
    <task_id>/result.log  →  log de ejecución de cada tarea

Uso:
    python extract_egp.py proyecto.egp
    python extract_egp.py proyecto.egp --logs
    python extract_egp.py proyecto.egp --output carpeta_salida
    python extract_egp.py carpeta_ya_descomprimida --logs
"""

import sys, re, json, zipfile, shutil, argparse
from collections import defaultdict
from pathlib import Path


# ============================================================
# LECTURA DEL XML
# ============================================================

def leer_xml(path):
    with open(path, 'rb') as f:
        raw = f.read()
    for enc in ('utf-16', 'utf-16-le', 'utf-16-be', 'utf-8-sig', 'utf-8'):
        try:
            text = raw.decode(enc)
            if '<ProjectCollection' in text or '<?xml' in text:
                print(f"  Codificacion: {enc}")
                return text
        except Exception:
            pass
    raise ValueError(f"No se pudo decodificar {path}")


# ============================================================
# PARSEO
# ============================================================

def bloques_por_tipo(text, element_type):
    marker  = f'<Element Type="{element_type}">'
    partes  = text.split(marker)
    bloques = []
    for parte in partes[1:]:
        fin    = re.search(r'<Element Type="SAS\.EG', parte)
        bloque = parte[:fin.start()] if fin else parte
        bloques.append(bloque)
    return bloques


def inner(bloque, tag):
    m = re.search(rf'<{tag}>(.*?)</{tag}>', bloque, re.DOTALL)
    return m.group(1).strip() if m else ''


def codigo_limpio(bloque):
    code = inner(bloque, 'TaskCode')
    if not code:
        code = inner(bloque, 'Text')
    return code.strip()


def safe_filename(nombre):
    for c in r'\/:*?"<>|':
        nombre = nombre.replace(c, '_')
    return nombre.strip().strip('._')


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def extraer_proyecto(input_path, output_dir=None, include_logs=False):
    input_path = Path(input_path).resolve()
    print(f"\n{'='*60}")
    print(f"  SAS EG Project Extractor")
    print(f"  Input  : {input_path.name}")
    print(f"  Modo   : {'codigo + logs' if include_logs else 'solo codigo'}")
    print(f"{'='*60}\n")

    # --- 1. Descomprimir si hace falta ---
    if input_path.suffix.lower() in ('.egp', '.zip'):
        extract_dir = input_path.parent / (input_path.stem + '_extracted')
        if not extract_dir.exists():
            print(f"Descomprimiendo -> {extract_dir.name}")
            zip_src = input_path
            zip_tmp = None
            if input_path.suffix.lower() == '.egp':
                zip_tmp = input_path.with_suffix('.zip')
                shutil.copy2(input_path, zip_tmp)
                zip_src = zip_tmp
            try:
                with zipfile.ZipFile(zip_src, 'r') as z:
                    z.extractall(extract_dir)
            finally:
                if zip_tmp and zip_tmp.exists():
                    zip_tmp.unlink()
        else:
            print(f"Carpeta ya extraida: {extract_dir.name}")
        project_root = extract_dir
    elif input_path.is_dir():
        project_root = input_path
        print(f"Carpeta: {project_root}")
    else:
        raise ValueError(f"Input no reconocido: {input_path}")

    # --- 2. Localizar y leer project.xml ---
    xml_matches = list(project_root.rglob('project.xml'))
    if not xml_matches:
        raise FileNotFoundError(f"No se encuentra project.xml en {project_root}")
    xml_path = xml_matches[0]
    print(f"project.xml: {xml_path.relative_to(project_root)}")
    text = leer_xml(xml_path)
    print(f"XML leido: {len(text):,} caracteres\n")

    # --- 3. Extraer flujos ---
    flows = {}
    for b in bloques_por_tipo(text, 'SAS.EG.ProjectElements.ProcessFlowContainer'):
        label = inner(b, 'Label')
        fid   = inner(b, 'ID')
        if label and fid:
            flows[fid] = label

    if not flows:
        raise ValueError("No se encontraron flujos en project.xml.")

    print(f"Flujos detectados: {len(flows)}")
    for _, fname in sorted(flows.items(), key=lambda x: x[1]):
        print(f"  {fname}")

    # --- 4. Construir mapa task_id -> container_id ---
    #
    # Fuente A: Code elements (<InputIDs>)  →  Query, AppendTask, ImportTask
    # Fuente B: Log elements  (<InputIDs>)  →  CodeTask sin Code wrapper
    #
    task_to_container = {}

    code_bloques = bloques_por_tipo(text, 'SAS.EG.ProjectElements.Code')
    log_bloques  = bloques_por_tipo(text, 'SAS.EG.ProjectElements.Log')

    print(f"\nCode elements: {len(code_bloques)}")
    print(f"Log elements : {len(log_bloques)}")

    # Nodos del flujo: (label, codigo, task_id) por container
    flow_nodos = defaultdict(list)   # container_id -> [(label, codigo, task_id)]

    for b in code_bloques:
        container = inner(b, 'Container')
        if container not in flows:
            continue
        label    = inner(b, 'Label')
        codigo   = codigo_limpio(b)
        task_id  = inner(b, 'InputIDs').strip()
        if task_id:
            task_to_container[task_id] = container
        if codigo:
            flow_nodos[container].append((label, codigo, task_id))

    # Fuente B: Log elements cubren CodeTask sin Code wrapper
    log_extras = 0
    for b in log_bloques:
        container = inner(b, 'Container')
        if container not in flows:
            continue
        task_id = inner(b, 'InputIDs').strip()
        if task_id and task_id not in task_to_container:
            task_to_container[task_id] = container
            log_extras += 1

    print(f"  + {log_extras} CodeTask adicionales desde Log elements")
    print(f"  Mapa task_id->container: {len(task_to_container)} entradas")

    # --- 5. Añadir código de CodeTask desde .sas físicos ---
    all_sas = list(project_root.rglob('*.sas'))
    sas_añadidos = 0
    for sas_file in all_sas:
        path_str = str(sas_file)
        for tid, container in task_to_container.items():
            if tid in path_str:
                ya = any(t == tid for _, _, t in flow_nodos[container])
                if not ya:
                    try:
                        codigo = sas_file.read_text(encoding='utf-8', errors='replace').strip()
                    except Exception:
                        codigo = ''
                    if codigo:
                        flow_nodos[container].append((sas_file.stem, codigo, tid))
                        sas_añadidos += 1
                break
    if all_sas:
        print(f"  .sas físicos: {len(all_sas)} encontrados, {sas_añadidos} añadidos")

    # --- 6. Preparar índice de logs físicos: task_id -> Path ---
    log_index = {}   # task_id -> Path del result.log
    logs_encontrados = 0

    if include_logs:
        for task_id in task_to_container:
            result_log = project_root / task_id / 'result.log'
            if result_log.exists():
                log_index[task_id] = result_log
                logs_encontrados += 1

        # Fallback: scan genérico si la estructura no es la esperada
        if logs_encontrados == 0:
            print("  ADVERTENCIA: ningún result.log encontrado con estructura estándar.")
            print("  Scan generico de *.log...")
            for lf in project_root.rglob('*.log'):
                path_str = str(lf)
                for tid in task_to_container:
                    if tid in path_str and tid not in log_index:
                        log_index[tid] = lf
                        logs_encontrados += 1
                        break

        aviso = '' if logs_encontrados > 0 else ' — pasa el .egp completo, no solo project.xml'
        print(f"  Logs encontrados: {logs_encontrados} / {len(task_to_container)}{aviso}")

    # --- 7. Preparar carpeta de salida ---
    if output_dir is None:
        output_dir = project_root / 'flujos_extraidos'
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nCarpeta de salida: {output_dir}\n")

    # --- 8. Escribir UN .txt por flujo ---
    #
    # Estructura del archivo:
    #
    #   /* FLUJO: nombre | Container: ID | Nodos: N */
    #
    #   /* ===== NODO 1: label [task_id] ===== */
    #
    #   /* --- CÓDIGO --- */
    #   <codigo SAS>
    #
    #   /* --- LOG --- */          (solo si --logs y existe result.log)
    #   <contenido del log>
    #
    resumen = []

    for container_id, flow_name in sorted(flows.items(), key=lambda x: x[1]):
        safe_name  = safe_filename(flow_name)
        nodos      = flow_nodos.get(container_id, [])
        n_con_log  = 0

        out_path = output_dir / f"{safe_name}.txt"

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(f"/* {'='*56}\n")
            f.write(f"   Flujo     : {flow_name}\n")
            f.write(f"   Container : {container_id}\n")
            f.write(f"   Nodos     : {len(nodos)}\n")
            f.write(f"   {'='*56} */\n")

            if not nodos:
                f.write("\n/* (sin nodos de código en este flujo) */\n")
            else:
                for i, (label, codigo, task_id) in enumerate(nodos, 1):
                    f.write(f"\n\n/* {'='*10} NODO {i}: {label}  [{task_id}]  {'='*10} */\n")

                    # Código SAS
                    f.write(f"\n/* --- CÓDIGO --- */\n\n")
                    f.write(codigo)
                    f.write("\n")

                    # Log (si se pidió y existe)
                    if include_logs:
                        log_path = log_index.get(task_id)
                        if log_path:
                            f.write(f"\n/* --- LOG --- */\n\n")
                            try:
                                f.write(log_path.read_text(encoding='utf-8', errors='replace'))
                            except Exception as e:
                                f.write(f"/* ERROR leyendo log: {e} */\n")
                            n_con_log += 1
                        else:
                            f.write(f"\n/* --- LOG: no encontrado para {task_id} --- */\n")

        tag_log = f"  {n_con_log}/{len(nodos)} con log" if include_logs else ""
        print(f"[ {flow_name} ]  {len(nodos)} nodos{tag_log}  ->  {out_path.name}")

        resumen.append({
            'flujo'   : flow_name,
            'nodos'   : len(nodos),
            'con_log' : n_con_log
        })

    # --- 9. Resumen JSON ---
    summary_path = output_dir / '_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"{'Flujo':<42} {'Nodos':>6} {'Logs':>6}")
    print(f"{'-'*56}")
    for s in sorted(resumen, key=lambda x: x['flujo']):
        print(f"  {s['flujo']:<40} {s['nodos']:>6} {s['con_log']:>6}")
    total_nodos = sum(s['nodos'] for s in resumen)
    total_logs  = sum(s['con_log'] for s in resumen)
    print(f"  {'TOTAL':<40} {total_nodos:>6} {total_logs:>6}")
    print(f"\n  Output: {output_dir}\n")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extrae codigo SAS y logs de un proyecto SAS Enterprise Guide (.egp) — UN archivo por flujo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python extract_egp.py proyecto.egp
  python extract_egp.py proyecto.egp --logs
  python extract_egp.py proyecto.egp --output C:/salida --logs
  python extract_egp.py carpeta_ya_descomprimida --logs
        """
    )
    parser.add_argument('input',
        help='Ruta al .egp, .zip, o carpeta ya descomprimida')
    parser.add_argument('--output', '-o', default=None,
        help='Carpeta de salida (por defecto: <input>_extracted/flujos_extraidos/)')
    parser.add_argument('--logs', '-l', action='store_true',
        help='Incluir logs de ejecucion junto al codigo de cada nodo')

    args = parser.parse_args()
    try:
        extraer_proyecto(args.input, args.output, args.logs)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
