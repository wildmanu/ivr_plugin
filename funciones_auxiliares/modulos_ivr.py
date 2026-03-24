# -*- coding: utf-8 -*-
"""
Archivo modulos_ivr.py

Este archivo alberga todas las funciones con lógical principal del IVR plugin, 
aunque requiere de otros módulos propios para su correcto funcioamiento. 

Fecha creación:     XX/12/2024
Fecha modificación: 08/02/2026 --> Última modificación 

Listado modificaciones y avances 

1) 08/02/02026 
- Filtrado BI por usos mixtos + tabla 15 
- Añadido lectura directa ficheros .CAT, se elimina dependencia al plugin
  clasificador catastral. 
- Se define nueva lógica del IVR lOC, ahora ya por parcelario urbano a nivel 
  municipal y no para el conjunto de municipios introducciodos por el usuario.

@author: Manuel
"""
# Módulos estándar
import time
from ast import literal_eval

# Librerías científicas
import numpy as np
import pandas as pd
from scipy.stats import logistic
import geopandas as gpd

# QGIS
from qgis.core import (QgsMessageLog, Qgis)

# Funciones de lectura de ficheros .CAT
from . import ivr_cat as cat

###############################################################################
#                         FUNCIONES  PRINCIPALES                              #
###############################################################################

# Función para limpiar y establecer ídncies de municipios y provncias
def limpiar_archivos(df_archivos):
    """"Limpia y reordena el DF con los datos cat que usuario introduce para 
    asignarle el nomnbre de la provincia y procesar de menor a mayor"""
    
    # Ordenar DataFrame para procesamiento
    # Simpre se deja la captial de provincia para el final "900" para que los 
    # municipios pequeños vayan más fluidos y la barra de progreso no se atasque
    # al principio y de un poco más de seguridad.
    
    df_archivos = (
        df_archivos
        .assign(
            cpro_num = df_archivos["cpro"].astype(int),
            cmun_num = df_archivos["cmun_dgc"].astype(int),
        )
        .sort_values(by=["cpro_num", "cmun_num"])
        .drop(columns=["cpro_num", "cmun_num"])
        .reset_index(drop=True)
    )
    
    # Profeso por provincia (DGC): 01-50 + 55 Ceuta + 56 Melilla ?!
    # Resto -> "Sin clasificación DGC"

    df_archivos["cpro"] = df_archivos["cpro"].astype(str).str.zfill(2)
    df_archivos["cmun_dgc"] = df_archivos["cmun_dgc"].astype(str).str.zfill(3)
    
    # Catálogo DGC (solo para nombre)
    # PD aunque no estén ni País Vasco y Navarra se añaden para completar la ç
    # lista y no dejarlo con huecos. 
    df_provincias_dgc = pd.DataFrame({
        "cpro": [
            "01","02","03","04","05","06","07","08","09","10",
            "11","12","13","14","15","16","17","18","19","20",
            "21","22","23","24","25","26","27","28","29","30",
            "31","32","33","34","35","36","37","38","39","40",
            "41","42","43","44","45","46","47","48","49","50",
            "55","56"
        ],
        "npro": [
            "Álava","Albacete","Alicante","Almería","Ávila","Badajoz",
            "Illes Balears","Barcelona","Burgos","Cáceres","Cádiz","Castellón",
            "Ciudad Real","Córdoba","A Coruña","Cuenca","Girona","Granada",
            "Guadalajara","Gipuzkoa","Huelva","Huesca","Jaén","León","Lleida",
            "La Rioja","Lugo","Madrid","Málaga","Murcia", "Navarra","Ourense",
            "Asturias","Palencia","Las Palmas","Pontevedra","Salamanca",
            "Santa Cruz de Tenerife","Cantabria","Segovia", "Sevilla","Soria",
            "Tarragona","Teruel","Toledo","Valencia","Valladolid","Bizkaia",
            "Zamora","Zaragoza", "Ceuta","Melilla"
        ]
    })
    
    # Mapeo 
    map_prov = df_provincias_dgc.set_index("cpro")["npro"].to_dict()
    validos_dgc = set(map_prov.keys())
    
    # Nombre provincia final
    df_archivos["npro"] = df_archivos["cpro"].map(map_prov)
    df_archivos.loc[~df_archivos["cpro"].isin(validos_dgc), "npro"] = "Sin clasificación DGC"
    df_archivos["npro"] = df_archivos["npro"].fillna("Sin clasificación DGC")
    
    # Debug rápido 
    sobran = sorted(set(df_archivos["cpro"]) - validos_dgc)
    if sobran:
        mensaje = f"Códigos de provincia erróneos detectados en DGC: {sobran}"
        QgsMessageLog.logMessage(mensaje, "IVR", Qgis.Info)
        
    # total por provincia = nº municipios únicos
    tot_por_prov = (
        df_archivos[["cpro", "cmun_dgc"]]
        .drop_duplicates()
        .groupby("cpro")
        .size()
        .to_dict()
    )
    
    # índice por provincia basado en orden de municipios únicos
    df_archivos["_mun_key"] = df_archivos["cpro"] + df_archivos["cmun_dgc"]
    orden_mun = df_archivos.drop_duplicates(["cpro", "cmun_dgc"]).copy()
    orden_mun["idx_prov_mun"] = orden_mun.groupby("cpro").cumcount() + 1
    map_idx = dict(zip(orden_mun["_mun_key"], orden_mun["idx_prov_mun"]))
    
    df_archivos["idx_prov"] = df_archivos["_mun_key"].map(map_idx)
    df_archivos["total_prov"] = df_archivos["cpro"].map(tot_por_prov)
    df_archivos = df_archivos.drop(columns=["_mun_key"])
    
    return df_archivos
# Funciones para procesamiento de usos mixtos    
def procesar_uso_principal(df, col_uso_sup = "tsc", valor_inicial = 0,
    col_uso_p = "uso_bi", col_por_uso_p = "p_uso_bi"):
    """
    Lógica de filtrado de BI Residensicales en función de su coeficiente de 
    participación respecto a todas las construcciones que componen el BI. Se 
    clasifica como resieldencail cualdo la proporción mayoritaria es residencial
    cómputable: 
     *   Residencial: "0111", "0112", "0121", "0122", "0131",
     *   Otros usos: "02", "03", "04", "05", "06", "07", "08", "09", "10"

    Calcula el uso principal por fila:
        - col_uso_sup (tsc) columna intermedia para el cálculo.
        - col_uso_p: uso predominante (2 dígitos: '01'..'10') sólo deja residenicales
        - col_por_uso_p: porcentaje (0–100) de superficie del uso principal
           respecto al total de usos, redondeado a 2 decimales.
           Sirve para filtrar por usos mixtos si el suario lo estabelce oportuno.

    Devuelve:
      Mismo df con las columnas resultantes e intermedias.
    """
    # Funciones de apoyo
    def convertir_a_lista(usos):
        """Convierte cualquier cosa a lista segura."""
        if usos is None:
            return []
        if isinstance(usos, float) and pd.isna(usos):
            return []
        if isinstance(usos, (int, float)):
            return []
        if isinstance(usos, list):
            return usos
        if isinstance(usos, np.ndarray):
            return usos.tolist()

        #  La función espera algo asi: "['0121_95', '0123_62']" -> "tsc"
        if isinstance(usos, str):
            txt = usos.strip()
            if txt.startswith("[") and txt.endswith("]"):
                try:
                    return literal_eval(txt)
                except Exception:
                    pass
            # Si llegará algo asi "0121_95,0123_62" también lo procesaría.
            if "," in txt:
                return [x.strip() for x in txt.split(",") if x.strip()]

            return [txt]  
        
    def procesar_fila(row):
        usos_list = convertir_a_lista(row[col_uso_sup])

        for item in usos_list:
            if not isinstance(item, str):
                item = str(item)

            if "_" not in item:
                continue

            partes = item.split("_")
            if len(partes) < 2:
                continue

            codigo = partes[0]
            sup_str = partes[1]  

            try:
                sup = float(sup_str)
            except ValueError:
                continue

            # Recortar progresivamente: 0722 → 072 → 07 
            cod = codigo
            while len(cod) > 0:
                if (cod in columnas_tip) and (cod in row.index):
                    row[cod] += sup
                    break
                cod = cod[:-1]

        return row
        
    # Definir y asegurar columnas de tipología

    columnas_tip = ["0111", "0112", "0121", "0122", "0131",    # Residencial
      "02", "03", "04", "05", "06", "07", "08", "09", "10"]    # Otros 

    original_cols = list(df.columns) # Guardar orden original

    # Crear columnas de tipología 
    for col in columnas_tip:
        if col not in df.columns:
            df[col] = valor_inicial

    # Repartir superficie para las columnas 
    # Asegurar que columnas tipológicas son numéricas
    df[columnas_tip] = df[columnas_tip].apply(
        lambda s: pd.to_numeric(s, errors="coerce")).fillna(0.0)
    
    df = df.apply(procesar_fila, axis=1) # Funciones de apoyo para repartir superfie

    # Calcular uso principal 
    # Asegurar que las columnas existen y son numéricas
    
    cols_tip_presentes = [c for c in columnas_tip if c in df.columns]

    if not cols_tip_presentes:
        df[col_uso_p] = np.nan
        df[col_por_uso_p] = 0.0
        return df, columnas_tip

    df[cols_tip_presentes] = df[cols_tip_presentes].apply(
        lambda s: pd.to_numeric(s, errors="coerce")
    ).fillna(0.0)

    # Mapeo de columna por Uso (2 primeros caracteres)
    mapeo = {c: c[:2] for c in cols_tip_presentes}
    usos_unicos = sorted(set(mapeo.values()), key=lambda x: int(x))

    # Columnas temporales de suma por uso
    tmp_cols = []
    for u in usos_unicos:
        cols_u = [c for c in cols_tip_presentes if mapeo[c] == u]
        tmp_name = f"_tmp_uso_{u}"
        tmp_cols.append(tmp_name)
        df[tmp_name] = df[cols_u].sum(axis=1)

    total_sup = df[tmp_cols].sum(axis=1)

    # uso principal
    idx_max = df[tmp_cols].idxmax(axis=1)
    df[col_uso_p] = idx_max.str.replace("_tmp_uso_", "", regex=False)

    # superficie del uso principal
    sup_max = df[tmp_cols].max(axis=1)

    # porcentaje (0–100)
    with np.errstate(divide="ignore", invalid="ignore"):
        df[col_por_uso_p] = np.where(
            total_sup > 0,
            (sup_max / total_sup) * 100,
            0.0
        ).round(2)

    # limpiar columnas temporales
    df.drop(columns=tmp_cols, inplace=True)


    # Reordenar columnas (originales + tipologías al final)
    cols_tip_new = [c for c in columnas_tip if c not in original_cols]
    cols_rest = [
        c for c in df.columns
        if c not in original_cols and c not in cols_tip_new and c not in tmp_cols
    ]
    nuevo_orden = original_cols + cols_tip_new + cols_rest
    df = df[nuevo_orden]

    return df, columnas_tip
