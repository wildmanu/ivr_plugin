# -*- coding: utf-8 -*-

"""
Archivo ivr_fig.py

Este archivo alberga todas las funciones relativas a la generación de las 
figuras creadas para el IVR plugin.

Fecha creación:     25/01/2026
Fecha modificación: 08/02/2026 --> Última modificación 

Listado modificaciones y avances 

1) 07/02/02026 
- Añade nota de atípicos en leyenda para "visualizar_normalizacion"
- Añade año de corte en "inf_aux_ivr" hacerlo automático
- Se añaden comentarios con posibles mejoras a futuro 
2) 08/02/2026 
- Se añade función "" para generar documentación CSV en .txt

@author: manuel
"""
# Módulos requeridos 

from difflib import SequenceMatcher
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.transforms import ScaledTranslation
from scipy.stats import logistic
import os, json, time
from datetime import datetime

from . import ivr_cat as cat

# Funciones 

__all__ = [
    "inf_aux_ivr",
    "parametos_sigmoides",
    "visualizar_normalizacion",
    "visualizar_normalizacion",
    "generar_info_txt",
           ]

# Gestor central de la información auxiliar 

def inf_aux_ivr(df_archivos, dfs_bi, df_pro, parametros_reg,
                parametros_estadisticos, output, metodo, rangos, fig_sig, fig_nor,
                csv_mun, csv_prov):
    """
    Gestiona lógica solicitada por el usuario, núcleo central para la generación 
    de las figuras y csv. 

    """
    # Generar carpetas infromación auxiliar
    carpeta_auxiliar = os.path.join(output, "Información Auxiliar IVR")
    
    if fig_sig or fig_nor:
        carpeta_figuras = os.path.join(carpeta_auxiliar, "Figuras")
        os.makedirs(carpeta_figuras, exist_ok=True)
        
    if csv_mun or csv_prov:
        carpeta_csv = os.path.join(carpeta_auxiliar, "CSV")
        os.makedirs(carpeta_csv, exist_ok=True)
        
    #
    ruta_txt = os.path.join(output, "leeme.txt")
    generar_info_txt(
        ruta_salida = ruta_txt,
        titulo = "DOCUMENTACIÓN DEL IVR PLUGIN",
        columnas_info = columnas_principales,
        inf_mun = csv_mun,
        columnas_mun = columnas_municipios,
        inf_prov = csv_prov,
        columnas_prov=columnas_provincias,
        autor = "Manuel Blasco Jiménez (UAH), Francisco Israel Aguilera Benavente (UAH) y Nikolai Shurupov (UAH).",
        colaboradores = "José Prada Trigo (UVa), Irene Sánchez Ondoño (UVa), Julia Clemente Párraga (UAH).",
        version="1.0.0"
    )

        
    dic_parametros = {
        "spc": parametos_sigmoides(
            df_archivos, loc = "loc_spc", scale = "scale_spc"),
        "ate": parametos_sigmoides(
            df_archivos, loc = "loc_ate", scale = "scale_ate"),
        "cv":  parametos_sigmoides(
            df_archivos, loc = "loc_cv", scale = "scale_cv")
    }

    # Lógica para generar figuras  
    if fig_sig:
        
        ruta_sigmoides = os.path.join(carpeta_figuras, "ivr_funciones.png")
        
        # Calculado el 07/02/2026 con datos de II semestre de 2025 de catastro
        parametros_globales = {
        "supc_bi": {"loc": 87.853863963425700, "scale": 16.5700712996760620},
        "ante_bi": {"loc": 1984.5976385822298, "scale": 11.0895156036098110},
        "cvcn_bi": {"loc": 0.9907060595134738, "scale": 0.06898716437223629},
        }

        specs = [
            {"tipo": "spc", "variable": "supc_bi", "xlabel": "Superficie habitable"},
            {"tipo": "ate", "variable": "ante_bi", "xlabel": "Antigüedad efectiva"},
            {"tipo": "cv",  "variable": "cvcn_bi", "xlabel": "Coeficiente de valor"},
        ]
        
        any_corte = 1 + datetime.now().year # Por si acaso se usan datos del mismo año
        
        fig, axes, res = visualizar_sigmoides_scipy(
            dfs_bi = dfs_bi,
            df_archivos = df_archivos,
            dic_parametros=dic_parametros,
            parametros_globales=parametros_globales,
            parametros_estadisticos = parametros_estadisticos,
            parametros_reg = parametros_reg,
            specs = specs,
            bins = 45,
            xmax_ate = any_corte,     # Poner otro año si son datos antigüos
            col_municipio = "nmun",
            figsize = None,
            wspace = 0.10,         
            bottom = 0.32,        
            top = 0.89, 
            output = ruta_sigmoides
        )
                                      
    if fig_nor:
        
        # Establecer rutas: 
        ruta_normalizacion = os.path.join(carpeta_figuras, "ivr_normalizacion.png")
        
        # Diccioanrio pametors variables normalizadas
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        ruta_dic_nor = os.path.join(ruta_base, "dic", "dic_nor_param.json")

        with open(ruta_dic_nor, "r",
                  encoding="utf-8") as archivo:
            dic_nor_param = json.load(archivo)

        # Generar figura 
        visualizar_normalizacion(
            dfs_bi,
            dic_parametros,
            dic_nor_param,
            metodo = metodo,
            rangos = rangos,
            bins = 45,
            bins_cv = 20,
            label_right = "Densidad de BI para el Índice de Vulenrabilidad Residencial (IVR)",
            titulo = "Proceso de normalización variables originales y normalizadas del IVR",
            titulo_x = 0.535,
            titulo_y = 0.95,
            wspace = 0.125,
            hspace = 0.125,
            right_margin = 0.96,
            label_right_x = 0.980,
            output = ruta_normalizacion,
            dpi = 400
        )
    
    # Lógica para generar csv 
    if csv_mun:
        df_archivos.to_csv(os.path.join(carpeta_csv, "info_ivr_municipios.csv"),
                           index = False, sep = ";", encoding = "utf-8-sig")
    if csv_prov:
        df_pro.to_csv(os.path.join(carpeta_csv, "info_ivr_provincias.csv"),
                           index = False, sep = ";", encoding = "utf-8-sig")

# Funciones para generación figuras 

