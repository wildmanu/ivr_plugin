# -*- coding: utf-8 -*-
"""
Archivo ui_buldings.py

Este archivo alberga todas las funciones relativas a la lógica del Front que 
relaciona la ui. con el funcionamiento de cada botón. 

figuras creadas para el IVR plugin.

Fecha creación:     25/01/2026
Fecha modificación: 05/02/2026 --> Última modificación 

Listado modificaciones y avances 

1) 05/02/02026 
- Añade bt_15 lófica para que siempre aparezca seleccioanda filtro Tabla 15

@author: manuel
"""
from contextlib import contextmanager

@contextmanager
def _bloquear_senales(w):
    try:
        w.blockSignals(True)
        yield
    finally:
        w.blockSignals(False)

# Lógica principal 
def setup_ui_logic(dlg):
    """Habilitar/deshabilitar controles según checks/combos."""

    def actualizar_controles_por_combo():
        if not hasattr(dlg, "bt_met"):
            return

        habilitar = dlg.bt_met.currentIndex() != 0
        botones = ["bt_rag", "bt_ivr_gau", "bt_ivr_loc", "bt_gau"]

        for nombre in botones:
            if hasattr(dlg, nombre):
                w = getattr(dlg, nombre)
                w.setEnabled(habilitar)

                # Si vuelve a "Sin clasificar", resetear estado
                if not habilitar:
                    if hasattr(w, "setChecked"):
                        w.setChecked(False)
                    if hasattr(w, "setValue"):
                        w.setValue(0)
                        
        if habilitar and hasattr(dlg, "bt_ivr_gau") and hasattr(dlg, "bt_ivr_loc"):
                # Asegura que están habilitados antes de marcar
                dlg.bt_ivr_gau.setEnabled(True)
                dlg.bt_ivr_loc.setEnabled(True)
        
                with _bloquear_senales(dlg.bt_ivr_gau):
                    dlg.bt_ivr_gau.setChecked(True)
                with _bloquear_senales(dlg.bt_ivr_loc):
                    dlg.bt_ivr_loc.setChecked(False)
                        
    def setup_exclusion_gau_loc(dlg):
        """Hace que IVR GAU y LOC mutuamente excluyentes."""
    
        def on_gau_toggled(checked):
            if not (hasattr(dlg, "bt_ivr_gau") and hasattr(dlg, "bt_ivr_loc")):
                return
            if checked:
                with _bloquear_senales(dlg.bt_ivr_loc):
                    dlg.bt_ivr_loc.setChecked(False)
    
        def on_loc_toggled(checked):
            if not (hasattr(dlg, "bt_ivr_gau") and hasattr(dlg, "bt_ivr_loc")):
                return
            if checked:
                with _bloquear_senales(dlg.bt_ivr_gau):
                    dlg.bt_ivr_gau.setChecked(False)
    
        # Conectar (si son checkables / emiten toggled)
        if hasattr(dlg, "bt_ivr_gau") and hasattr(dlg.bt_ivr_gau, "toggled"):
            dlg.bt_ivr_gau.toggled.connect(on_gau_toggled)
    
        if hasattr(dlg, "bt_ivr_loc") and hasattr(dlg.bt_ivr_loc, "toggled"):
            dlg.bt_ivr_loc.toggled.connect(on_loc_toggled)
            
    # Conectar al combo
    if hasattr(dlg, "bt_met"):
        dlg.bt_met.currentIndexChanged.connect(actualizar_controles_por_combo)

    # Estado inicial
    actualizar_controles_por_combo()
    setup_exclusion_gau_loc(dlg)
    
# Valores por defectos en la .ui
def setup_defaults(dlg):
    if hasattr(dlg, "bt_mix"):
        dlg.bt_mix.setOpacity(0.0)
    
    if hasattr(dlg, "bt_15") and hasattr(dlg.bt_15, "setChecked"):
            with _bloquear_senales(dlg.bt_15):
                dlg.bt_15.setChecked(True)

# Botones con funciones con lógica más detalalda definada en dialog
def setup_connections(dlg):
    if hasattr(dlg, "boton_ejecutar") and hasattr(dlg, "ejecutar_proceso"):
        dlg.boton_ejecutar.clicked.connect(dlg.ejecutar_proceso)

    # Respues revisar cancelar para que no se pierda en bucle segundo plano 
    if hasattr(dlg, "button_box"):
        dlg.button_box.accepted.connect(dlg.accept)
        dlg.button_box.rejected.connect(dlg.reject)

    if hasattr(dlg, "boton_entrada"):
        dlg.boton_entrada.clicked.connect(
            lambda: dlg.seleccionar_carpeta("entrada"))
        
    if hasattr(dlg, "boton_salida"):
        dlg.boton_salida.clicked.connect(
            lambda: dlg.seleccionar_carpeta("salida"))
        
