import pandas as pd
import numpy as np
import os
import math
import geopandas as gpd
import unicodedata

""" Data File dependencies """

IN_DATA_FILES_FOLDER = 'data_in'
OUT_DATA_FILES_FOLDER = './'

# Geojson with maps
GEOJSON_COUNTRIES   = os.path.join(IN_DATA_FILES_FOLDER,'countries.geojson')
GEOJSON_PROVINCES   = os.path.join(IN_DATA_FILES_FOLDER,'provincias_argentina.geojson')
GEOJSON_DEPARTMENTS = os.path.join(IN_DATA_FILES_FOLDER,'departamentos-argentina.json')
GEOJSON_BARRIOS     = os.path.join(IN_DATA_FILES_FOLDER,'barrios.geojson')
GEOJSON_CIUDADES_CORDOBA = os.path.join(IN_DATA_FILES_FOLDER,'cordoba/ciudades_cordoba.shp')

# Wiki csv with area,population info
INFO_COUNTRIES_FILE           = os.path.join(IN_DATA_FILES_FOLDER,'countries.csv')
INFO_PROVINCES_FILE           = os.path.join(IN_DATA_FILES_FOLDER,'info_provs.csv')
INFO_DEPARTMENTS_FILE         = os.path.join(IN_DATA_FILES_FOLDER,'departamentos.csv')
INFO_COMUNAS_FILE             = os.path.join(IN_DATA_FILES_FOLDER,'caba_comunas.csv')
INFO_BARRIOS_FILE             = os.path.join(IN_DATA_FILES_FOLDER,'barrios.csv')
INFO_CIUDADES_SANTA_FE_FILE   = os.path.join(IN_DATA_FILES_FOLDER,'poblacion_ciudades_santa_fe.csv')

COORDS_CIUDADES_SANTE_FE_FILE = os.path.join(IN_DATA_FILES_FOLDER, 'localidades-y-parajes.csv')

# Produced files with LOCATION (hierarchical) maps and info
GEOJSON_OUT = os.path.join(OUT_DATA_FILES_FOLDER,'maps_general.geojson')
INFO_OUT    = os.path.join(OUT_DATA_FILES_FOLDER,'info_general.csv')

""" Auxiliar functions """

def extract_province(name):
    """ Erase non province/department text (for Wikipedia tables scrapping). """
    redexes = ['Provincia de ','Provincia del ', 'Departamento de ','Departamento ','Bandera de la provincia de ',
             'Bandera de Provincia del ' ,'Bandera de Provincia de ', 'Partido de ','Partido del ',
             ' (Argentina)',' (Argentna)', 'Bandera de ', '*']
    for redex in redexes:
        name = name.replace(redex,"")
    return name
def normalize_str(s):
    """ Function for name normalization (handle áéíóú). """
    return unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii").upper()
def centroid_gdf(gdf):
    """ Given a GeoDataFrame LOCATION,geometry constructs LOCATION,LAT,LONG with centroids """
    df = gdf.copy()
    df['LAT'] = df['geometry'].centroid.apply(lambda p : p.coords[0][1])
    df['LONG'] = df['geometry'].centroid.apply(lambda p : p.coords[0][0])
    df = df.drop(columns=['geometry'])
    df = df.set_index('LOCATION')
    return df
def replace_numbers(s):
    repl = [('VEINTICINCO','25'),('NUEVE','9'),('DOS','2'),('PRIMERO DE','1 DE')]
    for x,y in repl:
        s = s.replace(x,y)
    return s
def barrio_to_comuna():
    df = gpd.read_file(GEOJSON_BARRIOS)
    df['barrio'] = df['barrio'].apply(normalize_str)
    barrio_to_comuna = {r['barrio']:r['comuna'] for _,r in df.iterrows()}
    return barrio_to_comuna

""" Functions that constructs GeoDataFrames with LOCATION,geometry """

def countries_gdf():
    select_countries=['ARGENTINA','CHILE','URUGUAY','PARAGUAY','BOLIVIA','BRAZIL','PERU','COLOMBIA','ECUADOR','GUYANA','PERU','SURINAME','VENEZUELA']
    df=gpd.read_file(GEOJSON_COUNTRIES)
    df['LOCATION']=df['ADMIN'].apply(normalize_str)
    df=df[df['LOCATION'].apply(lambda l : l in select_countries)]
    df=df[['LOCATION','geometry']]
    return df
def provinces_gdf():
    df = gpd.read_file(GEOJSON_PROVINCES)
    df['name']=df['name'].apply(extract_province)
    df['name']=df['name'].apply(normalize_str)
    df['name']=df['name'].apply(lambda n : 'ARGENTINA/'+n)
    df = df[ df['name'].apply(lambda n : n not in ['ARGENTINA/ISLA DE LOS ESTADOS']) ]
    df = df[ df.index.map(lambda x : x in set(df['name'].drop_duplicates().index) ) ]
    df = df.rename(columns = {'name':'LOCATION'})
    df = df[['LOCATION','geometry']].copy()
    df['LOCATION'] = df['LOCATION'].replace({'ARGENTINA/CATAMARACA':'ARGENTINA/CATAMARCA'})
    return df