def parametos_sigmoides(df_archivos, loc, scale, eps = 1e-12):
    """
    Extrae los parametros clave de las funciones logisticas para las variables 
    clave del IVR para representarlo.
    - Parametros
    df_archivos : Dataframe generado de la iteración de todos los municipios 
                  leidos 
    loc y scale : Columnas dónde alberga cada municipio los valores calve de la 
                  función sigmoidal.
                  
    PD: Nueva función asegura que no haya función no se represente algún municipio
    sin dispersión, a su vez, evita que se represente dos municpios en la tabla 
    cuando hay 3 o más. 


    - Devuelve
    dic_param_sig : Devuelve los parametos clave de la sigmoide para todos
    los municipios Máximo, Mínimo y Mediana,  así como la información de sus 
    cortes y nombre facilitar su representación. 

    """
    
    n_mun = df_archivos.shape[0]

    # --- 1) Candidatos válidos (scale > eps) ---
    if n_mun > 3:
        df_validos = df_archivos[df_archivos[scale] > eps].copy()
        if df_validos.empty:
            df_validos = df_archivos.copy()
    else:
        df_validos = df_archivos.copy()

    usados = set()

    # --- 2) MAX: loc máximo ---
    idx_max = df_validos[loc].idxmax()
    usados.add(idx_max)

    # --- 3) MIN: loc mínimo, evitando repetir MAX ---
    df_tmp = df_validos.drop(index=list(usados), errors="ignore")
    if not df_tmp.empty:
        idx_min = df_tmp[loc].idxmin()
    else:
        idx_min = idx_max
    usados.add(idx_min)

    # --- 4) MED: más cercano a la mediana, evitando repetir MAX/MIN ---
    mediana = df_validos[loc].median()
    df_tmp = df_validos.drop(index=list(usados), errors="ignore")
    if not df_tmp.empty:
        idx_med = (df_tmp[loc] - mediana).abs().idxmin()
    else:
        idx_med = idx_max
    usados.add(idx_med)

    # --- 5) Extraer valores ---
    loc_max = df_archivos.loc[idx_max, loc]
    scale_max = df_archivos.loc[idx_max, scale]
    nmun_max = df_archivos.loc[idx_max, "nmun"]
    cpro_max = df_archivos.loc[idx_max, "cpro"]
    cmun_max = df_archivos.loc[idx_max, "cmun_dgc"]

    loc_mediana = df_archivos.loc[idx_med, loc]
    scale_mediana = df_archivos.loc[idx_med, scale]
    nmun_mediana = df_archivos.loc[idx_med, "nmun"]
    cpro_mediana = df_archivos.loc[idx_med, "cpro"]
    cmun_mediana = df_archivos.loc[idx_med, "cmun_dgc"]

    loc_min = df_archivos.loc[idx_min, loc]
    scale_min = df_archivos.loc[idx_min, scale]
    nmun_min = df_archivos.loc[idx_min, "nmun"]
    cpro_min = df_archivos.loc[idx_min, "cpro"]
    cmun_min = df_archivos.loc[idx_min, "cmun_dgc"]

    # --- 6) Límites (igual que tu lógica) ---
    tipo = loc.split("_", 1)[1]
    limite_inferior = f"li_iqr_{tipo}"
    limite_superior = f"ls_iqr_{tipo}"

    # OJO: si alguna columna no existe, esto dará KeyError (igual que antes)
    if tipo == "spc":
        valor_li = df_archivos[limite_inferior].median()
        valor_ls = df_archivos[limite_superior].median()

        dic_param_loc = {
            "loc_max": loc_max, "scale_max": scale_max, "nmun_max": nmun_max, "cpro_max": cpro_max, "cmun_max": cmun_max,
            "loc_mediana": loc_mediana, "scale_mediana": scale_mediana, "nmun_mediana": nmun_mediana, "cpro_mediana": cpro_mediana, "cmun_mediana": cmun_mediana,
            "loc_min": loc_min, "scale_min": scale_min, "nmun_min": nmun_min, "cpro_min": cpro_min, "cmun_min": cmun_min,
            "limite_inferior": int(valor_li),
            "limite_superior": int(valor_ls),
        }

    elif tipo == "cv":
        valor_li = df_archivos[limite_inferior].median()
        valor_ls = df_archivos[limite_superior].median()

        dic_param_loc = {
            "loc_max": loc_max, "scale_max": scale_max, "nmun_max": nmun_max, "cpro_max": cpro_max, "cmun_max": cmun_max,
            "loc_mediana": loc_mediana, "scale_mediana": scale_mediana, "nmun_mediana": nmun_mediana, "cpro_mediana": cpro_mediana, "cmun_mediana": cmun_mediana,
            "loc_min": loc_min, "scale_min": scale_min, "nmun_min": nmun_min, "cpro_min": cpro_min, "cmun_min": cmun_min,
            "limite_inferior": valor_li,
            "limite_superior": valor_ls,
        }

    else:
        valor_li = df_archivos[limite_inferior].median()

        dic_param_loc = {
            "loc_max": loc_max, "scale_max": scale_max, "nmun_max": nmun_max, "cpro_max": cpro_max, "cmun_max": cmun_max,
            "loc_mediana": loc_mediana, "scale_mediana": scale_mediana, "nmun_mediana": nmun_mediana, "cpro_mediana": cpro_mediana, "cmun_mediana": cmun_mediana,
            "loc_min": loc_min, "scale_min": scale_min, "nmun_min": nmun_min, "cpro_min": cpro_min, "cmun_min": cmun_min,
            "limite_inferior": int(valor_li),
        }

    return dic_param_loc