# Funciones para agregar o ponderar datos y leer diccionarios
def moda_segura(x, lista_tpc, tip = False):
    """
    Devuelve la moda de una Serie.
    Si hay varias, devuelve la primera.
    Si no hay valores válidos, devuelve pd.NA.
    Sólo tiene en cuenta tipologías residenciales computables cuando tip = True.
    """
    if tip:
        # Elimina los elementos de la serie que no estén en la lista
        x = x[x.isin(lista_tpc)]

    m = x.mode()
    return m.iloc[0] if not m.empty else pd.NA
def calculo_cvct(df, dic_calidad): 
    """Cálcula el Coeficiente de Valor de la Construcción, tras ponderar la
    tipología construtiva y la calidad contrutiva bajo las especificaciones 
    jurídicas vigentes (Real Decreto 1020/1993)"""
    
    rows = []
    
    for tip, d in dic_calidad.items():
        for cal, coef in d.items():
            rows.append({
                "tcus_bi": tip,
                "cvcn_bi": cal,
                "cvct": coef
            })

    df_dic = pd.DataFrame(rows)

    # Merge de equivalencias con Coef. Valor de ct
    df["cvcn_bi"] = df["cvcn_bi"].astype("string")

    df = df.merge(
        df_dic,
        on=["tcus_bi", "cvcn_bi"],
        how="left"
    )

    df["cvcn_bi"] = df["cvct"] 
    
    # Filtrado columnas BI temporales 
    col_def_bi = ["31_pc", "51_nobf", "cpro", "cmun_dgc", "nmun", 
     "n_ct", "sup_bi","ante_bi", "supc_bi", "tcus_bi", "calp_bi", "cvcn_bi"]
    
    df = df[col_def_bi]
    
    return df 
def cortes_gaus(clasificador_gau, metodo, rangos):
    """Función de apoyo para leer el método, cortes, nararanjas que tiene que 
    representar la lógica principal para clasificar y dar simbología al IVR"""
    # Obtención del cortes por método y rangos 
    cortes = clasificador_gau[metodo][rangos]
    
    # Letra método y nombre columna class 
    if metodo == "Cuantiles":
        letra = "Q"
    else: 
        letra = metodo[0]
        
    col_class = f"Clases_{letra}{rangos}"
    
    # Obtener clases, etiqueta y naranjas 
    clases = [c[0] for c in cortes] + [cortes[-1][1]] 
    etiqueta = [f"{letra}{i}" for i in range(1, len(cortes) + 1)]
    naranjas = [c[2] for c in cortes]
    
    # Retornar variables 
    return clases, etiqueta, naranjas, col_class
