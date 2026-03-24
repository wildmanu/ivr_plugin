# -*- coding: utf-8 -*-
"""
Archivo ivr_qgis.py

Este archivo alberga todas las funciones para representar y tratar la capa en QGIS

Fecha creación:     09/02/2026

Listado modificaciones y avances 

1) 09/02/02026 
- Se unifican funcioens en este archivo

@author: manuel
"""

import os
from PyQt5.QtCore import QVariant, Qt
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsVectorLayer,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsProject,
    QgsSymbol,
    QgsRendererRange,
    QgsGraduatedSymbolRenderer
)

def detect_geom_col(gdf):
    """Detecta nombre de columna de geometría en GeoDataFrame."""
    if hasattr(gdf, "geometry") and gdf.geometry is not None:
        try:
            return gdf.geometry.name
        except Exception:
            pass
    if "geom" in getattr(gdf, "columns", []):
        return "geom"
    if "geometry" in getattr(gdf, "columns", []):
        return "geometry"
    raise ValueError("No encuentro columna de geometría ('geom'/'geometry').")

def detect_epsg(gdf, fallback=4326):
    """Detecta código EPSG del CRS del GeoDataFrame o devuelve fallback."""
    try:
        crs = getattr(gdf, "crs", None)
        if crs is None:
            return fallback
        if hasattr(crs, "to_epsg"):
            epsg = crs.to_epsg()
            return epsg if epsg is not None else fallback
        # si fuera string tipo "EPSG:3035"
        s = str(crs)
        if "EPSG" in s.upper():
            digits = "".join(ch for ch in s if ch.isdigit())
            return int(digits) if digits else fallback
    except Exception:
        pass
    return fallback

def convertir_tipo_serie(dtype_str):
    """Convierte tipo de dato pandas a tipo QVariant de QGIS."""
    # Mapeo simple pandas dtype -> QVariant
    ds = str(dtype_str).lower()
    if ds.startswith("int"):
        return QVariant.Int
    if ds.startswith("float"):
        return QVariant.Double
    if ds == "bool":
        return QVariant.Int
    return QVariant.String

def gdf_memoria_capa(gdf, layer_name="IVR", geom_col=None):
    """Convierte GeoDataFrame a capa vectorial en memoria de QGIS."""
    geom_col = geom_col or detect_geom_col(gdf)
    epsg = detect_epsg(gdf, fallback=4326)

    # Crear layer memoria (MultiPolygon por defecto; QGIS aceptará geometrías compatibles)
    vl = QgsVectorLayer(f"MultiPolygon?crs=EPSG:{epsg}", layer_name, "memory")
    pr = vl.dataProvider()

    # Campos
    fields = QgsFields()
    for col in gdf.columns:
        if col == geom_col:
            continue
        qtype = QVariant.String
        try:
            qtype = convertir_tipo_serie(gdf[col].dtype)
        except Exception:
            qtype = QVariant.String
        fields.append(QgsField(str(col), qtype))
    pr.addAttributes(fields)
    vl.updateFields()

    feats = []
    for _, row in gdf.iterrows():
        f = QgsFeature(vl.fields())

        attrs = []
        for col in gdf.columns:
            if col == geom_col:
                continue
            val = row[col]
            # NaN -> None
            try:
                if val != val:
                    val = None
            except Exception:
                pass
            # bool -> int (para evitar problemas)
            if isinstance(val, bool):
                val = int(val)
            attrs.append(val)
        f.setAttributes(attrs)

        geom = row[geom_col]
        if geom is None:
            continue

        # shapely -> WKB -> QgsGeometry
        try:
            wkb = geom.wkb
            qgeom = QgsGeometry()
            qgeom.fromWkb(wkb)
            if qgeom.isNull():
                continue
            f.setGeometry(qgeom)
        except Exception:
            continue

        feats.append(f)

    pr.addFeatures(feats)
    vl.updateExtents()
    return vl

def guardar_capa_gpkg(vlayer, gpkg_path, layer_name="IVR", overwrite_file=True):
    """Guarda capa vectorial QGIS en GeoPackage."""
    out_dir = os.path.dirname(gpkg_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name

    if overwrite_file:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    else:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        vlayer,
        gpkg_path,
        QgsProject.instance().transformContext(),
        options
    )

    # En QGIS 3.x suele ser una tupla de 4: (error, errorMessage, newFilename, newLayer)
    if isinstance(result, tuple):
        err_code = result[0]
        err_msg = result[1] if len(result) > 1 else ""
    else:
        # Fallback por si cambia la firma
        err_code = result
        err_msg = ""

    if err_code != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"Error guardando GeoPackage: {err_msg}")
        
def aplicar_simbologia_diccionario(vlayer, campo, dic_cortes_color, opacity=1.0):
    """
    Aplica simbología graduada a capa según diccionario de cortes y colores.
    
    Parametros:
        vlayer: QgsVectorLayer
        campo: str, nombre del campo numérico (ivr_gau o ivr_loc)
        dic_cortes_color: dict, {limite_inferior: '#RRGGBB'}
        opacity: float, opacidad 0-1 (default: 1.0)
    """

    # Ordenar cortes
    cortes = sorted(dic_cortes_color.items(), key=lambda x: float(x[0]))

    ranges = []

    for i, (vmin, color) in enumerate(cortes):
        vmin = float(vmin)

        # vmax = siguiente corte o infinito
        if i < len(cortes) - 1:
            vmax = float(cortes[i + 1][0])
            label = f"{vmin:.2f} – {vmax:.2f}"
        else:
            vmax = 1.10 # Valor máximo 1
            label = f"{vmin:.2f} - 1.00"

        symbol = QgsSymbol.defaultSymbol(vlayer.geometryType())
        symbol.setColor(QColor(color))
        symbol.setOpacity(opacity)

        # Quitar contorno en polígonos
        sl = symbol.symbolLayer(0)
        if sl is not None and hasattr(sl, "setStrokeStyle"):
            sl.setStrokeStyle(Qt.NoPen)

        rng = QgsRendererRange(vmin, vmax, symbol, label)
        ranges.append(rng)

    renderer = QgsGraduatedSymbolRenderer(campo, ranges)
    renderer.setMode(QgsGraduatedSymbolRenderer.Custom)

    vlayer.setRenderer(renderer)
    vlayer.triggerRepaint()