Language: 1) English 2) Español 3) Català

IVR Plugin (Residential Vulnerability Index) 
Language: English
===========================================

Overview
--------
The IVR Plugin is a QGIS plugin designed to calculate and analyze the Residential Vulnerability Index (IVR) using cadastral and spatial data.

It provides tools to support urban analysis by identifying patterns of residential vulnerability at different spatial scales, enabling better-informed decision-making in urban planning and policy.

---

Features
--------
- Calculation of Residential Vulnerability Index (IVR)
- Integration with cadastral data sources
- Automated data processing workflows
- Spatial visualization of vulnerability patterns
- User-friendly graphical interface within QGIS

---

Requirements
------------
- QGIS 3.34 or higher 
- Python 3 (included with QGIS)

---

Installation
------------

From QGIS Plugin Manager (recommended):
1. Open QGIS
2. Go to Plugins > Manage and Install Plugins
3. Search for "IVR Plugin"
4. Click Install

Manual installation:
1. Download the plugin .zip file
2. Extract it into your QGIS plugins directory:

C:/Users/<your_user>/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins

3. Restart QGIS
4. Enable the plugin in Plugin Manager

---

Usage
-----
1. Open QGIS
2. Load your spatial and cadastral datasets --> https://www.sedecatastro.gob.es/
3. Launch the IVR Plugin from the Plugins menu
4. Configure input parameters
5. Run the analysis to generate IVR outputs

---

Data Requirements
-----------------
The plugin is designed to work with:
- Cadastral data ("Descarga de información alfanumérica por provincia (formato CAT)")
- Vector layers ("Descarga de cartografía vectorial por provincia (formato Shapefile)")
- Install 7-Zip to extract files from large provinces
---

Limitations
-----------
- Requires downloading cadastral data from the Spanish Directorate General for Cadastre (Dirección General del Catastro) using a valid digital identity certificate
- Requires properly formatted input data
- Requires 7-Zip to extract data files in some provinces
- Performance may vary depending on dataset size

---

Contributing
------------
Contributions are welcome. Please open an issue or submit a pull request in the repository.

---

License
-------
This plugin is licensed under the GNU General Public License v2 or later (GPL v2+).

This software has been developed as part of formal academic research. If you use this plugin in your work, please cite the following reference:

Blasco, M.; Shurupov, N.; Aguilera, F.; Sánchez, I. & Prada, J. (2025). Información catastral y análisis de la vulnerabilidad residencial: hacia una herramienta para su análisis en las ciudades españolas. En XXIX Congreso de la Asociación Española de Geografía: Desafíos de la Geografía ante el Cambio Global. Cáceres, 14-17 octubre de 2025.
---

Author
------
Manuel Blasco Jiménez (UAH)

---

Acknowledgements
----------------
This plugin was initially generated using the QGIS Plugin Builder (GeoApt LLC) and subsequently developed and extended as part of academic research on Residential Vulnerability Index (IVR) analysis.

---

References
----------
Blasco, M.; Shurupov, N.; Aguilera, F.; Sánchez, I. & Prada, J. (2025). Información catastral y análisis de la vulnerabilidad residencial: hacia una herramienta para su análisis en las ciudades españolas. En XXIX Congreso de la Asociación Española de Geografía: Desafíos de la Geografía ante el Cambio Global. Cáceres, 14-17 octubre de 2025.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
IVR Plugin (Índice de Vulnerabilidad Residencial)
Idioma: Español
===========================================

Descripción general
--------
El IVR Plugin es un complemento de QGIS diseñado para calcular y analizar el Índice de Vulnerabilidad Residencial (IVR) a partir de datos catastrales y espaciales.

Proporciona herramientas para apoyar el análisis urbano mediante la identificación de patrones de vulnerabilidad residencial a diferentes escalas espaciales, facilitando una mejor toma de decisiones en planificación urbana y políticas públicas.

---

Funcionalidades
--------
- Cálculo del Índice de Vulnerabilidad Residencial (IVR)
- Integración con datos catastrales
- Procesamiento automatizado de datos
- Visualización espacial de patrones de vulnerabilidad
- Interfaz gráfica fácil de usar dentro de QGIS

---

Requisitos
------------
- QGIS 3.34 o superior
- Python 3 (incluido en QGIS)

---

Instalación
------------

Desde el gestor de plugins de QGIS (recomendado):
1. Abrir QGIS
2. Ir a Plugins > Administrar e instalar complementos
3. Buscar "IVR Plugin"
4. Hacer clic en Instalar

Instalación manual:
1. Descargar el archivo .zip del plugin
2. Extraerlo en el directorio de plugins de QGIS:

C:/Users/<your_user>/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins

3. Reiniciar QGIS
4. Activar el plugin en el gestor de complementos

---

Uso
-----
1. Abrir QGIS
2. Cargar los datos espaciales y catastrales --> https://www.sedecatastro.gob.es/
3. Ejecutar el IVR Plugin desde el menú de Plugins
4. Configurar los parámetros de entrada
5. Ejecutar el análisis para generar los resultados del IVR

---

Requisitos de datos
-----------------
El plugin está diseñado para trabajar con:
- Datos catastrales ("Descarga de información alfanumérica por provincia (formato CAT)")
- Capas vectoriales ("Descarga de cartografía vectorial por provincia (formato Shapefile)")
- Instalación de 7-Zip para descomprimir archivos en provincias de gran tamaño

---

Limitaciones
-----------
- Requiere descargar datos del Catastro (Dirección General del Catastro) mediante un certificado digital válido
- Requiere datos de entrada correctamente formateados
- Requiere 7-Zip para descomprimir archivos en algunas provincias
- El rendimiento puede variar en función del tamaño del conjunto de datos

---