# Función de normalización del IVR
def transformacion_sigmoidal_scipy(df, ivr_loc = True, año_corte = None):
    """
    Normaliza variables que constituyen el Índice de Vulnerabilidad Residencial 
    mediante una función sigmoidal usando scipy.stats.logistic.

    Se aplica sobre: "supc_bi", "ante_bi" y "cvcn_bi"

    Lógica:
      - Para cada variable se eliminan atípicos según su propio criterio
        (IQR, límites manuales en caso de la antigüedad) para el ajsute de la logística.
      - La transformación sigmoidal (CDF) se aplica sobre todo el DataFrame incluendo 
        esos valores extremos. 

    Parámetros globales fijos (GAU) Datos II Semestre 2025:
      * Se usan para las columnas *_TFG (IVR GAU)

    Parámetros muestrales (locales):
      * Se estiman con logistic.fit() tras filtrar atípicos
         y se usan para las columnas *_TFM (IVR LOC)
    """

    # 1) Parámetros globales fijos (GAU) 
    # Calculado el 07/02/2026 con datos de II semestre de 2025 de catastro
    parametros_globales = {
    "supc_bi": {"loc": 87.853863963425700, "scale": 16.5700712996760620},
    "ante_bi": {"loc": 1984.5976385822298, "scale": 11.0895156036098110},
    "cvcn_bi": {"loc": 0.9907060595134738, "scale": 0.06898716437223629},
    }

    # Con la nueva versión del plugin ahora es obligatorio dar ambos valores del 
    # IVR por lo que este parametro queda obsoleto ya que siempre se cácluclara el IVR LOC
    
    if ivr_loc:
        
        df_transf = df.copy()
        parametros_muestrales = {}
        parametros_estadisticos = {}
    
        # supc_bi 
        col = "supc_bi"
        serie = df_transf[col].dropna()
    
        Q1 = serie.quantile(0.25)
        Q3 = serie.quantile(0.75)
        IQR = Q3 - Q1
        lim_inf_IQR = Q1 - 1.5 * IQR
        lim_sup_IQR = Q3 + 1.5 * IQR
    
        mask_superficie = (serie >= lim_inf_IQR) & (serie <= lim_sup_IQR)
        serie_fit_superficie = serie[mask_superficie]
    
        q05 = serie_fit_superficie.quantile(0.05)
        q95 = serie_fit_superficie.quantile(0.95)
    
        n_original = len(serie)
        n_IQR_abajo = (serie < lim_inf_IQR).sum()
        n_IQR_arriba = (serie > lim_sup_IQR).sum()
        n_filtrados_IQR = n_IQR_abajo + n_IQR_arriba
    
        n_total = len(serie_fit_superficie)
    
        pc_ft_mun = round((n_filtrados_IQR / n_original) * 100, 5) if n_original else 0.0
    
        loc_sample, scale_sample = logistic.fit(serie_fit_superficie)
    
        parametros_muestrales["supc_bi"] = {"loc": loc_sample, "scale": scale_sample}
    
        parametros_estadisticos["supc_bi"] = {
            "q1_spc": float(Q1),
            "q3_spc": float(Q3),
            "iqr_spc": float(IQR),
            "li_iqr_spc": max(0, float(lim_inf_IQR)),  # Sin sentido límites de superficies negativas
            "n_li_spc": int(n_IQR_abajo),
            "ls_iqr_spc": float(lim_sup_IQR),   
            "n_ls_spc": int(n_IQR_arriba),
            "q05_spc": float(q05),
            "q95_spc": float(q95),
            "loc_spc": float(loc_sample),
            "scale_spc": float(scale_sample),
            "n_fit_spc": int(n_total),
            "pc_ft_spc": float(pc_ft_mun),
        }
    
        # ante_bi 
        col = "ante_bi"
        serie = df_transf[col].dropna()
    
        Q1 = serie.quantile(0.25)
        Q3 = serie.quantile(0.75)
        IQR = Q3 - Q1
        lim_inf_IQR = Q1 - 1.5 * IQR
        lim_sup_manual = año_corte
    
        mask_antig = (serie >= lim_inf_IQR) & (serie <= lim_sup_manual)
        serie_fit_antig = serie[mask_antig]
    
        q05 = serie_fit_antig.quantile(0.05)
        q95 = serie_fit_antig.quantile(0.95)
    
        n_original = len(serie)
        n_fuera_inf = (serie < lim_inf_IQR).sum()
        n_fuera_sup = (serie > lim_sup_manual).sum()
        n_filtrados_total = n_fuera_inf + n_fuera_sup
    
        n_total = len(serie_fit_antig)
    
        pc_ft_mun = round((n_filtrados_total / n_original) * 100, 5) if n_original else 0.0
    
        loc_sample, scale_sample = logistic.fit(serie_fit_antig)
    
        parametros_muestrales["ante_bi"] = {"loc": loc_sample, "scale": scale_sample}
    
        parametros_estadisticos["ante_bi"] = {
            "q1_ate": float(Q1),
            "q3_ate": float(Q3),
            "iqr_ate": float(IQR),
            "li_iqr_ate": float(lim_inf_IQR),
            "n_li_ate": int(n_fuera_inf),          # <- corregido
            "ls_iqr_ate": float(lim_sup_manual),   
            "n_ls_ate": int(n_fuera_sup),          # <- corregido
            "q05_ate": float(q05),
            "q95_ate": float(q95),
            "loc_ate": float(loc_sample),
            "scale_ate": float(scale_sample),
            "n_fit_ate": int(n_total),             # <- n tras filtro
            "pc_ft_ate": float(pc_ft_mun),
        }
    
        # cvcn_bi 
        col = "cvcn_bi"
        serie = df_transf[col].dropna()
    
        Q1 = serie.quantile(0.25)
        Q3 = serie.quantile(0.75)
        IQR = Q3 - Q1
        lim_inf_IQR = Q1 - 1.5 * IQR
        lim_sup_IQR = Q3 + 1.5 * IQR
    
        mask_cal = (serie >= lim_inf_IQR) & (serie <= lim_sup_IQR)
        serie_fit_cal = serie[mask_cal]
    
        q05 = serie_fit_cal.quantile(0.05)
        q95 = serie_fit_cal.quantile(0.95)
    
        n_original = len(serie)
        n_IQR_abajo = (serie < lim_inf_IQR).sum()
        n_IQR_arriba = (serie > lim_sup_IQR).sum()
        n_filtrados_IQR = n_IQR_abajo + n_IQR_arriba
    
        n_total = len(serie_fit_cal)
    
        pc_ft_mun = round((n_filtrados_IQR / n_original) * 100, 5) if n_original else 0.0
    
        loc_sample, scale_sample = logistic.fit(serie_fit_cal)
    
        parametros_muestrales["cvcn_bi"] = {"loc": loc_sample, "scale": scale_sample}
    
        parametros_estadisticos["cvcn_bi"] = {
            "q1_cv": float(Q1),
            "q3_cv": float(Q3),
            "iqr_cv": float(IQR),
            "li_iqr_cv": float(lim_inf_IQR),
            "n_li_cv": int(n_IQR_abajo),
            "ls_iqr_cv": float(lim_sup_IQR),
            "n_ls_cv": int(n_IQR_arriba),
            "q05_cv": float(q05),
            "q95_cv": float(q95),
            "loc_cv": float(loc_sample),
            "scale_cv": float(scale_sample),
            "n_fit_cv": int(n_total),
            "pc_ft_cv": float(pc_ft_mun),
        }
    
    else:
        print("Sin cálculo IVR LOC")

    # Aplicar transformaciones sigmoides (global y muestral)
        
    for col in ["supc_bi", "ante_bi", "cvcn_bi"]:

        global_loc = parametros_globales[col]["loc"]
        global_scale = parametros_globales[col]["scale"]

        # CDF global (TFG)
        df_transf[f"{col}_tfg"] = logistic.cdf(
            df_transf[col], loc=global_loc, scale=global_scale
        )

        if ivr_loc:
            sample_loc = parametros_muestrales[col]["loc"]
            sample_scale = parametros_muestrales[col]["scale"]
    
            # CDF muestral/local (TFM)
            df_transf[f"{col}_tfm"] = logistic.cdf(
                df_transf[col], loc=sample_loc, scale=sample_scale
            )

    # Calcular IVR (1 - Valor normalizado) --> Para que lo más alto sea vulnerable
    if ivr_loc:
        df_transf["ivr_gau"] = 1 - df_transf.filter(regex="_tfg$").mean(axis=1)
        df_transf["ivr_loc"] = 1 - df_transf.filter(regex="_tfm$").mean(axis=1)
    else:
        df_transf["ivr_gau"] = 1 - df_transf.filter(regex="_tfg$").mean(axis=1)

    if ivr_loc:
        return df_transf, parametros_muestrales, parametros_estadisticos
    return df_transf
