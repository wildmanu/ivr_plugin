# -*- coding: utf-8 -*-

"""
Archivo ivr_cat.py

Este archivo alberga todas las funciones para el tratamiento de datos ontenidos de 
la Sede Electronica de Catastro.

Fecha creación:     02/12/2024
Fecha modificación: 09/02/2026 --> Última modificación 

Listado modificaciones y avances 

1) 09/02/02026 
- Parcheado errores 7-zip, ya no sale terminal, también se adaptado para otros OS
- Se prueba en QGIS y funciona, hay que tener cuidado con lógica para que el usuario
  no este descomprimiendo todo el rato o sobreescribeido datos.

@author: manuel
"""
import os, re, glob
import gzip, zipfile
import subprocess, shutil, platform
import pandas as pd
import geopandas as gpd

from datetime import datetime
from qgis.core import Qgis, QgsMessageLog

# Definir las funciones que se exportarán al importar con *

__all__ = [
    "lectura_ficheros_cat",
    "encontrar_ruta_cat",
    "obtener_anio_cat",
    "descomprimir_ficheros_cat",
    "consolidar_rutas",
    "leer_parcela_shp_desde_zip",
    "catstruct_14",
    "catstruct_15",
           ]

###############################################################################
#                         FUNCIONES  AUXILIARES                               #
###############################################################################

# Descomprimir ficheros .cat con zipfile + 7-Zip
def descomprimir_peticiones(directorio, carpeta_destino=None):
    """
    Descomprime archivos .zip con patrones específicos en subcarpetas
    organizadas por los primeros 2 dígitos del archivo interno + tipo.
    
    Retorna:
        Boleano: True si se procesaron archivos, False si no había peticiones
    """
    # Tipo de peticoomes 
    patrones = {
        "_PETICION_DESCARGA_CAT": "_CAT",
        "_PETICION_DESCARGA_SH": "_SHP"   #_SHA en 2025, se deja en _SH por si cambia
    }
    
    # Verificar si hay archivos de peticiones antes de hacer nada
    archivos_peticiones = [
        f for f in os.listdir(directorio)
        if f.endswith('.zip') and any(p in f for p in patrones.keys())
    ]
    
    # Importante para simplificar lógica 
    if not archivos_peticiones:
        return False
    
    # Crear carpeta destino solo si hay archivos
    if carpeta_destino is None:
        carpeta_destino = directorio
    else:
        os.makedirs(carpeta_destino, exist_ok=True)
    
    descomprimidos = []
    errores = []
    
    for archivo in archivos_peticiones:
        tipo = None
        for patron, sufijo in patrones.items():
            if patron in archivo:
                tipo = sufijo
                break
        
        ruta_zip = os.path.join(directorio, archivo)
        
        try:
            with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
                contenido = zip_ref.namelist()
                if not contenido:
                    errores.append(f"{archivo}: ZIP vacío")
                    continue
                
                archivo_interno = contenido[0]
                for item in contenido:
                    if item.endswith('.zip'):
                        archivo_interno = item
                        break
                
                nombre_interno = os.path.basename(archivo_interno)
                prefijo = nombre_interno[:2]
                
                subcarpeta = os.path.join(carpeta_destino, f"{prefijo}{tipo}")
                os.makedirs(subcarpeta, exist_ok=True)
                
                zip_ref.extractall(subcarpeta)
                
            descomprimidos.append(archivo)
            
        except Exception as e:
            errores.append(f"{archivo}: {e}")
    
    # Log resumen
    QgsMessageLog.logMessage(
        f"Peticiones: {len(descomprimidos)} OK | {len(errores)} errores",
        "IVR", Qgis.Info
    )
    
    # Log errores solo si hay
    if errores:
        QgsMessageLog.logMessage(
            f"Errores en peticiones: {', '.join(errores)}",
            "IVR", Qgis.Warning
        )
    
    return True

