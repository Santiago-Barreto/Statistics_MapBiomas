"""
Configuración Global - MapBiomas Colombia
Contiene las rutas de los assets de Google Earth Engine y los parámetros 
visuales estándar para la clasificación LULC.
"""

ASSET_PARENT = "projects/mapbiomas-colombia/assets/LULC/COLECCION4/ESTADISTICAS/"
ASSET_REGIONES = "projects/mapbiomas-colombia/assets/DATOS_AUXILIARES/VECTORES/col-clasificacion-regiones-c3"

BASE_PATH_V1 = "projects/mapbiomas-colombia/assets/LULC/COLECCION4/clasificacion"
BASE_PATH_VX = "projects/mapbiomas-colombia/assets/LULC/COLECCION4/clasificacion-ft"

LEYENDA_MAPBIOMAS = {
    1: {"label": "Formación boscosa", "color": "#1F8D49", "level": 1},
    3: {"label": "Bosque", "color": "#1F8D49", "level": 2},
    5: {"label": "Manglar", "color": "#04381D", "level": 2},
    6: {"label": "Bosque inundable", "color": "#026975", "level": 2},
    49: {"label": "Vegetación leñosa sobre arena", "color": "#02D659", "level": 2},
    10: {"label": "Formación natural no boscosa", "color": "#D6BC74", "level": 1},
    11: {"label": "Formación natural no forestal inundable", "color": "#519799", "level": 2},
    12: {"label": "Formación herbácea", "color": "#D6BC74", "level": 2},
    32: {"label": "Planicie de marea hipersalina", "color": "#FC8114", "level": 2},
    29: {"label": "Afloramiento rocoso", "color": "#FFAA5F", "level": 2},
    50: {"label": "Vegetación herbácea sobre arena", "color": "#AD5100", "level": 2},
    13: {"label": "Otra formación natural no forestal", "color": "#D89F5C", "level": 2},
    81: {"label": "Herbazales o arbustales andinos", "color": "#DFEB62", "level": 2},
    82: {"label": "Herbazales o arbustales andinos inundables", "color": "#6FC179", "level": 2},
    14: {"label": "Área agropecuaria", "color": "#FFEFC3", "level": 1},
    9: {"label": "Silvicultura", "color": "#7A5900", "level": 2},
    35: {"label": "Palma aceitera", "color": "#9065D0", "level": 2},
    74: {"label": "Plátano y banano (beta)", "color": "#BE83F7", "level": 2},
    21: {"label": "Mosaico de agricultura o pasto", "color": "#FFEFC3", "level": 2},
    22: {"label": "Área sin vegetación", "color": "#D4271E", "level": 1},
    23: {"label": "Playas, dunas y bancos de arena", "color": "#FFA07A", "level": 2},
    24: {"label": "Infraestructura urbana", "color": "#D4271E", "level": 2},
    30: {"label": "Minería", "color": "#9C0027", "level": 2},
    68: {"label": "Otra área natural sin vegetación", "color": "#E97A7A", "level": 2},
    25: {"label": "Otra área sin vegetación", "color": "#DB4D4F", "level": 2},
    75: {"label": "Parques solares", "color": "#C12100", "level": 2},
    26: {"label": "Cuerpo de agua", "color": "#2532E4", "level": 1},
    33: {"label": "Río, lago u océano", "color": "#2532E4", "level": 2},
    31: {"label": "Acuicultura", "color": "#091077", "level": 2},
    34: {"label": "Glaciar y nival", "color": "#93DFE6", "level": 2},
    27: {"label": "No observado", "color": "#000000", "level": 1}
}

MAPBIOMAS_PALETTE = ["#FFFFFF"] * 100
for id_clase, info in LEYENDA_MAPBIOMAS.items():
    if id_clase < 100:
        MAPBIOMAS_PALETTE[id_clase] = info["color"]