def _tabla_info_bajo_ax(
    ax, loc_g, scale_g,
    loc_reg, scale_reg, any_cat,
    n_out, n_mun,
    # datos locales
    nmun_min=None, cpro_min=None, cmun_min=None, loc_min=None, scale_min=None,
    nmun_med=None, cpro_med=None, cmun_med=None, loc_med=None, scale_med=None,
    nmun_max=None, cpro_max=None, cmun_max=None, loc_max=None, scale_max=None,
    # estilo
    fontsize=10,
    auto_fontsize=True,
    min_fontsize=6,
    center_all=True,
    bbox=(0.0, -0.48, 1.0, 0.38),
    pad_frac=0.08,
    col_min_widths=(0.18, 0.12, 0.35, 0.12, 0.12),
    header_bold=True,
    header_alpha=0.95,
    cell_lw=0.6,
    umbral_similitud=0.80,
):
    """
    Función de apoyo para visualizar_sigmoides_scipy para visualizar de forma
    compacta bajo el eje los parametros de la funciones:
      - anchos de columnas adaptados al contenido
      - control explícito de fontsize
      - auto-reducción opcional del fontsize si hay texto largo

    """
    # Normalización de los nombres de los municipios 
    # Primera versión, todavía falla con municipios de Alicante que no identifica
    # bien el segundo nombre local, pediente de revisión. 
    def fmt_mun(name):
        if name is None:
            return ""
        b = str(name).strip()
        if not b:
            return ""

        # Normaliza: primera igual, resto minúsculas
        b = b[:1] + b[1:].lower()

        num_barrar = b.count("_")
        if num_barrar == 0:
            return b.capitalize()

        if num_barrar == 1:
            izquierda, derecha = b.split("_", 1)
            similitud = SequenceMatcher(None, izquierda.lower(), derecha.lower()).ratio()

            if similitud >= umbral_similitud:
                return izquierda.capitalize() + " / " + derecha.capitalize()
            else:
                return izquierda.capitalize() + " " + derecha.capitalize()

        return " ".join(p.capitalize() for p in b.split("_") if p)

    # Generación de la tabla 
    col_labels = ["Series", "Clave", "Municipio", "loc", "σ"] # Columnas 
    rows = []

    # Primera columna 
    # PD, en un futuro se podría poner varios análsisi por años 2024, 2025, etc
    # si hubiera datos historicos sería genial. Escribir a Catastro? 
    
    rows.append(["IVR GAU", "IIS-2025", "Muestra de 672 municipios",
                 f"{loc_g:.3f}", f"{scale_g:.3f}"])
    
    if loc_reg:
        rows.append(["IVR LOC", any_cat, f"Muestra de {n_mun} municipios", f"{loc_reg:.3f}", f"{scale_reg:.3f}"])
        
    
    # Lógica en función del número de municipios 1, 2, 3 o más
    def clave(cpro, cmun):
        if cpro is None or cmun is None:
            return ""
        return f"{cpro}{cmun}"  

    if n_mun <= 1:
        rows.append([
            "IVR LOC", clave(cpro_med, cmun_med), fmt_mun(nmun_med),
            f"{loc_med:.2f}", f"{scale_med:.2f}"
        ])
    elif n_mun == 2:
        rows.append([
            "IVR LOC-MIN", clave(cpro_min, cmun_min), fmt_mun(nmun_min),
            f"{loc_min:.2f}", f"{scale_min:.2f}"
        ])
        rows.append([
            "IVR LOC-MAX", clave(cpro_max, cmun_max), fmt_mun(nmun_max),
            f"{loc_max:.2f}", f"{scale_max:.2f}"
        ])
    else:
        rows.append([
            "IVR LOC-MIN", clave(cpro_min, cmun_min), fmt_mun(nmun_min),
            f"{loc_min:.2f}", f"{scale_min:.2f}"
        ])
        rows.append([
            "IVR LOC-MED", clave(cpro_med, cmun_med), fmt_mun(nmun_med),
            f"{loc_med:.2f}", f"{scale_med:.2f}"
        ])
        rows.append([
            "IVR LOC-MAX", clave(cpro_max, cmun_max), fmt_mun(nmun_max),
            f"{loc_max:.2f}", f"{scale_max:.2f}"
        ])
        
    # PD, Sugerencia de Prada, se podría poner también el conjunto de toda la 
    # muestra introducida por el usuario a parte de las locales como se hacía antes...
    
    # Se podría representar todas las gráficas (Sí, pero sería poco interpretrable no?)
    # aunque se podria dejar con un gris más claro y no dar sus datos... pensar

    # Estilos de la tabla, ajuste del texto
    n_cols = len(col_labels)
    all_text = [col_labels] + rows

    maxlen = []
    for j in range(n_cols):
        maxlen.append(max(len(str(r[j])) for r in all_text))

    weights = [(m * (1.0 + pad_frac)) for m in maxlen]

    minw = list(col_min_widths)
    if len(minw) != n_cols:
        minw = [0.0] * n_cols

    total_w = sum(weights) if sum(weights) > 0 else 1.0
    minw_as_weight = [mw * total_w for mw in minw]
    weights = [max(weights[j], minw_as_weight[j]) for j in range(n_cols)]

    s = sum(weights) if sum(weights) > 0 else 1.0
    col_widths = [w / s for w in weights]

    # Creación de la tabla
    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        cellLoc="center",
        colLoc="center",
        loc="lower center",
        bbox=list(bbox),
        colWidths=col_widths,
    )

    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)

    # Estilo + centrado total

    for (r, c), cell in table.get_celld().items():
        cell.set_linewidth(cell_lw)

        if r == 0:
            if header_bold:
                cell.set_text_props(weight="bold")
            cell.set_alpha(header_alpha)

        if center_all:
            cell._text.set_ha("center")
            cell._text.set_x(0.5)

    # Auto-ajuste fontsize

    if auto_fontsize:
        mun_len = maxlen[2]
        clave_len = maxlen[1]
        fs = fontsize

        if mun_len > 18 or clave_len > 14:
            fs = max(min_fontsize, fs - 1)
        if mun_len > 26 or clave_len > 20:
            fs = max(min_fontsize, fs - 1)
        if mun_len > 34 or clave_len > 26:
            fs = max(min_fontsize, fs - 1)

        if fs != fontsize:
            table.set_fontsize(fs)

    return table