def encontrar_7zip():
    """Busca la instalación de 7-Zip en el sistema (Windows, Mac o Linux).
    Si no esta, advierte al usuario de que instale 7-zip si va usar provincias
    problematicas."""
    # Buscar en PATH primero
    en_path = shutil.which('7z') or shutil.which('7za') or shutil.which('7zz')
    
    if en_path:
        return en_path
    
    sistema = platform.system()
    
    if sistema == "Windows":
        rutas_comunes = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
            os.path.expandvars(r"%PROGRAMFILES%\7-Zip\7z.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\7-Zip\7z.exe"),
        ]
    
    elif sistema == "Darwin":  # macOS
        rutas_comunes = [
            "/usr/local/bin/7z",
            "/usr/local/bin/7za",
            "/opt/homebrew/bin/7z",      
            "/opt/homebrew/bin/7za",
            "/Applications/7zFM.app/Contents/MacOS/7zFM",
        ]
    
    else:  # Linux
        rutas_comunes = [
            "/usr/bin/7z",
            "/usr/bin/7za",
            "/usr/bin/7zz",
            "/usr/local/bin/7z",
            "/snap/bin/7z",              
        ]
    
    for ruta in rutas_comunes:
        if os.path.isfile(ruta):
            return ruta
    
    # Mensaje en log de QGIS si no se encuentra
    partidos = ["03", "08", "15", "28", "29", "30", "41", "43", "45", "46"]
    
    QgsMessageLog.logMessage(
        f"7-Zip no encontrado. Instálelo: https://www.7-zip.org/\n"
        f"Provincias afectadas: {', '.join(partidos)}",
        "IVR", 
        Qgis.Warning
    )
    
    return None

def ejecutar_7zip(cmd, carpeta_actual, ruta_7zip):
    """Ejecuta 7-Zip sin mostrar ventana de terminal.
    Precaucuón por si el usuario le da por cerrarlo"""
    kwargs = {
        "capture_output": True,
        "text": True,
        "cwd": carpeta_actual
    }
    
    # Ocultar terminal en Windows
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    
    return subprocess.run(cmd, **kwargs)

def descomprimir_recursivo(directorio, borrar_originales=True):
    """
    Descomprime archivos ZIP (normales y partidos) de forma recursiva.
    
    Parámetros:
      * directorio (str): Directorio raíz donde buscar
      * borrar_originales (bool): Si True, elimina los archivos después de descomprimir
      (Sí, porque sino van a ser muchos datos duplicados, con no tocar peticiones)
    
    Devuelve:
        tupla: resumen dict, ruta_7zip
    """
    ruta_7zip = encontrar_7zip()
    tiene_7zip = ruta_7zip is not None
    
    resumen = {"exitos": 0, "errores": 0, "warnings": 0}
    
    for carpeta_actual, subcarpetas, archivos in os.walk(directorio):
        
        # Detectar ZIPs partidos (.z01 presente)
        partes_z01 = [f for f in archivos if f.lower().endswith('.z01')]
        zips_partidos = set()
        
        for parte in partes_z01:
            nombre_base = parte[:-4]
            zips_partidos.add(nombre_base)
        
        # Procesar ZIPs partidos
        for nombre_base in zips_partidos:
            archivo_principal = nombre_base + ".zip"
            ruta_principal = os.path.join(carpeta_actual, archivo_principal)
            
            if not os.path.exists(ruta_principal):
                patron = os.path.join(carpeta_actual, f"{nombre_base}.z*")
                partes = sorted(glob.glob(patron))
                if partes:
                    ruta_principal = partes[-1]
                else:
                    resumen["errores"] += 1
                    continue
            
            if not tiene_7zip:
                resumen["warnings"] += 1
                continue
            
            try:
                cmd = [ruta_7zip, "x", ruta_principal, f"-o{carpeta_actual}", "-y"]
                resultado = ejecutar_7zip(cmd, carpeta_actual, ruta_7zip)
                
                if resultado.returncode != 0:
                    raise Exception(resultado.stderr or resultado.stdout)
                
                resumen["exitos"] += 1
                
                if borrar_originales:
                    for parte in glob.glob(os.path.join(carpeta_actual, f"{nombre_base}.z*")):
                        os.remove(parte)
                    zip_final = os.path.join(carpeta_actual, f"{nombre_base}.zip")
                    if os.path.exists(zip_final):
                        os.remove(zip_final)
                    
            except Exception as e:
                QgsMessageLog.logMessage(f"Error ZIP partido {nombre_base}: {e}", "IVR", Qgis.Warning)
                resumen["errores"] += 1
        
        # Procesar ZIPs normales
        for archivo in archivos:
            if not archivo.lower().endswith('.zip'):
                continue
            
            nombre_base = archivo[:-4]
            
            if nombre_base in zips_partidos:
                continue
            
            tiene_partes = any(
                os.path.exists(os.path.join(carpeta_actual, f"{nombre_base}.z{str(i).zfill(2)}"))
                for i in range(1, 10)
            )
            if tiene_partes:
                continue
            
            ruta_zip = os.path.join(carpeta_actual, archivo)
            
            try:
                with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
                    zip_ref.extractall(carpeta_actual)
                
                resumen["exitos"] += 1
                
                if borrar_originales:
                    os.remove(ruta_zip)
                    
            except zipfile.BadZipFile:
                if tiene_7zip:
                    try:
                        cmd = [ruta_7zip, "x", ruta_zip, f"-o{carpeta_actual}", "-y"]
                        resultado = ejecutar_7zip(cmd, carpeta_actual, ruta_7zip)
                        
                        if resultado.returncode == 0:
                            resumen["exitos"] += 1
                            if borrar_originales:
                                os.remove(ruta_zip)
                        else:
                            raise Exception(resultado.stderr)
                    except Exception as e:
                        QgsMessageLog.logMessage(f"Error {archivo}: {e}", "IVR", Qgis.Warning)
                        resumen["errores"] += 1
                else:
                    resumen["errores"] += 1
                    
            except Exception as e:
                QgsMessageLog.logMessage(f"Error {archivo}: {e}", "IVR", Qgis.Warning)
                resumen["errores"] += 1
    
    # Log resumen final
    QgsMessageLog.logMessage(
        f"Descompresión: {resumen['exitos']} OK | {resumen['errores']} errores | {resumen['warnings']} warnings",
        "IVR", Qgis.Info
    )
    
    return resumen, ruta_7zip