def departments_gdf():
    df = gpd.read_file(GEOJSON_DEPARTMENTS)
    df['provincia']=df['provincia'].apply(normalize_str)
    df['departamento']=df['departamento'].apply(normalize_str)
    df['provincia']=df['provincia'].replace({'CIUDAD AUTONOMA DE BUENOS AIRES':'CABA'})
    df = df[df['departamento'].apply(lambda x : x not in ['ISLAS MALVINAS','ISLAS DEL ATLANTICO SUR'] )]
    df['LOCATION'] = 'ARGENTINA/'+df['provincia']+'/'+df['departamento'].apply(normalize_str)
    df = df[['LOCATION','geometry']].copy()
    return df
def gdf_caba(gdf_dep):
    df_caba = gdf_dep[ gdf_dep['LOCATION'].apply(lambda l : 'CABA' in l) ].copy()
    df_caba['LOCATION']='ARGENTINA/CABA'
    df_caba = df_caba.dissolve(by='LOCATION').reset_index()
    return df_caba
def barrios_gdf():
    df = gpd.read_file(GEOJSON_BARRIOS)
    df['barrio']=df['barrio'].apply(normalize_str)
    df['LOCATION']='ARGENTINA/CABA/COMUNA '+df['comuna'].apply(str)+'/'+df['barrio']
    df=df[['LOCATION','geometry']]
    return df
def ciudades_sante_fe_gdf(df_info):
    gdf = gpd.GeoDataFrame(df_info.reset_index(), geometry=gpd.points_from_xy(df_info.LONG, df_info.LAT))
    gdf=gdf[['LOCATION','geometry']]
    return gdf
def ciudades_cordoba_gdf():
    gdf = gpd.read_file(GEOJSON_CIUDADES_CORDOBA)
    gdf = gdf.rename(columns={'NOMLOC_10':'LOCATION'})
    gdf['DEPARTAMENTO']=gdf['NOM_DEPTO'].apply(normalize_str)
    gdf['LOCATION']=gdf['LOCATION'].apply(normalize_str)
    gdf=gdf.replace({
        'SAN MARCOS SIERRA': 'SAN MARCOS SIERRAS',
        'SAN MARCOS': 'SAN MARCOS SUD',
        'PTE ROQUE SAENZ PENA': 'PRESIDENTE ROQUE SAENZ PENA',
    })
    gdf['LOCATION']='ARGENTINA/CORDOBA/'+gdf['DEPARTAMENTO']+'/'+gdf['LOCATION']
    gdf = gdf[['LOCATION','geometry']]
    return gdf

""" Functions that constructs DataFrame with LOCATION,POPULATION,AREA """

def provinces_info():
    df = pd.read_csv(INFO_PROVINCES_FILE)
    df['LOCATION']=df['LOCATION'].apply(extract_province)
    df['LOCATION']=df['LOCATION'].apply(normalize_str)
    df['LOCATION']=df['LOCATION'].replace({'CIUDAD AUTONOMA DE BUENOS AIRES':'CABA'})
    df['LOCATION']=df['LOCATION'].apply(lambda n : 'ARGENTINA/'+n)
    df['POPULATION']=df['POPULATION'].apply(lambda s : int(''.join(c for c in s if not c.isspace())))
    df['AREA']=df['AREA'].apply(lambda s : int(''.join(c for c in s if not c.isspace())))
    df = df.set_index('LOCATION')
    return df