def visualizar_sigmoides_scipy(
        dfs_bi, df_archivos, dic_parametros, parametros_globales,
        parametros_estadisticos, parametros_reg, specs,
        bins = 45, xmax_ate = 2026, fun_loc = True, # Cambiar a True
        titulo = "Ajustes logísticos del IVR en bienes inmuebles",
        col_municipio = "nmun",
        figsize = None,
        wspace = 0.15,
        bottom = 0.32,
        top = 0.86,
        show_right_ticks = True,
        ypad = 0.02,
        output = None,
        dpi = 400
        
):
    """
    Representa la figura de normalización con todos los bienes inmubles de la
    muestra introducida por el usuario. Lo hace para las variables del IVR.
    """
        
    # Municipios únicos
    if df_archivos is None or col_municipio not in df_archivos:
        n_mun = 3
    else:
        n_mun = int(df_archivos[col_municipio].nunique(dropna=True))
        
    # En producción simpre debe ser fun_loc = True para mostrar IVR LOC muestral 
    # Si es False no se representa en la figura 
    # PD en un futuro pdoria actualziarse la .ui para dar ópción al usuario. 
    # Se añade que sí solo es un municipio IVR LOC no salga en la tabla 
    if not fun_loc or n_mun == 1:
        parametros_reg = None

    k = len(specs)

    if figsize is None:
        figsize = (6 * k, 6)

    # Lógica histograma acumulado y curvas lógisiticas
    YMAX_GLOBAL = 0.0

    for spec in specs:
        tipo = spec["tipo"]
        variable = spec["variable"]

        if (tipo not in dic_parametros) or (variable not in dfs_bi) or (variable not in parametros_globales):
            continue

        p = dic_parametros[tipo]

        x_raw = np.asarray(dfs_bi[variable], dtype=float)
        x_raw = x_raw[np.isfinite(x_raw)]
        if x_raw.size == 0:
            continue

        # Quizás tendria  más sentido que poner el limite inferiro más bajo o mayor
        # poner el limiter medio teniendo encuenta todos los municipios y no el más extremo
        # aunque pille más datos, si hay municipios extremos podría comprometer visualización 
        # del gráfico, darle una vuelta en futuras revisiones. 

        if "limite_inferior" not in p:
            continue

        xmin = float(p["limite_inferior"])
        if tipo == "ate":
            xmax = float(xmax_ate)
        else:
            if "limite_superior" not in p:
                continue
            xmax = float(p["limite_superior"])

        if xmax <= xmin:
            continue

        x = x_raw[(x_raw >= xmin) & (x_raw <= xmax)]
        if x.size == 0:
            continue

        N = x.size

        # Máximo real del hist acumulado es N 
        counts, _ = np.histogram(x, bins = bins, range = (xmin, xmax))
        y_hist_max = np.cumsum(counts)[-1]  

        # Máximo real de curvas: tiende a N
        loc_g = float(parametros_globales[variable]["loc"])
        scale_g = float(parametros_globales[variable]["scale"])
        
        # si faltan locales no podemos evaluar curvas -> usamos N
        req = ["loc_min", "scale_min", "loc_mediana",
               "scale_mediana", "loc_max", "scale_max"]
        
        if any(r not in p for r in req) or scale_g <= 0:
            YMAX_GLOBAL = max(YMAX_GLOBAL, y_hist_max, float(N))
            continue

        loc_min = float(p["loc_min"]);      scale_min = float(p["scale_min"])
        loc_med = float(p["loc_mediana"]);  scale_med = float(p["scale_mediana"])
        loc_max = float(p["loc_max"]);      scale_max = float(p["scale_max"])

        if min(scale_min, scale_med, scale_max) <= 0:
            YMAX_GLOBAL = max(YMAX_GLOBAL, y_hist_max, float(N))
            continue

        xx = np.linspace(xmin, xmax, 800)
        yy_g   = N * logistic.cdf(xx, loc=loc_g,   scale=scale_g)
        yy_min = N * logistic.cdf(xx, loc=loc_min, scale=scale_min)
        yy_med = N * logistic.cdf(xx, loc=loc_med, scale=scale_med)
        yy_max = N * logistic.cdf(xx, loc=loc_max, scale=scale_max)

        y_curve_max = max(float(yy_g.max()), float(yy_min.max()), float(yy_med.max()), float(yy_max.max()))
        YMAX_GLOBAL = max(YMAX_GLOBAL, float(y_hist_max), float(y_curve_max))

    if YMAX_GLOBAL <= 0:
        YMAX_GLOBAL = 1.0

    YLIM_TOP = YMAX_GLOBAL * (1.0 + float(ypad))

    fig, axes = plt.subplots(1, k, figsize=figsize, squeeze=False)
    axes = axes[0]
    
    # Extración de información de diccionarios 

    resultados = []

    for i, spec in enumerate(specs):
        ax = axes[i]
        tipo = spec["tipo"]
        variable = spec["variable"]
        xlabel = spec.get("xlabel", variable)

        p = dic_parametros[tipo]

        x_raw = np.asarray(dfs_bi[variable], dtype=float)
        x_raw = x_raw[np.isfinite(x_raw)]
        
        xmin = float(p["limite_inferior"])
        if tipo == "ate":
            xmax = float(xmax_ate)
        else:
            xmax = float(p["limite_superior"])

        # Cáculo de outliers
        # Antes aparecia en el gráfico, se ha eliminado para no saturar información,
        # aunque podria aparecer dentro de leyenda interna de la figura
        
        # Versión corregida 23/02/2026 para outliers 
        n_total = x_raw.size
        
        if parametros_estadisticos and variable in parametros_estadisticos:
            pe = parametros_estadisticos[variable]
            # Busca las claves n_li_* y n_ls_* independientemente del sufijo
            n_li  = next((v for k, v in pe.items() if k.startswith("n_li_")),  None)
            n_ls  = next((v for k, v in pe.items() if k.startswith("n_ls_")),  None)
            pc_ft = next((v for k, v in pe.items() if k.startswith("pc_ft_")), None)
        
            if n_li is not None and n_ls is not None:
                n_out   = int(n_li) + int(n_ls)
                pbi_out = float(pc_ft) if pc_ft is not None else (n_out / n_total) * 100.0
            else:
                # fallback al cálculo original
                n_out   = int(np.sum((x_raw < xmin) | (x_raw > xmax)))
                pbi_out = (n_out / n_total) * 100.0
        else:
            # fallback al cálculo original
            n_out   = int(np.sum((x_raw < xmin) | (x_raw > xmax)))
            pbi_out = (n_out / n_total) * 100.0

        # rango
        x = x_raw[(x_raw >= xmin) & (x_raw <= xmax)]
        N = x.size
        
        # Hay muncipios que no tienen casi disperisón y tienen casi la misma 
        # tipología en sus BI, para evitar problemas de rango en coeficiente 
        # de valor si salta error se limita al mínimo permitido. 
        # Ejemplo de municipio COBISA (45052)
        if xmax <= xmin:
            xmin = 0.35

        # global
        loc_g = float(parametros_globales[variable]["loc"])
        scale_g = float(parametros_globales[variable]["scale"])
        
        loc_reg = None
        scale_reg = None
        
        if parametros_reg: 
            loc_reg = float(parametros_reg[variable]["loc"])
            scale_reg = float(parametros_reg[variable]["scale"])
        
        # locales
        loc_min = float(p["loc_min"]);      scale_min = float(p["scale_min"])
        loc_med = float(p["loc_mediana"]);  scale_med = float(p["scale_mediana"])
        loc_max = float(p["loc_max"]);      scale_max = float(p["scale_max"])

        # Municipios info
        nmun_min = p.get("nmun_min", "MIN")
        nmun_med = p.get("nmun_mediana", "MEDIANA")
        nmun_max = p.get("nmun_max", "MAX")

        cpro_min = p.get("cpro_min", "MIN")
        cpro_med = p.get("cpro_mediana", "MEDIANA")
        cpro_max = p.get("cpro_max", "MAX")

        cmun_min = p.get("cmun_min", "MIN")
        cmun_med = p.get("cmun_mediana", "MEDIANA")
        cmun_max = p.get("cmun_max", "MAX")

        # Curvas representación
        xx = np.linspace(xmin, xmax, 800)
        yy_g   = N * logistic.cdf(xx, loc = loc_g,   scale = scale_g)
        if parametros_reg: 
            yy_reg = N * logistic.cdf(xx, loc = loc_reg, scale = scale_reg)
        yy_min = N * logistic.cdf(xx, loc = loc_min, scale = scale_min)
        yy_med = N * logistic.cdf(xx, loc = loc_med, scale = scale_med)
        yy_max = N * logistic.cdf(xx, loc = loc_max, scale = scale_max)

        # Generación histograma acomulado
        ax.hist(
            x, bins = bins, 
            range = (xmin, xmax),
            cumulative = True, 
            density = False,
            color = "lightgray", 
            edgecolor = "black",
            linewidth = 0.8, alpha = 1.0
        )

        # Líenas tabla 
        line_g, = ax.plot(xx, yy_g, linewidth=2.5, linestyle="--",
                          color="black", label = "IVR GAU")
        
        # IVR LOC-REG sólo si hay más de un municipio
        line_reg = None
        if parametros_reg and n_mun > 1:
            line_reg, = ax.plot(xx, yy_reg, linewidth=2.5, linestyle="--",
                                color="grey", label="IVR LOC")

        line_min = line_med = line_max = None
        if n_mun <= 1:
            line_med, = ax.plot(xx, yy_med, linewidth=2.0, color="#fa8331",
                                label="IVR LOC")
        elif n_mun == 2:
            line_min, = ax.plot(xx, yy_min, linewidth=2.0, color="#d94901",
                                label="IVR LOC-MIN")
            line_max, = ax.plot(xx, yy_max, linewidth=2.0, color="#fdbd83",
                                label="IVR LOC-MAX")
        else:
            line_min, = ax.plot(xx, yy_min, linewidth=2.0, color="#d94901",
                                label="IVR LOC-MIN")
            line_med, = ax.plot(xx, yy_med, linewidth=2.0, color="#fa8331",
                                label="IVR LOC-MED")
            line_max, = ax.plot(xx, yy_max, linewidth=2.0, color="#fdbd83",
                                label="IVR LOC-MAX")

        # Eje comun IZQ
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(0, YLIM_TOP)
        ax.grid(True, linestyle="--", alpha=0.4)

        ax.spines["left"].set_visible(True)
        if i == 0:
            ax.set_ylabel("Frecuencia acumulada")
            ax.tick_params(axis="y", left=True, labelleft=True)
        else:
            ax.set_ylabel("")
            ax.tick_params(axis="y", left=False, labelleft=False)

        # Eje comun DRC
        
        ax_v = ax.twinx()
        ax_v.set_ylim(0, 1)   # <- si lo quieres invertido: (1, 0)
        ax_v.grid(False)
        ax_v.spines["right"].set_visible(True)

        if i == k - 1:
            ax_v.set_ylabel("IVR por variable", fontsize=10, labelpad=10)
            ax_v.tick_params(axis="y", right=True, labelright=True, labelsize=9)
        else:
            ax_v.set_ylabel("")
            ax_v.tick_params(axis="y", right=True, labelright=show_right_ticks, labelsize=9)

        # Nombre leyenda dentro figura 
        ax.text(
            0.5, 1.02, xlabel,
            transform=ax.transAxes,
            ha="center", va="bottom",
            fontsize=12, fontweight="bold",
            color="0.50"
        )
        
        # leyenda líneas y atipicos 
        
        handles_lineas = [line_g]
        labels_lineas = ["IVR GAU"]

        if line_reg is not None:
            handles_lineas.append(line_reg)
            labels_lineas.append("IVR LOC")
        
        for ln in (line_min, line_med, line_max):
            if ln is not None:
                handles_lineas.append(ln)
                labels_lineas.append(ln.get_label())  
                
        # Información relativa a los autliers (añadido finalmente)
        texto_atip = f"Atípicos: {n_out}\nProporción: {pbi_out:.2f}%"
        handle_atip = Rectangle((0, 0), 0, 0, fill=False, edgecolor='none', visible=False)
        
        handles_lineas.append(handle_atip)
        labels_lineas.append(texto_atip)
                
        leg1 = ax.legend(
            handles_lineas,
            labels_lineas,
            loc="upper left",
            framealpha = 0.95,
            ncol = 1,
            fontsize = 9,            # Tamaño letra 
            handlelength = 1.00,     # Tamaño Simbolos
            labelspacing = 0.25,     # Reduce espacio vertical entre líneas 
            borderpad = 0.25,        # Reduce padding interno del borde 
            handletextpad = 0.6,     # Reduce espacio entre símbolo y texto 
            borderaxespad = 0.5,     # Reduce espacio entre leyenda y ejes 
            frameon = True,          # Asegura que tenga marco
            edgecolor ='0.75',        # Color del borde 
            fancybox = False         # Quita esquinas redondeadas 
        )


        # Texto de la leyenda de Atípicos (Más como nota informativa)

        txt_atip = leg1.get_texts()[-1]
        txt_atip.set_fontsize(8)     
        txt_atip.set_color("0.45")
        txt_atip.set_style("italic")
        txt_atip.set_ha("center")        
        offset = ScaledTranslation(-7/72, 0, fig.dpi_scale_trans)  # Ajusta el -35 según necesites
        txt_atip.set_transform(txt_atip.get_transform() + offset)
        ax.add_artist(leg1)

        # Aqui construir tabla (Función de apoyo)
        
        try:
            ruta_gz = df_archivos["ruta_cat"][0]
            any_cat = cat.obtener_anio_cat(ruta_gz)
        except:
            any_cat = time.localtime().tm_year
        
        _tabla_info_bajo_ax(
            ax = ax,
            loc_g = loc_g, scale_g = scale_g,
            loc_reg = loc_reg, scale_reg = scale_reg, any_cat=any_cat,
            n_out = n_out, n_mun = n_mun,
            nmun_min=nmun_min, cpro_min=cpro_min, cmun_min=cmun_min, loc_min=loc_min, scale_min=scale_min,
            nmun_med=nmun_med, cpro_med=cpro_med, cmun_med=cmun_med, loc_med=loc_med, scale_med=scale_med,
            nmun_max=nmun_max, cpro_max=cpro_max, cmun_max=cmun_max, loc_max=loc_max, scale_max=scale_max,
            fontsize = 9
        )
        
        resultados.append({
            "tipo": tipo,
            "variable": variable,
            "xlabel": xlabel,
            "n_municipios": int(n_mun),
            "n_total": int(n_total),
            "n_in_range": int(N),
            "n_outliers": int(n_out),
            "pbi_outliers": float(pbi_out),
            "xmin": float(xmin),
            "xmax": float(xmax),
        })

    if titulo:
        fig.suptitle(titulo, fontweight="bold")
        
    fig.subplots_adjust(bottom=bottom, wspace=wspace, top=top)
    
    if output: 
        plt.savefig(
            output,
            dpi = dpi, # Resolución 400 para que sea de alta calidad en IVR_plugin             
            bbox_inches = "tight",
            pad_inches = 0.02
            )
        
    plt.close(fig)
        
    return fig, axes, resultados