# Lectura especializada en ficheros .cat (Tabla 14 y Tabla 15)
def parsear_linea(linea, estructura):
    """Parsea una línea de texto de ancho fijo según una estructura definida.
    Extrae los campos por posición (1-based) y longitud, elimina espacios
    y devuelve un diccionario con valores de texto o None si están vacíos."""
    registro = {}

    for posicion, longitud, tipo, nombre, columna in estructura:
        valor = linea[posicion - 1 : posicion - 1 + longitud].strip()

        # Siempre texto, incluso si el tipo es 'N'
        registro[columna] = valor if valor != "" else None

    return registro

def lectura_ficheros_cat(ruta_gzip, tabla_15 = True):
    """Lee los ficheros .cat para dejarlos en un df bajo la estructura definida 
    en los diccionarios catstruct 14 y 15, obtenidos del Clasificador Catastral 
    desarrollado por Nikolai Shurupov (Universidad de Alcalá de Henares)."""
    
    filas_14 = []
    filas_15 = []

    with gzip.open(ruta_gzip, "rt", encoding="latin1", errors="replace") as f:
        for linea in f:
            tipo = linea[:2]

            if tipo == "14":
                filas_14.append(parsear_linea(linea, catstruct_14))

            elif tabla_15 and tipo == "15":
                filas_15.append(parsear_linea(linea, catstruct_15))

    df_14 = pd.DataFrame(filas_14)

    if tabla_15:
        df_15 = pd.DataFrame(filas_15)
        return df_14, df_15

    return df_14