Contribuciones
------------
Las contribuciones son bienvenidas. Se anima a los usuarios a reportar errores, proponer mejoras o contribuir al desarrollo del plugin mediante el envío de pull requests a través del repositorio.

---

Licencia
-------
Este plugin está licenciado bajo la GNU General Public License versión 2 o posterior (GPL v2+).

Este software ha sido desarrollado como parte de una investigación académica formal. Si utiliza este plugin en su trabajo, por favor cite la siguiente referencia:

Blasco, M.; Shurupov, N.; Aguilera, F.; Sánchez, I. & Prada, J. (2025). Información catastral y análisis de la vulnerabilidad residencial: hacia una herramienta para su análisis en las ciudades españolas. En XXIX Congreso de la Asociación Española de Geografía: Desafíos de la Geografía ante el Cambio Global. Cáceres, 14-17 octubre de 2025.

---

Autor
------
Manuel Blasco Jiménez (UAH)

---

Agradecimientos
----------------
Este plugin fue generado inicialmente utilizando QGIS Plugin Builder (GeoApt LLC) y posteriormente desarrollado y ampliado como parte de una investigación académica sobre el análisis del Índice de Vulnerabilidad Residencial (IVR).

---

Referencias
----------
Blasco, M.; Shurupov, N.; Aguilera, F.; Sánchez, I. & Prada, J. (2025). Información catastral y análisis de la vulnerabilidad residencial: hacia una herramienta para su análisis en las ciudades españolas. En XXIX Congreso de la Asociación Española de Geografía: Desafíos de la Geografía ante el Cambio Global. Cáceres, 14-17 octubre de 2025.

------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
IVR Plugin (Índex de Vulnerabilitat Residencial)
Idioma: Català
===========================================

Descripció general
--------
El IVR Plugin és un complement de QGIS dissenyat per calcular i analitzar l'Índex de Vulnerabilitat Residencial (IVR) a partir de dades cadastrals i espacials.

Proporciona eines per donar suport a l'anàlisi urbana mitjançant la identificació de patrons de vulnerabilitat residencial a diferents escales espacials, facilitant una millor presa de decisions en planificació urbana i polítiques públiques.

---

Funcionalitats
--------
- Càlcul de l'Índex de Vulnerabilitat Residencial (IVR)
- Integració amb dades cadastrals
- Processament automatitzat de dades
- Visualització espacial de patrons de vulnerabilitat
- Interfície gràfica fàcil d'utilitzar dins de QGIS

---

Requisits
------------
- QGIS 3.34 o superior
- Python 3 (inclòs a QGIS)

---

Instal·lació
------------

Des del gestor de complements de QGIS (recomanat):
1. Obrir QGIS
2. Anar a Complements > Gestionar i instal·lar complements
3. Cercar "IVR Plugin"
4. Fer clic a Instal·lar

Instal·lació manual:
1. Descarregar el fitxer .zip del plugin
2. Extreure'l al directori de complements de QGIS:

C:/Users/<your_user>/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins

3. Reiniciar QGIS
4. Activar el plugin al gestor de complements

---

Ús
-----
1. Obrir QGIS
2. Carregar les dades espacials i cadastrals --> https://www.sedecatastro.gob.es/
3. Executar l'IVR Plugin des del menú de Complements
4. Configurar els paràmetres d'entrada
5. Executar l'anàlisi per generar els resultats de l'IVR

---

Requisits de dades
-----------------
El plugin està dissenyat per treballar amb:
- Dades cadastrals ("Descarga de información alfanumérica por provincia (formato CAT)")
- Capes vectorials ("Descarga de cartografía vectorial por provincia (formato Shapefile)")
- Instal·lació de 7-Zip per descomprimir arxius en províncies de gran mida

---

Limitacions
-----------
- Requereix descarregar dades del Cadastre (Dirección General del Catastro) mitjançant un certificat digital vàlid
- Requereix dades d'entrada correctament formatejades
- Requereix 7-Zip per descomprimir arxius en algunes províncies
- El rendiment pot variar en funció de la mida del conjunt de dades

---

Contribucions
------------
Les contribucions són benvingudes. Es recomana als usuaris informar d'errors, proposar millores o contribuir al desenvolupament del plugin mitjançant pull requests a través del repositori.

---

Llicència
-------
Aquest plugin està llicenciat sota la GNU General Public License versió 2 o posterior (GPL v2+).

Aquest programari ha estat desenvolupat com a part d'una investigació acadèmica formal. Si utilitzeu aquest plugin en el vostre treball, si us plau citeu la següent referència:

Blasco, M.; Shurupov, N.; Aguilera, F.; Sánchez, I. & Prada, J. (2025). Información catastral y análisis de la vulnerabilidad residencial: hacia una herramienta para su análisis en las ciudades españolas. En XXIX Congreso de la Asociación Española de Geografía: Desafíos de la Geografía ante el Cambio Global. Cáceres, 14-17 octubre de 2025.

---

Autor
------
Manuel Blasco Jiménez (UAH)

---

Agraïments
----------------
Aquest plugin va ser generat inicialment utilitzant QGIS Plugin Builder (GeoApt LLC) i posteriorment desenvolupat i ampliat com a part d'una investigació acadèmica sobre l'anàlisi de l'Índex de Vulnerabilitat Residencial (IVR).

---

Referències
----------
Blasco, M.; Shurupov, N.; Aguilera, F.; Sánchez, I. & Prada, J. (2025). Información catastral y análisis de la vulnerabilidad residencial: hacia una herramienta para su análisis en las ciudades españolas. En XXIX Congreso de la Asociación Española de Geografía: Desafíos de la Geografía ante el Cambio Global. Cáceres, 14-17 octubre de 2025.


Copyright (C) 2026 Manuel Blasco Jiménez

GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007