def visualizar_normalizacion(
    df, dic_parametros, dic_nor_param,
    metodo, rangos,
    bins = 45, bins_cv = 20,  # Número de Bins fila CVCT 
    label_right = "Densidad",
    titulo = None,
    titulo_x = None,
    titulo_y = None,
    figsize = (14, 12),
    wspace = 0.125,
    hspace = 0.125,
    coef_round = None,
    right_margin = 0.96,
    label_right_x = 0.985,
    invert_ivr_axis = True,
    output = None,
    dpi = 400
):
    """
    Figura con toda información del proceso de normalización para todas las
    variables del ivr en un formato de 3x3 con los siguentes columnas: 
    - Columna izquierda: Histograma con frc. relativa.
    - Columnas centro/derecha: IVR GAY/LOC con densidad, misma escala.
    - dic_nor_param: colorea bins de IVR por clases.
    """

    # Funciones de normalizado variables 
    def _normalize_classes(classes):
        if classes is None:
            return None
        classes2 = [(float(vmin), float(vmax), color) for (vmin, vmax, color) in classes]
        classes2.sort(key=lambda x: x[0])
        return classes2

    def _color_for_value(x, classes, default="#1f77b4"):
        if not classes:
            return default
        for k, (vmin, vmax, col) in enumerate(classes):
            if k == len(classes) - 1:
                if vmin <= x <= vmax:
                    return col
            else:
                if vmin <= x < vmax:
                    return col
        return default

    # Parametros preconfigurados 
    fila_a_param = ["spc", "ate", "cv"]
    filas = [
        ["sup_bi",  "supc_bi_tfg",  "supc_bi_tfm"],
        ["ante_bi", "ante_bi_tfg",  "ante_bi_tfm"],
        ["cvcn_bi", "cvcn_bi_tfg",  "cvcn_bi_tfm"]
    ]

    etiquetas_fila = ["Superficie habitable", "Antigüedad efectiva",
                      "Coeficiente de valor"]
    etiquetas_columna = ["Histograma", "IVR GAU", "IVR LOC"]
    colores_titulos = ("#444444", "#464e50", "#464e50")
    color_label_right = "#464e50"                       

    fig, axes = plt.subplots(3, 3, figsize=figsize)

    if titulo:
        fig.suptitle(titulo, fontsize=14, fontweight="bold", x = titulo_x, y = titulo_y)

    anio_actual = datetime.now().year
    
    # Bucle para construcción de figuras 
    for i, fila in enumerate(filas):
        bins_fila = bins if i < 2 else bins_cv
        bins_iv = np.linspace(0, 1, bins_fila + 1)

        # Clases por fila (spc / ate / cv)
        rangos = str(rangos)
        param_key = fila_a_param[i]
        try:
            classes_raw = dic_nor_param[param_key][metodo][rangos]
        except Exception:
            classes_raw = None
        classes = _normalize_classes(classes_raw)

        # Max densidad por fila (IVR)
        max_density_fila = 0.0
        hist_cache = {}
        for j in (1, 2):
            col_iv = fila[j]
            serie_iv = df[col_iv].dropna().astype(float).to_numpy()
            h, edges = np.histogram(serie_iv, bins=bins_iv, density=True)
            hist_cache[col_iv] = (h, edges)
            if h.size:
                max_density_fila = max(max_density_fila, float(h.max()))

        for j, col in enumerate(fila):
            ax = axes[i, j]
            serie = df[col].dropna().astype(float)

            # Diseño 
            ax.grid(True, alpha=0.18, linestyle="--", linewidth=0.8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(labelsize=9)
            ax.set_xlabel("")

            # Ajustar limites de corte
            if j == 0:
                if col == "sup_bi":
                    li = dic_parametros["spc"]["limite_inferior"]
                    ls = dic_parametros["spc"]["limite_superior"]
                elif col == "ante_bi":
                    li = dic_parametros["ate"]["limite_inferior"]
                    ls = anio_actual
                else:  # cvcn_bi
                    li = dic_parametros["cv"]["limite_inferior"]
                    ls = dic_parametros["cv"]["limite_superior"]

                serie = serie[(serie >= li) & (serie <= ls)]
                ax.set_xlim(li, ls)

                if len(serie) > 0:
                    serie_plot = np.round(serie, coef_round) if (col == "cvcn_bi" and coef_round is not None) else serie
                
                    ax.hist(
                        serie_plot,
                        bins=bins_fila,
                        density=False,            # <- conteos
                        color="#B0B0B0",
                        alpha=0.95,
                        edgecolor="black",
                        linewidth=0.6
                    )
                    ax.set_ylabel(f"{etiquetas_fila[i]}\n(Nº de BI)", fontsize=11)
                

            # Columnas del IVR
            else:
                h, edges = hist_cache[col]
                widths = np.diff(edges)
                left = edges[:-1]
                centers = left + widths / 2.0

                bar_colors = [_color_for_value(c, classes) for c in centers] if classes else ["#1f77b4"] * len(centers)

                ax.bar(
                    left,
                    h,
                    width=widths,
                    align="edge",
                    color=bar_colors,
                    edgecolor="white",
                    linewidth=0.6,
                    alpha=0.95
                )

                if max_density_fila > 0:
                    ax.set_ylim(0, max_density_fila * 1.05)

                ax.set_xlim(0, 1)
                if invert_ivr_axis:
                    ax.invert_xaxis()
                    ax.set_xticks([1, 0.5, 0])
                else:
                    ax.set_xticks([0, 0.5, 1])

                ax.set_ylabel("")

            # Ajsute titulo
            if i == 0:
                ax.set_title(
                    etiquetas_columna[j],
                    fontsize=12,
                    fontweight="bold",
                    color=colores_titulos[j]
                )

    top = 0.90 if titulo else 0.92
    fig.subplots_adjust(top=top, right=right_margin, wspace=wspace, hspace=hspace)

    # Ajsute texto de densidad 
    fig.text(
        label_right_x, 0.5, label_right,
        va="center", ha="center",
        rotation = 90, fontsize = 12.5,
        color = color_label_right
    )

    if output: 
        plt.savefig(
            output,
            dpi = dpi,                 
            bbox_inches = "tight",
            pad_inches = 0.02
            )
        
    plt.close(fig)

# Funciones para generación documentación general y csv  
def generar_info_txt(ruta_salida, titulo, columnas_info, 
                     inf_mun=False, columnas_mun=None, 
                     inf_prov=False, columnas_prov=None,
                     autor=None, colaboradores=None, version=None):
    """
    Genera archivo .txt con título centrado y lista de columnas.
    Opcionalmente incluye información de municipios, provincias, autor y versión.
    
    Args:
        ruta_salida: str, ruta completa del archivo (ej: 'C:/salida/info.txt')
        titulo: str, título del documento
        columnas_info: dict, {nombre_columna: descripción} para capa principal
        inf_mun: bool, si True genera sección de municipios
        columnas_mun: dict, {nombre_columna: descripción} para municipios
        inf_prov: bool, si True genera sección de provincias
        columnas_prov: dict, {nombre_columna: descripción} para provincias
        autor: str, nombre del autor (opcional)
        colaboradores: list o str, colaboradores (opcional)
        version: str, versión del complemento (opcional)
    """
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        ancho = 80
        
        # Título principal centrado
        titulo_centrado = titulo.center(ancho)
        f.write("=" * ancho + "\n")
        f.write(titulo_centrado + "\n")
        f.write("=" * ancho + "\n\n")
        
        # Información de columnas principales
        f.write("INFORMACIÓN DE COLUMNAS - CAPA IVR (COMPLETA)\n")
        f.write("-" * ancho + "\n\n")
        
        for i, (columna, descripcion) in enumerate(columnas_info.items(), 1):
            f.write(f"{i}. Columna: {columna}\n")
            f.write(f"   {descripcion}\n\n")
        
        # Información de municipios (opcional)
        if inf_mun and columnas_mun:
            f.write("\n" + "=" * ancho + "\n\n")
            f.write("INFORMACIÓN DE COLUMNAS - MUNICIPIOS\n")
            f.write("-" * ancho + "\n\n")
            
            for i, (columna, descripcion) in enumerate(columnas_mun.items(), 1):
                f.write(f"{i}. Columna: {columna}\n")
                f.write(f"   {descripcion}\n\n")
        
        # Información de provincias (opcional)
        if inf_prov and columnas_prov:
            f.write("\n" + "=" * ancho + "\n\n")
            f.write("INFORMACIÓN DE COLUMNAS - PROVINCIAS\n")
            f.write("-" * ancho + "\n\n")
            
            for i, (columna, descripcion) in enumerate(columnas_prov.items(), 1):
                f.write(f"{i}. Columna: {columna}\n")
                f.write(f"   {descripcion}\n\n")
        
        # Información final: Autor, Colaboradores y Versión
        f.write("=" * ancho + "\n\n")
        
        if autor:
            f.write(f"Autor principal y otros autores: {autor}\n")
        
        if colaboradores:
            if isinstance(colaboradores, list):
                f.write(f"Otros colaboradores: {', '.join(colaboradores)}\n")
            else:
                f.write(f"Otros colaboradores: {colaboradores}\n")
        
        if version:
            f.write(f"Versión complemento: {version}\n")
        
        if autor or colaboradores or version:
            f.write("\n" + "=" * ancho + "\n")

# Ejemplo de uso completo:
columnas_principales = {
    # Básicas 
    "refcat": "Referencia catastral de 18 dígitos sin caracteres de control.",
    "cpro": "Código de provincia (extraído de rutas de datos de catastro).",
    "cmun_dgc": "Código de municipio DGC (puede diferir del código INE).",
    "nmun": "Nombre del municipio (extraído de rutas de datos de catastro).",
    
    # Información adicional
    "n_ct": "Número de construcciones existentes dentro de la parcela catastral.",
    "n_bi": "Número de Bienes Inmuebles Residenciales dentro de la parcela catastral.",
    "sup_pc": "Superficie total construida dentro de la parcela catastral (suma de todas las construcciones).",
    
    # Información original 
    "ante_pc": "Antigüedad efectiva media de los Bienes Inmuebles Residenciales (ponderación de año de construcción y reformas).",
    "supc_pc": "Superficie habitable media de los Bienes Inmuebles Residenciales dentro de la parcela catastral.",
    "tcus_pc": "Tipología constructiva predominante de los Bienes Inmuebles Residenciales dentro de la parcela catastral.",
    "calp_pc": "Calidad constructiva predominante de los Bienes Inmuebles Residenciales dentro de la parcela catastral.",
    "cvcn_pc": "Coeficiente de Valor de Construcción predominante de los Bienes Inmuebles Residenciales (según Real Decreto 1020/1993).",
    
    # Información normalizada
    "ante_n_gau": "Variable normalizada de antigüedad efectiva para Grandes Áreas Urbanas (GAUs).",
    "supc_n_gau": "Variable normalizada de superficie habitable para Grandes Áreas Urbanas (GAUs).",
    "cvct_n_gau": "Variable normalizada de Coeficiente de Valor de Construcción para Grandes Áreas Urbanas (GAUs).",
    "ante_n_loc": "Variable normalizada de antigüedad efectiva para cada municipio procesado.",
    "supc_n_loc": "Variable normalizada de superficie habitable para cada municipio procesado.",
    "cvct_n_loc": "Variable normalizada de Coeficiente de Valor de Construcción para cada municipio procesado.",
    
    # Índices IVR
    "ivr_gau": "Índice de Vulnerabilidad Residencial para Grandes Áreas Urbanas (GAUs).",
    "ivr_loc": "Índice de Vulnerabilidad Residencial para localidades municipales (LOCs).",
    "Clases_MR": "Clasificación según método (Q-Cuantiles, J-Cortes Naturales de Jenks, I-Intervalos Iguales) y rangos (2-10) para GAUs.",
    "geom": "Geometría del Parcelario Urbano Residencial obtenido de la DGC (PARCELA.SHP).",
}

columnas_municipios = {
    # Datos derivados de la generación de df_archivos (9)
    "cpro": "Código de provincia (extraído de rutas de datos de catastro).",
    "cmun_dgc": "Código de municipio DGC (puede diferir del código INE).",
    "tipo": "Tipo de suelo: Urbano (u) o Rústico (r). Nota: rústicos no disponibles aún.",
    "nmun": "Nombre del municipio (extraído de rutas de datos de catastro).",
    "npro": "Nombre de la provincia.",
    "idx_prov": "Índice del municipio dentro de su provincia según orden de procesamiento.",
    "total_prov": "Número total de municipios procesados en esa provincia.",
    
    # Datos derivados de la lectura de ficheros .CAT y su limpieza (8)
    "num_ct": "Número de construcciones totales dentro del municipio.",
    "ct_51_nah": "Número de construcciones consideradas elementos comunes (filtradas).",
    "ct_105_nah": "Número de construcciones sin tipología residencial (filtradas).",
    "ct_nah": "Número de construcciones totales filtradas para el análisis.",
    "num_ctc": "Número de construcciones válidas con superficie computable de tipología residencial (solo BI Residenciales T15 si procede).",
    "ct_nah_%": "Porcentaje de construcciones respecto al total municipal filtradas para el cálculo del IVR.",
    "ct_esp": "Existen construcciones con calidades constructivas superiores a 1 en el municipio (A, B o C): True o False.",
    "tm_ct": "Tiempo de lectura de ficheros .CAT (T14 + T15 si procede) y filtrado de datos (en segundos).",
    
    # Datos derivados de la agregación a nivel Inmuble (10)
    "n_tbi14": "Número total de Bienes Inmuebles en registros de construcción (T14).",
    "n_tbi15": "Número total de Bienes Inmuebles en registros de inmuebles (T15).",
    "n_bi_c": "Número de Bienes Inmuebles con tipología constructiva y superficie computable (T14 y filtro T15 si procede).",
    "n_bi_ur": "Número de Bienes Inmuebles Urbanos Residenciales (T15).",
    "n_bi01": "Número de Bienes Inmuebles con participación predominante residencial (T14 y filtro T15 si procede).",
    "n_bi01_p": "Número de Bienes Inmuebles residenciales puros (T14 y filtro T15 si procede).",
    "n_bi01_m": "Número de Bienes Inmuebles residenciales mixtos (T14 y filtro T15 si procede).",
    "med_bi01_m": "Media de la participación de los Bienes Inmuebles residenciales mixtos (T14 y filtro T15 si procede).",
    "n_bi01_fil": "Número de Bienes Inmuebles residenciales filtrados según el umbral establecido (T14 y filtro T15 si procede).",
    "tm_bi": "Tiempo de procesamiento de los Bienes Inmuebles de ficheros (T14 + T15 si procede)-(en segundos).",
    
    # Datos derivados de la normalización de los BI  (13 * 3)
    # Estadísticos de Superficie Computable (supc_bi)
    "q1_spc": "Primer cuartil (Q1) de la superficie computable de Bienes Inmuebles.",
    "q3_spc": "Tercer cuartil (Q3) de la superficie computable de Bienes Inmuebles.",
    "iqr_spc": "Rango intercuartílico (IQR) de la superficie computable de Bienes Inmuebles.",
    "li_iqr_spc": "Límite inferior del IQR (Q1 - 1.5*IQR) para superficie computable (solo contempla superficies positivas, valores negativos como 0).",
    "n_li_spc": "Número de Bienes Inmuebles por debajo del límite inferior del IQR en superficie computable.",
    "ls_iqr_spc": "Límite superior del IQR (Q3 + 1.5*IQR) para superficie computable.",
    "n_ls_spc": "Número de Bienes Inmuebles por encima del límite superior del IQR en superficie computable.",
    "q05_spc": "Percentil 5 de la superficie computable de Bienes Inmuebles.",
    "q95_spc": "Percentil 95 de la superficie computable de Bienes Inmuebles.",
    "loc_spc": "Parámetro de localización (loc) del ajuste logístico para superficie computable (interpretable como mediana).",
    "scale_spc": "Parámetro de escala (scale) del ajuste logístico para superficie computable (interpretable como dispersión).",
    "n_fit_spc": "Número de Bienes Inmuebles Residenciales usados en el ajuste logístico para superficie computable.",
    "pc_ft_spc": "Porcentaje de Bienes Inmuebles Residenciales filtrados como outliers (fuera del rango IQR) para superficie computable.",
    
    # Estadísticos de Antigüedad Efectiva (ante_bi)
    "q1_ate": "Primer cuartil (Q1) de la antigüedad efectiva de Bienes Inmuebles.",
    "q3_ate": "Tercer cuartil (Q3) de la antigüedad efectiva de Bienes Inmuebles.",
    "iqr_ate": "Rango intercuartílico (IQR) de la antigüedad efectiva de Bienes Inmuebles.",
    "li_iqr_ate": "Límite inferior del IQR (Q1 - 1.5*IQR) para antigüedad efectiva.",
    "n_li_ate": "Número de Bienes Inmuebles por debajo del límite inferior del IQR en antigüedad efectiva.",
    "ls_iqr_ate": "Límite superior del IQR (Q3 + 1.5*IQR) para antigüedad efectiva (Siempre un año superior al que se ejecuta el complemento).",
    "n_ls_ate": "Número de Bienes Inmuebles por encima del límite superior del IQR en antigüedad efectiva.",
    "q05_ate": "Percentil 5 de la antigüedad efectiva de Bienes Inmuebles.",
    "q95_ate": "Percentil 95 de la antigüedad efectiva de Bienes Inmuebles.",
    "loc_ate": "Parámetro de localización (loc) del ajuste logístico para antigüedad efectiva (interpretable como mediana).",
    "scale_ate": "Parámetro de escala (scale) del ajuste logístico para antigüedad efectiva (interpretable como dispersión).",
    "n_fit_ate": "Número de Bienes Inmuebles usados en el ajuste logístico para antigüedad efectiva.",
    "pc_ft_ate": "Porcentaje de Bienes Inmuebles filtrados como outliers (fuera del rango IQR) para antigüedad efectiva.",
    
    # Estadísticos de Coeficiente de Valor de Construcción (cvcn_bi)
    "q1_cv": "Primer cuartil (Q1) del coeficiente de valor de construcción de Bienes Inmuebles.",
    "q3_cv": "Tercer cuartil (Q3) del coeficiente de valor de construcción de Bienes Inmuebles.",
    "iqr_cv": "Rango intercuartílico (IQR) del coeficiente de valor de construcción de Bienes Inmuebles.",
    "li_iqr_cv": "Límite inferior del IQR (Q1 - 1.5*IQR) para coeficiente de valor.",
    "n_li_cv": "Número de Bienes Inmuebles por debajo del límite inferior del IQR en coeficiente de valor.",
    "ls_iqr_cv": "Límite superior del IQR (Q3 + 1.5*IQR) para coeficiente de valor.",
    "n_ls_cv": "Número de Bienes Inmuebles por encima del límite superior del IQR en coeficiente de valor.",
    "q05_cv": "Percentil 5 del coeficiente de valor de construcción de Bienes Inmuebles.",
    "q95_cv": "Percentil 95 del coeficiente de valor de construcción de Bienes Inmuebles.",
    "loc_cv": "Parámetro de localización (loc) del ajuste logístico para coeficiente de valor (interpretable como mediana).",
    "scale_cv": "Parámetro de escala (scale) del ajuste logístico para coeficiente de valor (interpretable como dispersión).",
    "n_fit_cv": "Número de Bienes Inmuebles usados en el ajuste logístico para coeficiente de valor.",
    "pc_ft_cv": "Porcentaje de Bienes Inmuebles filtrados como outliers (fuera del rango IQR) para coeficiente de valor.",

    # Valores del IVR medios del municipios
    "ivr_gau_media": "Media del IVR calculado con normalización GAU (Grandes Áreas Urbanas) para el municipio.",
    "ivr_gau_mediana": "Mediana del IVR calculado con normalización GAU (Grandes Áreas Urbanas) para el municipio.",
    "ivr_loc_media": "Media del IVR calculado con normalización LOC (Local por municipio) para el municipio.",
    "ivr_loc_mediana": "Mediana del IVR calculado con normalización LOC (Local por municipio) para el municipio.",
    "tm_nor": "Tiempo de procesamiento de la normalización de variables (en segundos).",

    # Clasificador GAU 
    "clase_MN": "Columnas dinámicas generadas solo con clasificación (N = 2 a 10 rangos)."
    "Formato: clase_{M}{N} donde M = método (Q-Cuantiles, J-Jenks, I-Intervalos) y N = número de rango."
    "Cada columna indica cuántos Bienes Inmubles Residenciales del municipio están en ese rango de IVR.",

    # Datos derivados del procesamiento de parcelas
    "n_pcl": "Número total de parcelas catastrales urbanas en el archivo SHP del municipio.",
    "num_pcc": "Número de parcelas con al menos una construcción residencial de superficie computable.",
    "num_pc": "Número de parcelas con Bienes Inmuebles residenciales procesadas (antes de unión con geometría).",
    # "n_pcu": "Número de parcelas procesadas que NO se pudieron unir con el parcelario (sin geometría asociada).", 
    # "n_biu": "Número de Bienes Inmuebles que NO se pudieron unir con el parcelario (pertenecen a parcelas sin geometría).",
    "tm_pc": "Tiempo de procesamiento de agregación a nivel de parcela y unión con geometría (en segundos).",
    
    # Rutas
    "ruta_cat": "Ruta del archivo .CAT de donde se extrae información catastral de construcciones y Bienes Inmuebles.",
    "ruta_shp": "Ruta del archivo shapefile de donde se extrae la información espacial del parcelario."
    
}
    
columnas_provincias = {
    "cpro": "Código de provincia (extraído de rutas de datos de catastro).",
    "npro": "Nombre de la provincia.",
    "n_mun_pr": "Número de municipios procesados en la provincia.",
    "n_ct_pr": "Número total de construcciones en la provincia.",
    "n_bi_r_pr": "Número total de Bienes Inmuebles Residenciales en la provincia.",
    "sup_pr_sum": "Superficie total construida en la provincia (suma de todas las construcciones).",
    "sup_pr_med": "Superficie construida media por parcela en la provincia.",
    "ante_pr_med": "Antigüedad efectiva media de los Bienes Inmuebles Residenciales en la provincia.",
    "supc_pr_sum": "Superficie computable total de los Bienes Inmuebles Residenciales en la provincia.",
    "supc_pr_med": "Superficie computable media de los Bienes Inmuebles Residenciales en la provincia.",
    "tcus_pr": "Tipología constructiva predominante de los Bienes Inmuebles Residenciales en la provincia.",
    "calp_pr": "Calidad constructiva predominante de los Bienes Inmuebles Residenciales en la provincia.",
    "cvcn_pr": "Coeficiente de Valor de Construcción predominante de los Bienes Inmuebles Residenciales en la provincia.",
    "ivr_gau": "IVR medio de la provincia calculado con normalización GAU (Grandes Áreas Urbanas).",
    "ivr_loc": "IVR medio de la provincia calculado con normalización LOC (Local por municipio).",
}