# Detectar de que año y semestre es archivo de catastro
def obtener_anio_cat(ruta_gzip, df_14=None):
    """
    Devuelve el periodo del fichero CAT en formato:
    - 'IS-año' para primer semestre (enero-junio)
    - 'IIS-año' para segundo semestre (julio-diciembre)
    """
    fecha = None
    
    # 1. Buscar fecha completa en el nombre (formato DDMMYYYY o YYYYMMDD)
    nombre = os.path.basename(ruta_gzip)
    
    # Buscar patrón DDMMYYYY (
    match_ddmmyyyy = re.search(r'(\d{2})(\d{2})(20\d{2})', nombre)
    if match_ddmmyyyy:
        dia, mes, anio = match_ddmmyyyy.groups()
        try:
            fecha = datetime(int(anio), int(mes), int(dia))
        except ValueError:
            pass
    
    # Buscar patrón YYYY-MM-DD o YYYYMMDD
    if not fecha:
        match_yyyymmdd = re.search(r'(20\d{2})[-_]?(\d{2})[-_]?(\d{2})', nombre)
        if match_yyyymmdd:
            anio, mes, dia = match_yyyymmdd.groups()
            try:
                fecha = datetime(int(anio), int(mes), int(dia))
            except ValueError:
                pass
    
    # 2. Si no hay fecha en nombre, buscar en datos
    if not fecha and df_14 is not None and 'fecha_alta' in df_14.columns:
        fechas = pd.to_datetime(df_14['fecha_alta'].dropna(), format='%Y%m%d', errors='coerce')
        if not fechas.empty:
            fecha = fechas.max()
    
    # 3. Si aún no hay fecha, usar modificación del archivo
    if not fecha and os.path.exists(ruta_gzip):
        fecha = datetime.fromtimestamp(os.path.getmtime(ruta_gzip))
    
    # Determinar semestre y formatear
    if fecha:
        anio = fecha.year
        mes = fecha.month
        semestre = "IS" if mes <= 6 else "IIS"
        return f"{semestre}-{anio}"
    
    return None

# Busqueda de rutas a los archivos .cat 
def nombre_carpeta_n(ruta, n):
    """Devuelve el nombre de la carpeta n niveles por encima del archivo.
    Función auxiliar para generar df_archivos bien"""
    for _ in range(n):
        ruta = os.path.dirname(ruta)
    return os.path.basename(ruta)

def encontrar_ruta_cat(ruta_base, patron):
    """
    Devuelve una lista con la ruta completa de todos los archivos .CAT.gz
    encontrados recursivamente dentro de ruta_base. Función auxiliar.
    """
    rutas_cat_gz = []

    for root, _, files in os.walk(ruta_base):
        for f in files:
            if f.upper().endswith(patron):
                rutas_cat_gz.append(os.path.join(root, f))

    return rutas_cat_gz

def consolidar_rutas(ruta_base):
    """
    Sirve para ordenar toda la información de las rutas, cpro, cmun_dgc, nmun...
    junto la información de la ruta de los archivos para ser procesados. 
    A su vez, servirá de nezo iterable para el núcleo de procesameinto de la 
    lógica principal del IVR y fututamente se almacenrán en las estadísticas 
    en el df_archivos para generar csv municipios. 
    
    Tiene ruta_base para lozalizar archivos y devuelve df_archvios con información 
    básica. 
    """
    # Funciones auxiliares .cat
    descomprimir_ficheros_cat(ruta_base)

    rutas_cat_gz = encontrar_ruta_cat(ruta_base, patron = ".CAT.GZ")
    rutas_pc_zip = encontrar_ruta_cat(ruta_base, patron = "_PARCELA.ZIP")
    
    # Sacar nombres carpetas interesantes 
    carpeta_cat = [nombre_carpeta_n(r, 0) for r in rutas_cat_gz]
    carpeta_shp = [nombre_carpeta_n(r, 1) for r in rutas_pc_zip]
    
    # Generar info de ruta a .CAT
    df_cat = pd.DataFrame({
        "cpro": [c[:2] for c in carpeta_cat],
        "cmun_dgc": [c[2:5] for c in carpeta_cat],
        # Sin mucho sentido generar fecha, mejor función y no duplicar info en df 
        # "fecha": [c.split("_", 1)[1][:8] for c in carpeta_cat if "_" in c],
    })
    
    df_cat["ruta_cat"] = pd.Series(rutas_cat_gz) # Ruta CAT
    
    # Generar info de ruta a .SHP
    df_shp = pd.DataFrame({
        "cpro": [c[:2] for c in carpeta_shp],
        "cmun_dgc": [c[2:5] for c in carpeta_shp],
        "tipo": [c[5] for c in carpeta_shp],     # Tipo de ámbito
        "subtipo": [c[6] for c in carpeta_shp],
        "nmun": [" ".join(c.split()[2:]).strip() for c in carpeta_shp if len(c.split()) >= 3],
    })
    
    df_shp["ruta_shp"] = pd.Series(rutas_pc_zip) # Ruta SHP
    
    # Consolidar datos 
    df_archivos = df_shp.merge(
        df_cat,
        on=["cpro", "cmun_dgc"],
        how="inner"   
    )
    
    return df_archivos