def departments_info(provinces_names_check = None):
    df = pd.read_csv(INFO_DEPARTMENTS_FILE)
    df['DEPARTAMENTO']=df['DEPARTAMENTO'].apply(extract_province)
    df['DEPARTAMENTO']=df['DEPARTAMENTO'].apply(normalize_str)

    df['PROVINCIA']=df['PROVINCIA'].apply(lambda l : l.replace("(Argentina)",""))
    df['PROVINCIA']=df['PROVINCIA'].apply(extract_province)
    df['PROVINCIA']=df['PROVINCIA'].apply(lambda l : l[len(l)//2+1:])
    df['PROVINCIA']=df['PROVINCIA'].apply(lambda l : 'Tierra del Fuego' if 'Tierra del Fuego' in l else l)
    df['PROVINCIA']=df['PROVINCIA'].apply(normalize_str)
    if provinces_names_check:
        assert set(df['PROVINCIA'])==provinces_names_check

    df['POPULATION']=df['POBLACION'].apply(lambda s : int(''.join(c for c in s if c.isdigit())))
    df['AREA']=df['AREA'].apply(lambda s : int(''.join(c for c in s if c.isdigit() or c=='.' or c==',')))

    df['LOCATION'] = 'ARGENTINA/'+  df['PROVINCIA'] + '/' + df['DEPARTAMENTO']
    df=df[['LOCATION','POPULATION','AREA']]
    df = df[df['LOCATION'].apply(lambda x : x not in ['ARGENTINA/TIERRA DEL FUEGO/ANTARTIDA ARGENTINA',
                                                      'ARGENTINA/TIERRA DEL FUEGO/ISLAS DEL ATLANTICO SUR'] )]
    df=df.set_index('LOCATION')
    df.index = df.index.map(replace_numbers)
    return df
def comunas_info():
    df = pd.read_csv(INFO_COMUNAS_FILE)
    df['LOCATION']='ARGENTINA/CABA/'+df['COMUNA'].apply(normalize_str)
    df=df.drop(columns=['COMUNA'])
    df=df.set_index('LOCATION')
    df['POPULATION']=df['POPULATION'].apply(lambda s : int(''.join(c for c in s if c.isdigit())))
    df['AREA']=df['AREA'].apply(lambda s : float(''.join(c for c in s.replace(',','.') if c.isdigit() or c=='.')))
    return df
def barrios_info():
    df = pd.read_csv(INFO_BARRIOS_FILE)
    barrio_to_comuna_dict = barrio_to_comuna()
    df=df[df['LOCATION'].apply(lambda l : "Comuna" not in l)]
    df['LOCATION']=df['LOCATION'].apply(normalize_str)
    df['LOCATION']=df['LOCATION'].apply(lambda l : l.rstrip().lstrip())
    df['LOCATION']=df['LOCATION'].replace({
        'LUGANO':'VILLA LUGANO',
        'SANTA RITA':'VILLA SANTA RITA',
        'VILLA GRAL MITRE':'VILLA GRAL. MITRE'
    })
    df['AREA']=df['AREA'].apply(lambda s : float(''.join(c for c in s.replace(',','.') if c.isdigit() or c=='.')))
    df['LOCATION']=df['LOCATION'].apply(lambda b: 'ARGENTINA/CABA/COMUNA {}/{}'.format(barrio_to_comuna_dict[b],b))
    df=df.set_index('LOCATION')
    return df

def ciudades_sante_fe_info():
    # Get coordinates
    df_coords = pd.read_csv(COORDS_CIUDADES_SANTE_FE_FILE)
    df_coords['nombre']=df_coords['nombre'].apply(normalize_str)
    df_coords['nombre']=df_coords['nombre'].apply(lambda s : s[:s.index('(')] if '(' in s else s)
    df_coords['departamento_nombre']=df_coords['departamento_nombre'].apply(normalize_str)
    df_coords['departamento_nombre']=df_coords['departamento_nombre'].replace({'NUEVE DE JULIO':'9 DE JULIO'})
    df_coords = df_coords.rename(columns={'lat':'LAT','lon':'LONG'})
    df_coords['LOCATION']='ARGENTINA/SANTA FE/'+df_coords['departamento_nombre']+'/'+df_coords['nombre']
    df_coords = df_coords[['LOCATION','LAT','LONG']]
    # Get populations
    df_pob = pd.read_csv(INFO_CIUDADES_SANTA_FE_FILE)
    df_pob['POPULATION']=df_pob['POPULATION'].apply(lambda p : int(p.replace('.','') if type(p)==str else p))
    df_pob['ciudad']=df_pob['ciudad'].apply(normalize_str)
    df_pob['ciudad']=df_pob['ciudad'].apply(lambda s : s[:s.index('(')] if '(' in s else s)
    df_pob['departamento']=df_pob['departamento'].apply(normalize_str)
    df_pob['departamento']=df_pob['departamento'].replace({'NUEVE DE JULIO':'9 DE JULIO'})
    df_pob['LOCATION']='ARGENTINA/SANTA FE/'+df_pob['departamento']+'/'+df_pob['ciudad']
    # Merge
    df_info = pd.merge(df_coords,df_pob[['LOCATION','POPULATION']],on='LOCATION',how='left')
    df_info = df_info.set_index('LOCATION')
    df_info['AREA']=math.nan
    return df_info

def ciudades_cordoba_info(gdf_ciudades_cordoba):
    df = centroid_gdf(gdf_ciudades_cordoba)
    df['AREA']=math.nan
    df['POPULATION']=math.nan
    return df

if __name__ == '__main__':
    print('Getting all geojsons...')
    gdf_paises = countries_gdf()
    gdf_dep = departments_gdf()
    gdf_prov = gpd.GeoDataFrame( pd.concat([provinces_gdf(),gdf_caba(gdf_dep)], ignore_index=True) )
    gdf_prov = gdf_prov.set_index('LOCATION')
    new_buenos_aires = gdf_prov.loc['ARGENTINA/BUENOS AIRES','geometry'].difference(gdf_prov.loc['ARGENTINA/CABA','geometry'])
    gdf_prov.loc['ARGENTINA/BUENOS AIRES','geometry']=new_buenos_aires
    gdf_prov = gdf_prov.reset_index()
    gdf_barrios = barrios_gdf()
    gdf_ciudades_cordoba = ciudades_cordoba_gdf()

    print('Calculating centroids...')
    coords_paises = centroid_gdf(gdf_paises)
    coords_prov = centroid_gdf(gdf_prov)
    assert(len(coords_prov)==24)
    coords_dep = centroid_gdf(gdf_dep)
    coords_barrios = centroid_gdf(gdf_barrios)

    coords = pd.concat( [coords_paises,coords_prov,coords_dep,coords_barrios] )


    print('Construct info DataFrames with checks and add centroids...')
    print('    - Countries INFO...')
    df_paises = pd.read_csv(INFO_COUNTRIES_FILE).set_index('LOCATION')
    assert set(df_paises.index)==(set(coords_paises.index))
    df_paises = pd.merge(coords_paises,df_paises,left_index=True,right_index=True,how='outer')

    print('    - Provinces INFO...')
    df_prov = provinces_info()
    assert(len(df_prov)==24)
    assert set(df_prov.index)==(set(coords_prov.index))
    df_prov = pd.merge(coords_prov,df_prov,left_index=True,right_index=True)

    print('    - Departments INFO...')
    provinces_names = set(df_prov.index.map(lambda l : l[len('ARGENTINA/'):])).difference(set(['CABA']))
    df_dep = departments_info(provinces_names)

    replacement = {
     'ARGENTINA/BUENOS AIRES/CORONEL ROSALES':'ARGENTINA/BUENOS AIRES/CORONEL DE MARINA LEONARDO ROSALES',
     'ARGENTINA/BUENOS AIRES/GENERAL MADARIAGA':'ARGENTINA/BUENOS AIRES/GENERAL JUAN MADARIAGA',
     'ARGENTINA/BUENOS AIRES/JOSE C. PAZ':'ARGENTINA/BUENOS AIRES/JOSE C PAZ',
     'ARGENTINA/BUENOS AIRES/LEANDRO N. ALEM':'ARGENTINA/BUENOS AIRES/LEANDRO N ALEM',
     'ARGENTINA/CHACO/MAYOR LUIS JORGE FONTANA': 'ARGENTINA/CHACO/MAYOR LUIS J. FONTANA',
     'ARGENTINA/LA RIOJA/GENERAL JUAN FACUNDO QUIROGA':'ARGENTINA/LA RIOJA/GENERAL JUAN F. QUIROGA',
     'ARGENTINA/SANTIAGO DEL ESTERO/JUAN FELIPE IBARRA': 'ARGENTINA/SANTIAGO DEL ESTERO/JUAN F IBARRA',
    }

    df_dep.index = df_dep.index.map(lambda x : replacement.get(x,x))
    df_comunas = comunas_info()
    df_dep = pd.concat([df_dep,df_comunas])

    assert set(df_dep.index)==(set(coords_dep.index)).union({'ARGENTINA/BUENOS AIRES/LEZAMA'})
    df_dep = pd.merge(coords_dep,df_dep,left_index=True,right_index=True,how='outer')

    print('    - Barrios INFO...')
    df_barrios = barrios_info()
    assert set(coords_barrios.index)==(set(df_barrios.index))
    df_barrios = pd.merge(coords_barrios,df_barrios,left_index=True,right_index=True,how='outer')

    print('    - Santa Fe ciudades INFO...')
    df_ciudades_stafe = ciudades_sante_fe_info()

    print('    - Cordoba ciudades INFO...')
    df_ciudades_cordoba = ciudades_cordoba_info(gdf_ciudades_cordoba)

    print('Constructing geojson for Santa Fe cities...')
    gdf_ciudades_stafe = ciudades_sante_fe_gdf(df_ciudades_stafe)


    print('Joining all INFO in one file...')
    df_general = pd.concat([df_paises, df_prov, df_dep, df_barrios, df_ciudades_stafe, df_ciudades_cordoba])
    df_general.to_csv(INFO_OUT)

    print('Joining all geojson in one...')
    gdf_general = gpd.GeoDataFrame( pd.concat( [gdf_paises,gdf_prov,gdf_dep,gdf_barrios,gdf_ciudades_stafe,gdf_ciudades_cordoba], ignore_index=True) )
    gdf_general.to_file(GEOJSON_OUT, driver='GeoJSON')

    print('DONE!')