# Lógica principal de IVR Plugin
def logica_principal_ivr(ruta_base, metodo, rangos, col_ivr, 
                         val_t15, crs_ui, umbral_mix, task = None):
    """
    Se encarga unificar todas las funciones para clacular todos lso datos necesarios 
    del IVR, ¿Qué hace en resumidas cuentas? 
    
    A. Reconoce archivos .CAT y SHP y preprara para su procesameinto (df_archivos)
    B. Lee Tablas tipo 14 y 15 de catastro y archivos SHP
    C. Filtra en función de especificaciones del usuario, docuemntado proceso
    D. Agrega a nivel de BI y normaliza variables del IVR GAU y LOC
    E. Cáculula cortes y y estadísticas del filtrado
    G. Agrega a nivel de parcela y genera capa IVR 
    H. Prepara DFs con estadísticas a nivel de municipio y provincia  
    
    Últimos cambios y decisiones:
    1. A peteción de J.Prada e I.Sáchez se observan usos mixtos como catedrales
    o estaciones que tienen BI, se intrudice el filtrado de la tabla 15 y usos 
    mixtos obteniendo buenos resultados, aunque quedan algunos BI que no filtra
    al ser cosiderados como residenciales aunqeu sean cementerios o Bases militares. 
    Se estima que dichos BI, no hay manera de quitarlos ya con los datos de catastro
    y habría que hacerlo en base otros criterios. 
    
    2. Se cambia IVR LOC, ahora para cada muncipiom, antes para todos el parcelario 
    que introducia el usuario. El cambio, viene motivado a que es más interpretable 
    hacerlo por municipios para realziar comparaciones, de la otra forma el usuario 
    requiere mayor nivel de conocimiento para elegir muestras representativas.
    PD: Resulto se clacuúla dfs_bi el IVR LOC para todo el parcelario de forma 
    adiccional. 
        
    Cambios versión usos mixtos 20/01/2026 - Tabla 15 05/0272026
    """
    # Lista de dfs
    dfs_bi = []
    dfs_ivr = []
    
    t0 = time.time()

    # 1 Carga incial de rutas y extración datos carpetas 
    # Obtener datos básicos cpro, cmun_dgc y nombre municipio con rutas archivos
    try:
        df_archivos = cat.consolidar_rutas(ruta_base)  
        df_archivos = limpiar_archivos(df_archivos)
    except Exception as e:
        msg = f"Datos mal introducidos o no descomprimidos → {e!r}"
        # La causa mayoritaria de errores va a ser esta seguramente, quizás
        # habría que mejorarla u indicar como solucionarlo.
        QgsMessageLog.logMessage(msg, "IVR", Qgis.Critical)


    # Variables Globales
    num_municipios = len(df_archivos)
    año_corte = int(time.strftime("%Y")) + 1
     
    # Variables clasificador GAU
    if metodo != "Sin clasificar":
        clases, etiqueta, naranjas, col_class = cortes_gaus(
            clasificador_gau, metodo, rangos)
        
        # Crear diccioanrio para simbología
        dic_gau = dict(zip(clases, naranjas))
    
    # Iterar sobre cada archivo encontrado
    for i, (cpro, cmun, nmun, ruta_cat, ruta_shp) in enumerate(
        zip(df_archivos["cpro"], df_archivos["cmun_dgc"], 
            df_archivos["nmun"], df_archivos["ruta_cat"],
            df_archivos["ruta_shp"])):
        
        # Imprimir Datos del Municipio y Provincia  
        npro = df_archivos.loc[i, "npro"]
        idx_prov = int(df_archivos.loc[i, "idx_prov"])
        total_prov = int(df_archivos.loc[i, "total_prov"])
                
        QgsMessageLog.logMessage(
            f"Procesando ({cpro}) {npro} | "
            f"{idx_prov}/{total_prov} prov | "
            f"Global {i+1}/{num_municipios} | "
            f"Municipio: ({cpro}{cmun}) {nmun} ",
            "TIME", Qgis.Info)
        
        t1 = time.time()
        
        # Filtrado de Bienes Inmubles Urbanos Residenciales tabla 15
        try:
            # Obtener simpre el número de construcciones del municipio
            df14 = cat.lectura_ficheros_cat(ruta_cat, tabla_15 = False)
            n_ct = df14.shape[0]
            
            if val_t15: 
                #Lectura tabla T14 y T15
                df_14, df_15 = cat.lectura_ficheros_cat(ruta_cat)
                
                #
                n_tbi_15 = df_15.shape[0]
                df_15 = df_15[df_15["29_cn"] == "UR"]             # Filtro Urbano
                df_15 = df_15[df_15["428_grbice/coduso"] == "V"]  # Filtro viviendas
                
                nbi_ur = df_15.shape[0] # Número de BI Urbanos Residenciales 
                
                # Merge 
                df14 = df_14.merge(
                    df_15[["31_pc", "45_car"]],
                    left_on=['31_pc', '51_nobf'],
                    right_on=['31_pc', '45_car'],
                    how='inner'
                )
        except:
            msg = "Error en el procesamiento de la tabla tipo 14 o tipo 15"
            QgsMessageLog.logMessage(msg, "IVR", Qgis.Critical)
            continue
        
        # 2 Limpieza tabla 14: elementos comunes y sin clasificar construcciones
        # 2.1.1 Eliminar NA en 51_nobf (construcciones comunes)
        df14["105_tip"] = df14["105_tip"].astype(str).str.strip()
        df14 = df14.dropna(subset=["51_nobf"])
        valor_nah_51 = n_ct - df14.shape[0]
        
        # 2.1.2 Eliminar NA en 105_tip e información incompatibla
        df14 = df14.dropna(subset=["105_tip"])
        df14 = df14[df14["105_tip"].str.len() >= 5]
        
        # Quitar "00000" (sin tipología definida)
        df14 = df14[df14["105_tip"] != "00000"]
        
        # Mantener solo las que empiezan por 4 dígitos 
        mask_no_especiales = df14["105_tip"].str.match(r"^\d{4}")
        df14_f = df14[mask_no_especiales].copy()
        
        valor_nah_105 = n_ct - valor_nah_51 - df14_f.shape[0]
        
        del df14
        
        if num_municipios == 1:
            if task is not None:
                task.setProgress(15)
                if task.isCanceled():
                    return None, None, None, None
        
        # 2.1.4 Selección columnas  
        col_ft = ["24_cd", "26_cmc", "31_pc", "51_nobf", "79_aec", "84_stl", "105_tip"]
        col_ext = [c for c in col_ft if c in df14_f.columns]
        df14_f = df14_f[col_ext].copy()
        
        # 2.1.5 Creación y prepación variables clave 
        # 2.1.5.1 USO de la tipología contructiva 
        df14_f["105_uso"] = df14_f["105_tip"].str[:4].astype(str) 
        # 2.1.5.2 Coeficiente de valor de construcción 
        df14_f["105_cal"] = df14_f["105_tip"].str[4:5].astype(str)
        
        # Mapeo calidad a valores normales, se sustituye A, B, C
        
        val_especial = (df14_f["105_cal"].str.upper().isin(["A", "B", "C"]).any())
        
        mapa_calidad = {'A': 1, 'B': 1, 'C': 1, '1': 1, '2': 2, '3': 3, 
                        '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9}
                
        if val_especial:
            df14_f["105_cal_n"] = (df14_f["105_cal"].str.upper().map(mapa_calidad))
        else:
            df14_f["105_cal_n"] = df14_f["105_cal"]
    
        # 2.1.5.1 Paso de cadenas a número en variables númericas
        df14_f["79_aec"] = pd.to_numeric(df14_f["79_aec"], errors="coerce")
        df14_f["84_stl"] = pd.to_numeric(df14_f["84_stl"], errors="coerce")
        
        # 2.1.6 Variable temporal cálculo usos mixtos
        df14_f["tip_sup_cod"] = (
            df14_f["105_uso"].astype(str) + "_" + df14_f["84_stl"].astype(str))
        
        # 2.1.7 Añadir nombre de municipio 
        df14_f["nmun"] = nmun
        
        # 2.2 Simplificación agregación (Sólo valores computables)
        
        # Proporción filtrado  
        df14_f.shape[0]
        ftd_t14 = n_ct - df14_f.shape[0] 
        pp_ftd_t14 = round((ftd_t14 / n_ct) * 100, 3)
        
        # 2.2.1 Valorar  construcciones computables 
        lista_tpc = ['0121', '0122', '0111', '0112', '0131'] # Tipologias computables 
        df14_fc = df14_f[df14_f["105_uso"].isin(lista_tpc)] 
        # n_ctcp = df14_fc.shape[0]                             # Número de ct computables 
        
        # 2.1.2 Valorar otras construcciones a parte de computables 
        lista_refcat = df14_fc["31_pc"].dropna().unique().tolist()
        df14_f = df14_f[df14_f["31_pc"].isin(lista_refcat)] 
        n_ctc = df14_fc.shape[0]                             # Número de ct pc computables
        
        n_pc = len(lista_refcat) # Número de parcelas con superfcie computable 
        del df14_fc, lista_refcat
        
        if num_municipios == 1:
            if task is not None:
                task.setProgress(25)
                if task.isCanceled():
                    return None, None, None, None
        
        t2 = time.time()
        
        # 2.2.2 Aztualizar infomración en df_archivos 
        df_archivos.loc[i, "num_ct"] = n_ct               # Número de contrucciones 
        df_archivos.loc[i, "ct_51_nah"] = valor_nah_51    # Filtro ct comunes  
        df_archivos.loc[i, "ct_105_nah"] = valor_nah_105  # Filtro ct sin tipología  
        df_archivos.loc[i, "ct_nah"] =  ftd_t14           # Contrucciones tras filtrado  
        df_archivos.loc[i, "num_ctc"] = n_ctc             # Número de contrucciones computables
        # df_archivos.loc[i, "num_ctcp"] = n_ctcp         # Número de contrucciones parcelas computables (Próximas versiones, sin verificar)
        df_archivos.loc[i, "ct_nah_%"] = pp_ftd_t14       # % Contrucciones eliminadas  
        df_archivos.loc[i, "ct_esp"] = val_especial       # Contrucciones especiales  
        df_archivos.loc[i, "tm_ct"] = t2 - t1             # Tiempo procesamiento contrucciones  
        
        # 3. Tratamiento Bienes Inmubles (BI)
        # Número de Bienes Inmuble en función de construcciones 
        n_tbi_14 = df14_f.groupby(["31_pc", "51_nobf"]).ngroups 
        
        # 3.1 Simplificación agregación (Sólo valores computables)
        
        # 3.1.1 Valorar  construcciones computables 
        df14_f["refcat18"] = df14_f["31_pc"] + df14_f["51_nobf"]
        lista_tpc = ['0121', '0122', '0111', '0112', '0131'] # Tipologias computables 
        df14_fc = df14_f[df14_f["105_uso"].isin(lista_tpc)] 
        n_ctc = df14_fc.shape[0]                             # Número de ct computables 
        
        # 3.1.2 Valorar otras construcciones a parte de computables 
        lista_refcat = df14_fc["refcat18"].dropna().unique().tolist()
        df14_f = df14_f[df14_f["refcat18"].isin(lista_refcat)] 
        n_ctc = df14_fc.shape[0]                             # Número de ct computables
        
        n_pcc = len(lista_refcat) # Número de parcelas con superfcie computable 
        del df14_fc, lista_refcat
        
        # 3.2 Agrupación BI desde las construcciones 
        df_bi = (
            df14_f
            .groupby(["31_pc", "51_nobf"], as_index = False)
            .agg(
                # Nueva información generada (5)
                cpro = ("24_cd", "first"),
                cmun_dgc = ("26_cmc", "first"),
                nmun = ("nmun", "first"),
                n_ct = ("51_nobf", "size"),
                sup_bi = ("84_stl", "sum"),
                # IVR información agregada (4)
                # 1. Antigüedad Efectiva 
                ante_bi = ("79_aec", "mean"),
                # 2. Superficie Residencial Computable (Se cálcula despúes) 
                supc_bi = ("84_stl", "first"),        #
                tcus_bi=("105_uso",   lambda x: moda_segura(x, lista_tpc, tip=True)),
                # 3. Tipología Constructiva (USO)
                calp_bi=("105_cal",   lambda x: moda_segura(x, lista_tpc)),
                # 4.1 calidad (original)
                cvcn_bi=("105_cal_n", lambda x: moda_segura(x, lista_tpc)), 
                # 4.2 coef normalizado
                
                # Auxiliar, para cálcular uso predominante
                tsc = ("tip_sup_cod", lambda x: x),
            )
        )
        
        del df14_f
        
        if num_municipios == 1:
            if task is not None:
                task.setProgress(45)
                if task.isCanceled():
                    return None, None, None, None
        
        # 3.3   Depuración variables a nivel de BI 
        # 3.3.1 Cáculo de participación y asignación de uso predominante 
        df_bi, lista_columnas = procesar_uso_principal(
            df_bi,
            col_uso_sup = "tsc",
            valor_inicial = 0,
            col_uso_p = "uso_bi",
            col_por_uso_p = "p_uso_bi",
        )
        
        # 3.3.1 Cáculo de superficie residencial computable
        df_bi["supc_bi"] = df_bi[lista_tpc].sum(axis=1)
        n_bic = df_bi.shape[0]  # Número de BI con alguna ct computable
        
        # 3.3.2 Filtramos BI cuyo usos predominante es el residencial 
        df_bi = df_bi[df_bi["uso_bi"] == "01"].copy()
        
        n_bi01 = df_bi.shape[0] # Número de BI uso residencial predominate
        
        n_100 = (df_bi["p_uso_bi"] == 100).sum()   # Puros 
        n_mix = ((df_bi["p_uso_bi"] != 0) & (df_bi["p_uso_bi"] != 100)).sum() # Mixtos 
        
        media_mix = df_bi["p_uso_bi"].mask(
        (df_bi["p_uso_bi"] == 0) | (df_bi["p_uso_bi"] == 100)
        ).mean()
        
        # Añadir aquí lógica de filtrado usos mixtos 
        mask = df_bi["p_uso_bi"] < umbral_mix
        n_filtro = mask.sum() # Número de BI inferiroes al umbral
        df_bi = df_bi[~mask]  # Se queda con los superiores al umbral

    
        # 3.3.3 Calcular Coef. Valor Construcciones y limpiar df 
        df_bi = calculo_cvct(df_bi, dic_calidad) # Proceso externalizado 
        
        t3 = time.time()
        
        if num_municipios == 1:
            if task is not None:
                task.setProgress(65)
                if task.isCanceled():
                    return None, None, None, None
        
        # 3.4 Actualizar infomración en df_archivos para BI 
        df_archivos.loc[i, "n_tbi14"] = n_tbi_14     # Número de Bienes Inmubles totales T14
        if val_t15: 
            df_archivos.loc[i, "n_tbi15"] = n_tbi_15 # Número de Bienes Inmubles totales T15
        df_archivos.loc[i, "n_bi_c"] = n_bic         # Número de Bienes Inmubles con tip computable
        if val_t15:
            df_archivos.loc[i, "n_bi_ur"] = nbi_ur   # Número de Bienes Inmubles Urbanos Residenciales (T15)
        df_archivos.loc[i, "n_bi01"] = n_bi01        # Número de Bienes Inmubles uso residencial predominate
        df_archivos.loc[i, "n_bi01_p"] = n_100       # BI01 Puros 
        df_archivos.loc[i, "n_bi01_m"] = n_mix       # BI01 Mixtos 
        df_archivos.loc[i, "med_bi01_m"] = media_mix # Media de mixtos Bienes Inmubles uso residencial predominate
        df_archivos.loc[i, "n_bi01_fil"] = n_filtro  # Número de filtrados
        df_archivos.loc[i, "tm_bi"] = t3 - t2        # Tiempo procesamiento Bienes Inmuebles 

        # 4. Proceso de Normalización de Bienes Inmubles (BI)
        # En esta versión del completo el ivr_loc siempre se calculará 
        df_bi , param_loc, param_estadis = transformacion_sigmoidal_scipy(
            df_bi, ivr_loc = True, año_corte = año_corte)
        
        if num_municipios == 1:
            if task is not None:
                task.setProgress(75)
                if task.isCanceled():
                    return None, None, None, None
        
        t4 = time.time()
        
        # Info  normalización
        df_archivos.loc[i, "q1_spc"] = param_estadis["supc_bi"]["q1_spc"]
        df_archivos.loc[i, "q3_spc"] = param_estadis["supc_bi"]["q3_spc"] 
        df_archivos.loc[i, "iqr_spc"] = param_estadis["supc_bi"]["iqr_spc"]
        df_archivos.loc[i, "li_iqr_spc"] = param_estadis["supc_bi"]["li_iqr_spc"]    
        df_archivos.loc[i, "n_li_spc"] = param_estadis["supc_bi"]["n_li_spc"]  
        df_archivos.loc[i, "ls_iqr_spc"] = param_estadis["supc_bi"]["ls_iqr_spc"]  
        df_archivos.loc[i, "n_ls_spc"] = param_estadis["supc_bi"]["n_ls_spc"]  
        df_archivos.loc[i, "q05_spc"] = param_estadis["supc_bi"]["q05_spc"]  
        df_archivos.loc[i, "q95_spc"] = param_estadis["supc_bi"]["q95_spc"]  
        df_archivos.loc[i, "loc_spc"] = round(param_estadis["supc_bi"]["loc_spc"], 5)
        df_archivos.loc[i, "scale_spc"] = round(param_estadis["supc_bi"]["scale_spc"], 5) 
        df_archivos.loc[i, "n_fit_spc"] = param_estadis["supc_bi"]["n_fit_spc"]  
        df_archivos.loc[i, "pc_ft_spc"] = param_estadis["supc_bi"]["pc_ft_spc"]
        
        df_archivos.loc[i, "q1_ate"] = param_estadis["ante_bi"]["q1_ate"]
        df_archivos.loc[i, "q3_ate"] = param_estadis["ante_bi"]["q3_ate"] 
        df_archivos.loc[i, "iqr_ate"] = param_estadis["ante_bi"]["iqr_ate"]
        df_archivos.loc[i, "li_iqr_ate"] = param_estadis["ante_bi"]["li_iqr_ate"]    
        df_archivos.loc[i, "n_li_ate"] = param_estadis["ante_bi"]["n_li_ate"]  
        df_archivos.loc[i, "ls_iqr_ate"] = param_estadis["ante_bi"]["ls_iqr_ate"]  
        df_archivos.loc[i, "n_ls_ate"] = param_estadis["ante_bi"]["n_ls_ate"]  
        df_archivos.loc[i, "q05_ate"] = param_estadis["ante_bi"]["q05_ate"]  
        df_archivos.loc[i, "q95_ate"] = param_estadis["ante_bi"]["q95_ate"]  
        df_archivos.loc[i, "loc_ate"] = round(param_estadis["ante_bi"]["loc_ate"], 5)
        df_archivos.loc[i, "scale_ate"] = round(param_estadis["ante_bi"]["scale_ate"], 5) 
        df_archivos.loc[i, "n_fit_ate"] = param_estadis["ante_bi"]["n_fit_ate"]  
        df_archivos.loc[i, "pc_ft_ate"] = param_estadis["ante_bi"]["pc_ft_ate"]  
        
        df_archivos.loc[i, "q1_cv"] = param_estadis["cvcn_bi"]["q1_cv"]
        df_archivos.loc[i, "q3_cv"] = param_estadis["cvcn_bi"]["q3_cv"]
        df_archivos.loc[i, "iqr_cv"] = param_estadis["cvcn_bi"]["iqr_cv"]
        df_archivos.loc[i, "li_iqr_cv"] = param_estadis["cvcn_bi"]["li_iqr_cv"]    
        df_archivos.loc[i, "n_li_cv"] = param_estadis["cvcn_bi"]["n_li_cv"]  
        df_archivos.loc[i, "ls_iqr_cv"] = param_estadis["cvcn_bi"]["ls_iqr_cv"]  
        df_archivos.loc[i, "n_ls_cv"] = param_estadis["cvcn_bi"]["n_ls_cv"]  
        df_archivos.loc[i, "q05_cv"] = param_estadis["cvcn_bi"]["q05_cv"]  
        df_archivos.loc[i, "q95_cv"] = param_estadis["cvcn_bi"]["q95_cv"]  
        df_archivos.loc[i, "loc_cv"] = round(param_estadis["cvcn_bi"]["loc_cv"], 5)
        df_archivos.loc[i, "scale_cv"] = round(param_estadis["cvcn_bi"]["scale_cv"], 5) 
        df_archivos.loc[i, "n_fit_cv"] = param_estadis["cvcn_bi"]["n_fit_cv"]  
        df_archivos.loc[i, "pc_ft_cv"] = param_estadis["cvcn_bi"]["pc_ft_cv"] 
        
        
        df_archivos.loc[i, "ivr_gau_media"] = df_bi["ivr_gau"].mean()      # Número de parcelas computables   
        df_archivos.loc[i, "ivr_gau_mediana"] = df_bi["ivr_gau"].median()  # Número de parcelas computables   
        df_archivos.loc[i, "ivr_loc_media"] = df_bi["ivr_loc"].mean()      # Número de parcelas computables   
        df_archivos.loc[i, "ivr_loc_mediana"] = df_bi["ivr_loc"].median()  # Número de parcelas computables   
        
        df_archivos.loc[i, "tm_nor"] = t4 - t3      # Tiempo procesamiento Normalización 
        
        # 5. Proceso de agregación a nivel parcea (PC)
        
        # 5.1 Agregación de BI a Parcelas (PC) 
        # Claro y si no piden IVR LOC Habría que hacer desarrollo paralelo       Revisar 
        
        df_pc = (
            df_bi
            .groupby(["31_pc"], as_index = False)
            .agg(
                # Nueva información generada (5)
                cpro = ("cpro", "first"),
                cmun_dgc = ("cmun_dgc", "first"),
                nmun = ("nmun", "first"),
                n_ct = ("n_ct", "sum"),
                n_bi = ("51_nobf", "size"),
                sup_pc = ("sup_bi", "sum"),
                # IVR información agregada (4)
                # 1. Antigüedad Efectiva 
                ante_pc = ("ante_bi", "mean"),
                # 2. Superficie Residencial Computable (Se cálcula despúes) 
                supc_pc = ("supc_bi", "mean"),
                # 3. Tipología Constructiva (USO)
                tcus_pc = ("tcus_bi",   lambda x: moda_segura(x, lista_tpc, tip=True)),
                # 4.1 calidad (original)
                calp_pc = ("calp_bi",   lambda x: moda_segura(x, lista_tpc)),
                # 4.2 coef normalizado
                cvcn_pc = ("cvcn_bi", lambda x: moda_segura(x, lista_tpc)), 
                # IVR por parcelas
                
                # Variables normalizadas (Asignación pesos usurio)
                # GAU
                ante_n_gau = ("ante_bi_tfg", "mean"),
                supc_n_gau = ("supc_bi_tfg", "mean"),
                cvct_n_gau = ("cvcn_bi_tfg", "mean"),
                # LOC
                ante_n_loc = ("ante_bi_tfm", "mean"),
                supc_n_loc = ("supc_bi_tfm", "mean"),
                cvct_n_loc = ("cvcn_bi_tfm", "mean"),
                # Total 
                ivr_gau = ("ivr_gau", "mean"),
                ivr_loc = ("ivr_loc", "mean"),
            )
        )
        
        # Para facilitar coherencia usuario se da la variable trasformada 
        df_pc["ante_n_gau"] = 1 - df_pc["ante_n_gau"]
        df_pc["supc_n_gau"] = 1 - df_pc["supc_n_gau"]
        df_pc["cvct_n_gau"] = 1 - df_pc["cvct_n_gau"]
        
        df_pc["ante_n_loc"] = 1 - df_pc["ante_n_loc"]
        df_pc["supc_n_loc"] = 1 - df_pc["supc_n_loc"]
        df_pc["cvct_n_loc"] = 1 - df_pc["cvct_n_loc"]
        
        if num_municipios == 1:
            if task is not None:
                task.setProgress(85)
                if task.isCanceled():
                    return None, None, None, None
        
        # 5.2.1 Lectura y unión del Parcelario Urbano 
        try:
            df_pcl = cat.leer_parcela_shp_desde_zip(
                ruta_shp, columns = ["REFCAT", "geometry"])
            
        except Exception as e:
            print(f"Error en lectura Parcelario ruta:n\ {ruta_shp}: {e}")
            continue
        
        n_pcl = df_pcl.shape[0] # Númer ode parcelas en parcelariao 
        
        # 5.2.2 Lectura del Parcelario Urbano 
         
        df_ivr = df_pc.merge(
            df_pcl,
            left_on = "31_pc",
            right_on = "REFCAT",
            how = "inner"
        )
        
        n_biu = df_pc["n_bi"].sum() - df_ivr["n_bi"].sum()
        n_pcu = df_pc.shape[0] - df_ivr.shape[0] # Igual o posivo
        
        print(f"Parcelario OK, Diff BI {n_biu}, PC {n_pcu}")

        # 5.3 Limpieza y selección de variables finales
        
        # Todas las columnas
        cols_ivr = ["31_pc", "cpro", "cmun_dgc", "nmun", "n_ct", "n_bi", 
                    "sup_pc","ante_pc", "supc_pc", "tcus_pc","calp_pc", 
                    "cvcn_pc", "ante_n_gau","supc_n_gau", "cvct_n_gau", 
                    "ante_n_loc", "supc_n_loc", "cvct_n_loc", "ivr_gau", 
                    "ivr_loc", "REFCAT", "geometry", ]

        cols_ivr = [c for c in cols_ivr if c != "REFCAT"] # Elimianr REFCAT
        cols_ivr = ["refcat" if c == "31_pc" else c for c in cols_ivr]  # Renombre 
        cols_ivr = ["geom" if c == "geometry" else c for c in cols_ivr] # Renombre
        cols_ivr = [c for c in cols_ivr if c != "geom"] + ["geom"]

        # 5. Aplicar al dataframe
        df_ivr = df_ivr.rename(columns = {"REFCAT": "refcat", "geometry": "geom"} 
                               )[cols_ivr]

        df_ivr = gpd.GeoDataFrame(
            df_ivr,
            geometry = "geom",
            crs = df_pcl.crs
        )
        
        crs = int(crs_ui.split(":")[1].split(")")[0])
        df_ivr = df_ivr.to_crs(epsg = crs)
        
        if num_municipios == 1:
            if task is not None:
                task.setProgress(90)
                if task.isCanceled():
                    return None, None, None, None
        
        
        #  Clasificador GAU
        
        if metodo != "Sin clasificar":
 
            df_ivr[col_class] = pd.cut(
                df_ivr[col_ivr],       # IVR GAU o IVR LOC
                bins = clases,
                labels = etiqueta,
                include_lowest = True, # Valor mínimo no aparece ahora como NA
                right = True           # (izquierda , derecha]
            )
            
            # Reordenar nueva columna
            # Lista columnas 
            cols = list(df_ivr.columns)
            cols.remove(col_class)
            # Busca geom (siempre la última)
            idx_geom = cols.index("geom")
            cols.insert(idx_geom, col_class)
            # Reordena columna
            df_ivr = df_ivr[cols]
    
            # Resumen variables por mun
            
            dic_clases = (
                df_ivr[col_class]
                .value_counts()
                .sort_index()
                .to_dict()
            )
    
            for nombre_etiqueta, valor in dic_clases.items():
                df_archivos.loc[i, f"clase_{nombre_etiqueta}"] = valor
        
        
        t5 = time.time()
        
        df_archivos.loc[i, "n_pcl"] = n_pcl    # Número de parcelas en parcelario
        df_archivos.loc[i, "num_pcc"] = n_pcc  # Parcelas computables
        df_archivos.loc[i, "num_pc"] = n_pc    # Parcelas residenciales procesadas
        # Se descartan en primera versión al no estar seguro de dichas estadísticas
        # df_archivos.loc[i, "n_pcu"] = n_pcu    # Parcelas NO unidas (perdidas)
        # df_archivos.loc[i, "n_biu"] = n_biu    # Número de NO BI unidos por parcelario
        df_archivos.loc[i, "tm_pc"] = t5 - t4  # Tiempo procesamiento Normalización
        
        # Añadir al acumulador global
        
        dfs_bi.append(df_bi) # df14_f | df_bi | df_pc
        dfs_ivr.append(df_ivr) # df14_f | df_bi | df_ivr
        
        # 95 Ya que luego faltan tareas 
        
        if num_municipios == 1:
            if task is not None:
                task.setProgress(95)
                if task.isCanceled():
                    return None, None, None, None
                
            QgsMessageLog.logMessage(
                f"Procesado: CT {(t2-t1):.2f}s | BI + IVR {(t4-t2):.2f}s | PC {(t5-t4):.2f}s\n",
                "TIME", Qgis.Info)
        else:
            progreso_decimal = min(95, max(1, ((i + 1) / num_municipios) * 95))
            progreso_entero = int(progreso_decimal)
                 
            if task is not None:
                task.setProgress(progreso_entero)
                if task.isCanceled():
                    return None, None, None, None
            
            QgsMessageLog.logMessage(
                f"Progreso municipios: {((i + 1) / num_municipios) * 100:.2f}% | "
                f"Progreso provincial: {((idx_prov) / total_prov) * 100:.2f}% | "
                f"Progreso herramienta: {(progreso_decimal):.2f}%",
                "TIME", Qgis.Info)
            
            QgsMessageLog.logMessage(
                f"Procesado: CT {(t2-t1):.2f}s | BI + IVR {(t4-t2):.2f}s | PC {(t5-t4):.2f}s\n",
                "TIME", Qgis.Info)
          
    # Esto esta mal 
    tf = time.time()
    QgsMessageLog.logMessage(
    f"Finalizado en {((tf - t0)/60):.2f} m ",
    "TIME", Qgis.Info)
    
    # -------------------------------------------------------------------
    # 2) CONCATENAR TODOS LOS RESULTADOS EN UN SOLO DATAFRAME
    # -------------------------------------------------------------------
    try:
        dfs_bi = pd.concat(dfs_bi, ignore_index=True) if dfs_bi else pd.DataFrame()
        dfs_ivr = pd.concat(dfs_ivr, ignore_index=True) if dfs_ivr else pd.DataFrame()
    except Exception:
        print("Error")
    
    df_pro = (
        dfs_bi
        .groupby("cpro", as_index = False)
        .agg(
            # Nueva información generada (5)
            cpro = ("cpro", "first"),
            n_mun_pr = ("cmun_dgc", "nunique"),
            n_ct_pr = ("n_ct", "sum"),
            n_bi_r_pr = ("51_nobf", "size"),
            sup_pr_sum = ("sup_bi", "sum"),
            sup_pr_med = ("sup_bi", "mean"),
            # IVR información agregada (4)
            # 1. Antigüedad Efectiva 
            ante_pr_med = ("ante_bi", "mean"),
            # 2. Superficie Residencial Computable (Se cálcula despúes) 
            supc_pr_sum = ("supc_bi", "sum"),
            supc_pr_med = ("supc_bi", "mean"),
            # 3. Tipología Constructiva (USO)
            tcus_pr = ("tcus_bi",   lambda x: moda_segura(x, lista_tpc, tip=True)),
            # 4.1 calidad (original)
            calp_pr = ("calp_bi",   lambda x: moda_segura(x, lista_tpc)),
            # 4.2 coef normalizado
            cvcn_pr = ("cvcn_bi", lambda x: moda_segura(x, lista_tpc)), 
            # IVR por parcelas
            ivr_gau = ("ivr_gau", "mean"),
            ivr_loc = ("ivr_loc", "mean"),
        )
    )
    
    # Limpiza csv 
    # Reordenar rutas csv mun
    cols = [c for c in df_archivos.columns if c not in ["ruta_cat", "ruta_shp"]]
    cols.extend(["ruta_cat", "ruta_shp"])
    df_archivos = df_archivos[cols]
    
    # Dar nombre provincias y reordenar cvs provincias
    
    df_pro = df_pro.merge(
        df_archivos[['cpro', 'npro']].drop_duplicates(subset = 'cpro'), 
        on='cpro', 
        how='left'
    )

    cols = df_pro.columns.tolist()
    cols.remove('npro')
    cols.insert(cols.index('cpro') + 1, 'npro')
    df_pro = df_pro[cols]
    
    if metodo != "Sin clasificar":
        return df_archivos, dfs_bi, dfs_ivr, df_pro, dic_gau, col_class
    else: 
        return df_archivos, dfs_bi, dfs_ivr, df_pro
    
def log_estado_ui(self, col_ivr):
    """Imprime mensaje en panel de registro de Qgis, para ver que datos han
    sido seleccionado el usuario de modo informativo o para ver errores"""
    mensaje = [
        "Proceso en segundo plano ACTIVADO",
        f"Ruta entrada: {self.input_path}",
        f"Ruta salida: {self.output_path}",
    ]

    if self.metodo != "Sin clasificar":
        mensaje.append(
            f"Método de clasificación: {self.metodo} | "
            f"Clases: {self.clases} | "
            f"Variable a visualizar: {col_ivr}"
        )
    else:
        mensaje.append("Sin aplicar Clasificador GAU")

    mensaje.extend([
        f"Filtro T15 Bines Residenciales: {self.val_t15}",
        f"Filtro BI residenciales mixtos: {self.val_mix}",
        f"EPSG aplicado: {self.val_crs}",
        f"Fit sigmoides: {self.fsig}",
        f"Fit normalización: {self.fnor}",
        f"CSV Municipios: {self.csvmun}",
        f"CSV Provincias: {self.csvpro}",
    ])

    QgsMessageLog.logMessage("\n".join(mensaje), "IVR", Qgis.Info)

def informacion_capa_ivr(gdf, colcl, inf_add, inf_org, inf_nor, inf_cls):
    "Filtra la información que el usuario necesita del IVR"
    # Columnas por defecto 
    lista_defecto = ["refcat", "cpro", "cmun_dgc", "nmun"]
    lista_ivr_geo = ["ivr_gau", "ivr_loc", "geom"]

    # Columnas posibles 
    list_add = ["n_ct", "n_bi", "sup_pc"]
    list_org = ["ante_pc", "supc_pc", "tcus_pc", "calp_pc", "cvcn_pc"]
    list_nor = [
        "ante_n_gau", "supc_n_gau", "cvct_n_gau",
        "ante_n_loc", "supc_n_loc", "cvct_n_loc"
    ]
    
    list_cls = [colcl] # Nombre de la columna col_class

    # Gestión lógica de adicción columnas
    col_sec = lista_defecto.copy()

    if inf_add:
        col_sec += list_add
    if inf_org:
        col_sec += list_org
    if inf_nor:
        col_sec += list_nor
    if inf_cls:
        col_sec += list_cls

    # Añadir IVR + geometría al final SIEMPRE
    col_sec += lista_ivr_geo

    # Quitar duplicados manteniendo orden
    col_sec = list(dict.fromkeys(col_sec))

    # Quedarse solo con las columnas que existen en el gdf
    col_sec = [c for c in col_sec if c in gdf.columns]

    return gdf[col_sec]  
    
# Diccionarios principales
# Real Decreto 1020/1993
dic_calidad = {
    '0111': {
        '1': 1.65, '2': 1.40, '3': 1.20, '4': 1.05, '5': 0.95,
        '6': 0.85, '7': 0.75, '8': 0.65, '9': 0.55
    },
    '0112': {
        '1': 1.60, '2': 1.35, '3': 1.15, '4': 1.00, '5': 0.90,
        '6': 0.80, '7': 0.70, '8': 0.60, '9': 0.50
    },
    '0121': {
        '1': 2.15, '2': 1.80, '3': 1.45, '4': 1.25, '5': 1.10,
        '6': 0.90, '7': 0.80, '8': 0.70, '9': 0.60
    },
    '0122': {
        '1': 2.00, '2': 1.65, '3': 1.35, '4': 1.15, '5': 1.05,
        '6': 0.95, '7': 0.85, '8': 0.75, '9': 0.65
    },
    '0131': {
        '1': 1.35, '2': 1.10, '3': 0.90, '4': 0.75, '5': 0.65,
        '6': 0.60, '7': 0.55, '8': 0.40, '9': 0.35}}
# Cálculado datos de II Semetres de 2025
clasificador_gau = {
    'Cuantiles': {   
        2: [
            (0.00000, 0.47838, '#fff5eb'),
            (0.47838, 1.00000, '#7f2704'),
        ],
        3: [
            (0.00000, 0.36696, '#fff5eb'),
            (0.36696, 0.60407, '#fd9243'),
            (0.60407, 1.00000, '#7f2704'),
        ],
        4: [
            (0.00000, 0.31120, '#fff5eb'),
            (0.31120, 0.47838, '#fdbd83'),
            (0.47838, 0.67559, '#ee6511'),
            (0.67559, 1.00000, '#7f2704'),
        ],
        5: [
            (0.00000, 0.27394, '#fff5eb'),
            (0.27394, 0.41148, '#fdd2a5'),
            (0.41148, 0.54967, '#fd9243'),
            (0.54967, 0.72013, '#df5005'),
            (0.72013, 1.00000, '#7f2704'),
        ],
        6: [
            (0.00000, 0.24560, '#fff5eb'),
            (0.24560, 0.36696, '#fddab6'),
            (0.36696, 0.47838, '#fdab67'),
            (0.47838, 0.60407, '#f67723'),
            (0.60407, 0.74999, '#d14501'),
            (0.74999, 1.00000, '#7f2704'),
        ],
        7: [
            (0.00000, 0.22331, '#fff5eb'),
            (0.22331, 0.33576, '#fee0c2'),
            (0.33576, 0.43024, '#fdbd83'),
            (0.43024, 0.52796, '#fd9243'),
            (0.52796, 0.64565, '#ee6511'),
            (0.64565, 0.77106, '#c24002'),
            (0.77106, 1.00000, '#7f2704'),
        ],
        8: [
            (0.00000, 0.20440, '#fff5eb'),
            (0.20440, 0.31120, '#fee4ca'),
            (0.31120, 0.39449, '#fdc997'),
            (0.39449, 0.47838, '#fda45d'),
            (0.47838, 0.56960, '#f87f2c'),
            (0.56960, 0.67559, '#e5590a'),
            (0.67559, 0.78713, '#b83c02'),
            (0.78713, 1.00000, '#7f2704'),
        ],
        9: [
            (0.00000, 0.18746, '#fff5eb'),
            (0.18746, 0.29089, '#fee7cf'),
            (0.29089, 0.36696, '#fdd2a5'),
            (0.36696, 0.44043, '#fdb271'),
            (0.44043, 0.51591, '#fd9243'),
            (0.51591, 0.60407, '#f3701b'),
            (0.60407, 0.70016, '#df5005'),
            (0.70016, 0.79953, '#b13a03'),
            (0.79953, 1.00000, '#7f2704'),
        ],
        10: [
            (0.00000, 0.17300, '#fff5eb'),
            (0.17300, 0.27394, '#fee8d2'),
            (0.27394, 0.34544, '#fdd6af'),
            (0.34544, 0.41148, '#fdbd83'),
            (0.41148, 0.47838, '#fda057'),
            (0.47838, 0.54967, '#fa8331'),
            (0.54967, 0.63285, '#ee6511'),
            (0.63285, 0.72013, '#d94901'),
            (0.72013, 0.80968, '#ab3803'),
            (0.80968, 1.00000, '#7f2704'),
        ],
    },
    'Jenks': {
        2: [
            (0.00000, 0.50236, '#fff5eb'),
            (0.50236, 1.00000, '#7f2704'),
        ],
        3: [
            (0.00000, 0.34696, '#fff5eb'),
            (0.34696, 0.62136, '#fd9243'),
            (0.62136, 1.00000, '#7f2704'),
        ],
        4: [
            (0.00000, 0.26152, '#fff5eb'),
            (0.26152, 0.46857, '#fdbd83'),
            (0.46857, 0.68394, '#ee6511'),
            (0.68394, 1.00000, '#7f2704'),
        ],
        5: [
            (0.00000, 0.22424, '#fff5eb'),
            (0.22424, 0.39876, '#fdd2a5'),
            (0.39876, 0.56806, '#fd9243'),
            (0.56806, 0.74286, '#df5005'),
            (0.74286, 1.00000, '#7f2704'),
        ],
        6: [
            (0.00000, 0.19148, '#fff5eb'),
            (0.19148, 0.33751, '#fddab6'),
            (0.33751, 0.47305, '#fdab67'),
            (0.47305, 0.61753, '#f67723'),
            (0.61753, 0.76887, '#d14501'),
            (0.76887, 1.00000, '#7f2704'),
        ],
        7: [
            (0.00000, 0.17428, '#fff5eb'),
            (0.17428, 0.30492, '#fee0c2'),
            (0.30492, 0.42413, '#fdbd83'),
            (0.42413, 0.54743, '#fd9243'),
            (0.54743, 0.67493, '#ee6511'),
            (0.67493, 0.80172, '#c24002'),
            (0.80172, 1.00000, '#7f2704'),
        ],
        8: [
            (0.00000, 0.16419, '#fff5eb'),
            (0.16419, 0.28497, '#fee4ca'),
            (0.28497, 0.39012, '#fdc997'),
            (0.39012, 0.49074, '#fda45d'),
            (0.49074, 0.59420, '#f87f2c'),
            (0.59420, 0.70326, '#e5590a'),
            (0.70326, 0.81572, '#b83c02'),
            (0.81572, 1.00000, '#7f2704'),
        ],
        9: [
            (0.00000, 0.15579, '#fff5eb'),
            (0.15579, 0.26689, '#fee7cf'),
            (0.26689, 0.36025, '#fdd2a5'),
            (0.36025, 0.44778, '#fdb271'),
            (0.44778, 0.53635, '#fd9243'),
            (0.53635, 0.62914, '#f3701b'),
            (0.62914, 0.72634, '#df5005'),
            (0.72634, 0.82814, '#b13a03'),
            (0.82814, 1.00000, '#7f2704'),
        ],
        10: [
            (0.00000, 0.13736, '#fff5eb'),
            (0.13736, 0.23574, '#fee8d2'),
            (0.23574, 0.32090, '#fdd6af'),
            (0.32090, 0.40076, '#fdbd83'),
            (0.40076, 0.48151, '#fda057'),
            (0.48151, 0.56737, '#fa8331'),
            (0.56737, 0.65804, '#ee6511'),
            (0.65804, 0.74978, '#d94901'),
            (0.74978, 0.84347, '#ab3803'),
            (0.84347, 1.00000, '#7f2704'),
        ],
    },
    'Intervalos Iguales': {
        2: [
            (0.00000, 0.50348, '#fff5eb'),
            (0.50348, 1.00000, '#7f2704'),
        ],
        3: [
            (0.00000, 0.33863, '#fff5eb'),
            (0.33863, 0.66833, '#fd9243'),
            (0.66833, 1.00000, '#7f2704'),
        ],
        4: [
            (0.00000, 0.25620, '#fff5eb'),
            (0.25620, 0.50348, '#fdbd83'),
            (0.50348, 0.75076, '#ee6511'),
            (0.75076, 1.00000, '#7f2704'),
        ],
        5: [
            (0.00000, 0.20675, '#fff5eb'),
            (0.20675, 0.40457, '#fdd2a5'),
            (0.40457, 0.60239, '#fd9243'),
            (0.60239, 0.80022, '#df5005'),
            (0.80022, 1.00000, '#7f2704'),
        ],
        6: [
            (0.00000, 0.17378, '#fff5eb'),
            (0.17378, 0.33863, '#fddab6'),
            (0.33863, 0.50348, '#fdab67'),
            (0.50348, 0.66833, '#f67723'),
            (0.66833, 0.83319, '#d14501'),
            (0.83319, 1.00000, '#7f2704'),
        ],
        7: [
            (0.00000, 0.15022, '#fff5eb'),
            (0.15022, 0.29153, '#fee0c2'),
            (0.29153, 0.43283, '#fdbd83'),
            (0.43283, 0.57413, '#fd9243'),
            (0.57413, 0.71543, '#ee6511'),
            (0.71543, 0.85674, '#c24002'),
            (0.85674, 1.00000, '#7f2704'),
        ],
        8: [
            (0.00000, 0.13256, '#fff5eb'),
            (0.13256, 0.25620, '#fee4ca'),
            (0.25620, 0.37984, '#fdc997'),
            (0.37984, 0.50348, '#fda45d'),
            (0.50348, 0.62712, '#f87f2c'),
            (0.62712, 0.75076, '#e5590a'),
            (0.75076, 0.87440, '#b83c02'),
            (0.87440, 1.00000, '#7f2704'),
        ],
        9: [
            (0.00000, 0.11882, '#fff5eb'),
            (0.11882, 0.22873, '#fee7cf'),
            (0.22873, 0.33863, '#fdd2a5'),
            (0.33863, 0.44853, '#fdb271'),
            (0.44853, 0.55843, '#fd9243'),
            (0.55843, 0.66833, '#f3701b'),
            (0.66833, 0.77824, '#df5005'),
            (0.77824, 0.88814, '#b13a03'),
            (0.88814, 1.00000, '#7f2704'),
        ],
        10: [
            (0.00000, 0.10783, '#fff5eb'),
            (0.10783, 0.20675, '#fee8d2'),
            (0.20675, 0.30566, '#fdd6af'),
            (0.30566, 0.40457, '#fdbd83'),
            (0.40457, 0.50348, '#fda057'),
            (0.50348, 0.60239, '#fa8331'),
            (0.60239, 0.70130, '#ee6511'),
            (0.70130, 0.80022, '#d94901'),
            (0.80022, 0.89913, '#ab3803'),
            (0.89913, 1.00000, '#7f2704'),
        ],
    },
}