def descomprimir_ficheros_cat(ruta_base):
    for raiz, carpetas, archivos in os.walk(ruta_base):
        for archivo in archivos:
            nombre = archivo.lower()
    
            if (
                nombre.endswith(".zip")
                and ("_ua_" in nombre or "_u_" in nombre)
            ):
                ruta_zip = os.path.join(raiz, archivo)
    
                # nombre sin .zip
                nombre_sin_zip = os.path.splitext(archivo)[0]
    
                # carpeta donde se descomprimirá
                ruta_destino = os.path.join(raiz, nombre_sin_zip)
    
                # si ya está descomprimido, saltamos
                if os.path.exists(ruta_destino):
                    continue
    
                # descomprimir
                try:
                    with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
                        zip_ref.extractall(ruta_destino)
                except zipfile.BadZipFile:
                    QgsMessageLog.logMessage(
                        f"ZIP corrupto: {ruta_zip}",
                        "TIME", Qgis.Info)
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"Error en: {ruta_zip}: {e}",
                        "TIME", Qgis.Info)
 
def leer_parcela_shp_desde_zip(ruta_zip, nombre_shp = "PARCELA.SHP", columns = None):
    """
    Devuelve un GeoDataFrame desde un ZIP, concretamente busca PARCELA.SHP en rutas SHP
    que contiene el parcelario residencial. Devuelve también la columna de geoemtry bien
    para no romper lógica plugin. 
    """
    
    objetivo = nombre_shp.lower()

    with zipfile.ZipFile(ruta_zip, "r") as z:
        nombres = z.namelist()

        candidatos = []
        for n in nombres:
            if n.lower().endswith(".shp") and os.path.basename(n).lower() == objetivo:
                candidatos.append(n)

        shp_interno = candidatos[0]

    vfs_path = "zip://{}!{}".format(ruta_zip, shp_interno)
    gdf = gpd.read_file(vfs_path)

    # Normalizar columnas SIN tocar geometry
    geom_name = gdf.geometry.name  # normalmente 'geometry'
    nuevas_cols = []
    for c in gdf.columns:
        if c == geom_name:
            nuevas_cols.append("geometry")
        else:
            nuevas_cols.append(c.upper())

    gdf.columns = nuevas_cols
    gdf = gdf.set_geometry("geometry")

    # Filtrar columnas si se solicitan
    if columns is not None:
        cols = []
        for c in columns:
            if str(c).lower() == "geometry":
                cols.append("geometry")
            else:
                cols.append(str(c).upper())

        # asegurar geometry activa
        if "geometry" not in cols:
            cols.append("geometry")

        gdf = gdf[cols]
        gdf = gdf.set_geometry("geometry")

    return gdf


###############################################################################
#                         OTRA INFORMACIÓN NO ORIGINAL                        #
###############################################################################

# Autor diccionarios: Nikolai Shurupov (Universidad de Alcalá de Henares)
# Función: structured dictionaries to extract information from 
# .CAT files, used in the cadastral classifier QGIS plugin

# Esta es una definicion de los diccionarios que conentran la estrucutra que se
# debe seguir a la hora de realizar la extraccion de la diferente informacion 
# que atañe a cada tipo de tabla. Para cada tipo de tabla que es posible generar,
# para cada columna que tendrá,  se define el punto de comienzo, la longitud,
# el tipo, una descripcion y el codigo interno.

# Enlace http://www.catastro.hacienda.gob.es/documentos/formatos_intercambio/catastro_fin_cat_2006.pdf

