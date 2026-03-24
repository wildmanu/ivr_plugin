# -*- coding: utf-8 -*-

"""
Archivo ivr_texts.py

Este archivo alberga todas las funciones tooltip y whatsthis que tiene la ui. 
para dar conteto de los diferentes botones. 

Fecha creación:     25/01/2026
Fecha modificación: 05/02/2026 --> Última modificación 

Listado modificaciones y avances 

1) 05/02/02026 
- Añade bt_15 su info para tooltip y whatsthis 

@author: manuel
"""

def _set_tooltip_safe(dlg, name: str, text: str):
    w = getattr(dlg, name, None)
    if w is None:
        # En desarrollo: avisa. En producción podrías silenciarlo.
        # QMessageBox.warning(dlg, "UI", f"Falta el widget '{name}' para setToolTip")
        return
    w.setToolTip(text)

def _set_whatsthis_safe(dlg, name: str, text: str):
    w = getattr(dlg, name, None)
    if w is None:
        return
    w.setWhatsThis(text)

def setup_ui_texts(dlg):
    
    # 1.1 Ruta de entrada
    _set_tooltip_safe(dlg, "boton_entrada",
        "Añada la ruta a la carpeta con información descarga los ficheros .CAT y .SHP.")
    
    _set_whatsthis_safe(dlg, "boton_entrada",
        "Añada la ruta de la carpeta que contenga los ficheros descargados del Catastro "
        "(.CAT y .SHP). Recuerde que debe descargar previamente la información alfanumérica " 
        "por provincia en formato CAT (tipo urbano) y la cartografía vectorial en formato "
        "Shapefile (tipo Urbana sin Historia, incluyendo los ficheros SHP.zip y SHP.z01 si "
        "la provincia lo requiere)."
        )
    
    # 1.2 Ruta de salida
    _set_tooltip_safe(dlg, "boton_salida",
        "Añada la ruta dónde se guardará la información generada")
    
    _set_whatsthis_safe(dlg, "boton_salida",
        "Carpeta dónde se guardarán los reusltados, en caso de no completar dicho campo la "
        "información se generará en la carpeta de entrada en una nueva subcarpeta denominada 'Resultados'." 
        )
    
    # 2.1 Información Capa
    _set_tooltip_safe(dlg, "bt_org",
        "Añade información a la capa de variables originales del IVR agregadas a nivel de parcela.")
    _set_tooltip_safe(dlg, "bt_nor",
        "Añade información a la capa de variables normalizadas del IVR agregadas a nivel de parcela.")
    _set_tooltip_safe(dlg, "bt_gau",
        "Añade la clasificación resultante del análisis de las GAUs (requiere completar el Clasificador GAU).")
    _set_tooltip_safe(dlg, "br_adc",
        "Añade información adicional relevante a la capa, no relacionada con el IVR.")
    
    _set_whatsthis_safe(dlg, "bt_org",
    "Añade información agregada de las variables origniales del IVR de los Bienes Inmubles (BI) a nivel de parcela:\n"
    "A) Superficie media cómputable del BI (supc_pc)\n"
    "B) Antigüedad efectiva media del BI (ante_pc)\n"
    "C) Coeficiente de valor de construcción  del BI (cvcn_pc)\n"
    "C1) Tipología constructiva predomiente del BI (tcus_pc)\n"
    "C2) Calidad constructiva predomienante del BI (calp_pc)"
    )
    
    _set_whatsthis_safe(dlg, "bt_nor",
    "Añade información agregada de las variables normalizadas del IVR de los Bienes Inmubles (BI) a nivel de parcela:\n"
    "• Superficie media cómputable BI normalizada GAU (supc_n_gau)\n"
    "• Superficie media cómputable BI normalizada LOC (supc_n_loc)\n"
    "• Antigüedad efectiva media del BI normalizada GAU (ante_n_gau)\n"
    "• Antigüedad efectiva media del BI normalizada LOC (ante_n_loc)\n"
    "• Coeficiente de valor de construcción del BI normalizada GAU (cvct_n_gau)\n"
    "• Coeficiente de valor de construcción del BI normalizada LOC (cvct_n_loc)"
    )
    
    _set_whatsthis_safe(dlg, "bt_gau",
    "Al completar el 'Clasificador GAU' se añade la variable IVR GAU o IVR LOC clasificada a nivel de parcela:\n"
    "Se tiene en cuenta una muestra de 672 municipios de las GAUs de españa para datos de II Semetre de Catastro."
    )
    
    _set_whatsthis_safe(dlg, "br_adc",
    "Añade información agregada de variables edicionales derivadas de los Registros de Construcción (tabla 14):\n"
    "• Número de construcciones dentro de la parcela (n_ct)\n"
    "• Número de BI residenciales dentro de la parcela (n_bi)\n"
    "• Superficie total construida en la parcela (sup_pc)"
    )
    
    # 2.2 Clasificador GAU
    _set_tooltip_safe(dlg, "bt_met",
        "Métodos de clasificación disponibles para el Clasificador GAU.")
    _set_tooltip_safe(dlg, "bt_rag",
        "Número de clases para cada método (2 a 10).")
    _set_tooltip_safe(dlg, "bt_ivr_gau",
        "Se añadirá simbología al IVR GAU con el Clasificador GAU.")
    _set_tooltip_safe(dlg, "bt_ivr_loc",
        "Se añadirá simbología al IVR LOC con el Clasificador GAU.")
    
    _set_whatsthis_safe(dlg, "bt_met",
    "Métodos de clasificación (precalculados sobre 14 millones de BIs):\n"
    "• Q – Cuantiles: cada clase contiene el mismo número de elementos.\n"
    "• J – Jenks: minimiza la variabilidad interna y maximiza las diferencias entre clases.\n"
    "• I – Intervalos iguales: divide el rango de valores en tramos del mismo tamaño."
    )
    
    _set_whatsthis_safe(dlg, "bt_rag",
    "Número de clases con el que se cáculara el método de clasificación, entre 2 a 10 clases"
    )
    
    _set_whatsthis_safe(dlg, "bt_ivr_gau",
    "Se añadirá simbología al IVR GAU con la clasificación seleccioanda, pero se desactiva el IVR LOC."
    )
    
    _set_whatsthis_safe(dlg, "bt_ivr_loc",
    "Se añadirá simbología al IVR LOC con la clasificación seleccioanda, pero se desactiva el IVR GAU."
    )

    
    # 2.3 Filtros y CRS
    _set_tooltip_safe(dlg, "bt_15",
       "Seleccione sólo Bines Inmubles residenciales urbanos registrados en catastro."
       )

    _set_tooltip_safe(dlg, "bt_mix",
        "Filtro para eliminar BI residenciales mixtos con otros usos."
        )
    _set_tooltip_safe(dlg, "bt_crs",
       "Elija la proyección (EPSG) que mejor se adecúe al área de estudio."
       )

    _set_whatsthis_safe(dlg, "bt_15",
        "Se seleccionan las construcciones que esten clasificadas como Bines Inmuebles "
        "residenciales urbanos en el registro de Bienes Inmubles (Tabla tipo 15 en .CAT)."
    )

    _set_whatsthis_safe(dlg, "bt_mix",
        "Filtra los (BI) residenciales con usos mixtos cuya participación "
        "sea inferior al umbral especificado."
    )
    
    _set_whatsthis_safe(dlg, "bt_crs",
    "Proyecciones métricas recomendadas (EPSG) según el área de estudio:\n\n"
    "• EPSG:25830 – ETRS89 / UTM zona 30N\n"
    "  Uso recomendado: Península Ibérica (opción más habitual en España).\n\n"
    "• EPSG:25829 – ETRS89 / UTM zona 29N\n"
    "  Uso recomendado: Galicia occidental y zonas más al oeste.\n\n"
    "• EPSG:25831 – ETRS89 / UTM zona 31N\n"
    "  Uso recomendado: Cataluña oriental y Baleares.\n\n"
    "• EPSG:4083 / 4082 – REGCAN95 / UTM\n"
    "  Uso recomendado: Islas Canarias.\n\n"
    "• EPSG:3035 – ETRS89 / LAEA Europe (por defecto)\n"
    "Recomendación general: Seleccione siempre una proyección métrica adecuada al ámbito espacial del estudio."
    )
    
    # 3 Filtros y CRS
    _set_tooltip_safe(dlg, "bt_fsig",
        "Añade un histograma acomulada con las sigmoides más representativas")
    _set_tooltip_safe(dlg, "bt_fnor",
        "Añade una composción sobre el proceso de normalización variables del IVR")
    _set_tooltip_safe(dlg, "bt_mun",
        "Se añadirá un csv con infomración agregada por cada municipio.")
    _set_tooltip_safe(dlg, "bt_pro",
        "Se añadirá un csv con infomración agregada por cada provincia.")
    
    _set_whatsthis_safe(dlg, "bt_fsig",
    "Genera una carpeta nueva con un histograma acomulada con las sigmoides más representativas a nivel de BI."
    )
    
    _set_whatsthis_safe(dlg, "bt_fnor",
    "Genera una carpeta nueva con una composción sobre el proceso de normalización variables del IVR a nivel de BI."
    )
    
    _set_whatsthis_safe(dlg, "bt_mun",
    "Genera una carpeta nueva con un csv con infomración agregada por cada municipio a nivel de BI."
    )
    
    _set_whatsthis_safe(dlg, "bt_pro",
    "Genera una carpeta nueva con un csv con infomración agregada por cada provincia a nivel de BI."
    )

# Construir combos 
def setup_combo_metodos(dlg):
    
    # Opciones Método
    combo_met = getattr(dlg, "bt_met", None)
    if combo_met is None:
        return
    combo_met.clear()
    combo_met.addItems(["Sin clasificar", "Cuantiles", "Jenks", "Intervalos Iguales"])
    combo_met.setCurrentIndex(0)
    
    # Opciones CRS
    combo_crs = getattr(dlg, "bt_crs", None)
    if combo_crs is None:
        return
    combo_crs.clear()
    combo_crs.addItems([
    "ETRS89 / LAEA Europe (EPSG:3035) — Por defecto",
    "ETRS89 / UTM 30N (EPSG:25830) — Península Ibérica",
    "ETRS89 / UTM 29N (EPSG:25829) — Galicia occidental",
    "ETRS89 / UTM 31N (EPSG:25831) — Cataluña y Baleares",
    "REGCAN95 / UTM 27N (EPSG:4082) — Canarias occidentales",
    "REGCAN95 / UTM 28N (EPSG:4083) — Canarias orientales",])
    combo_crs.setCurrentIndex(0)
    

