# 14- Registros de construcción
catstruct_14 = [
    [24, 2, 'N', 'cmun_dgc', '24_cd'],
    [26, 3, 'N', 'cod_mun_dgc', '26_cmc'],
    [31, 14, 'X', 'refcat', '31_pc'],
    [45, 4, 'N', 'numero_orden_elemento_construccion', "45_noec"],
    [51, 4, 'X', 'numordbieinm', "51_nobf"],
    [55, 4, 'X', 'codigo_unidad_constructiva_asociada', "55_cuc"],
    [59, 4, 'X', 'bloque', "59_bl"],
    [63, 2, 'X', 'escalera', "63_es"],
    [65, 3, 'X', 'planta', "65_pt"],
    [68, 3, 'X', 'puerta', "68_pu"],
    [71, 3, 'X', 'codigo_destino_dgc', "71_cd"],
    [74, 1, 'X', 'tipo_reforma_o_rehabilitacion', "74_tr"], 
    [75, 4, 'N', 'anyo_reforma', "75_ar"],
    [79, 4, 'N', 'ant_efc', "79_aec"],
    [83, 1, 'X', 'indicador_local_interior', "83_ili"], # 'S', 'N'
    [84, 7, 'N', 'supptcat', "84_stl"],
    [91, 7, 'N', 'superficie_porches_y_terrazas_m2', "91_spt"],
    [98, 7, 'N', 'superficie_imputable_en_otras_plantas_m2', "98_sil"],
    [105, 5, 'X', 'tipcon_ntv', "105_tip"],
    [112, 3, 'X', 'modalidad_reparto_elementos_comunes', "112_modl"]
]

# 15 - Registro de Inmueble
catstruct_15 = [
    [24, 2, 'N', 'codigo_delegacion_meh', "24_cd"],
    [26, 3, 'N', 'codigo_municipio_dgc', "26_cmc"],
    [29, 2, 'X', 'clase_bi', "29_cn"],
    [31, 14, 'X', 'refcat', "31_pc"],
    [45, 4, 'N', 'numordbieinm', "45_car"],
    [49, 1, 'X', 'primer_caracter_control', "49_cc1"],
    [50, 1, 'X', 'segundo_caracter_control', "50_cc2"],
    [51, 8, 'N', 'numero_fijo_bien_inmueble', "51_nfbi"],
    [59, 15, 'X', 'identificacion_inmueble_segun_ayuntamiento', "59_iia"],
    [74, 19, 'X', 'numero_finca_registral', "74_nfv"],
    [93, 2, 'N', 'codigo_provincia_ine', "93_cp"],
    [95, 25, 'X', 'nombre_provincia', "95_np"],
    [120, 3, 'N', 'codigo_municipio_dgc_2', "120_cmc"],
    [123, 3, 'N', 'codigo_municipio_ine', "123_cm"],
    [126, 40, 'X', 'nombre_municipio', "126_nm"],
    [166, 30, 'X', 'nombre_entidad_menor', "166_nem"],
    [196, 5, 'N', 'codigo_via_publica_dgc', "196_cv"],
    [201, 5, 'X', 'tipo_via', "201_tv"],
    [206, 25, 'X', 'nombre_via', "206_nv"],
    [231, 4, 'N', 'primer_numero_policia', "231_pnp"],
    [235, 1, 'X', 'primera_letra', "235_plp"],
    [236, 4, 'N', 'segundo_numero_policia', "236_snp"],
    [240, 1, 'X', 'segunda_letra', "240_slp"],
    [241, 5, 'N', 'kilometro_por_cien', "241_km"],
    [246, 4, 'X', 'bloque', "246_bl"],
    [250, 2, 'X', 'escalera', "250_es"],
    [252, 3, 'X', 'planta', "252_pt"],
    [255, 3, 'X', 'puerta', "255_pu"],
    [258, 25, 'X', 'direccion_no_estructurada', "258_td"],
    [283, 5, 'N', 'codigo_postal', "283_dp"],
    [288, 2, 'X', 'distrito_municipal', "288_dm"],
    [290, 3, 'N', 'codigo_municipio_origen_caso_agregacion_dgc', "290_cma"],
    [293, 2, 'N', 'codigo_zona_concentracion', "293_czc"],
    [295, 3, 'N', 'codigo_poligono', "295_cpo"],
    [298, 5, 'N', 'codigo_parcela', "298_cpa"],
    [303, 5, 'X', 'codigo_paraje_dgc', "303_cpaj"],
    [308, 30, 'X', 'nombre_paraje', "308_npa"],
    [368, 4, 'X', 'numero_orden_inmueble_en_escritura', "368_noe"],
    [372, 4, 'N', 'ant_bi', "372_ant"],
    [428, 1, 'X', 'clave_uso', "428_grbice/coduso"], 
    [442, 10, 'N', 'superficie_construida_m2', "442_sfc"],
    [452, 10, 'N', 'superficie_asociada_m2', "452_sfs"],
    [462, 9, 'N', 'coeficiente_propiedad_en_cienmillonesimas_partes', "462_cpt"]
]









