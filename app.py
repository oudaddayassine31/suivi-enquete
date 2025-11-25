#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application de Suivi des Enquêtes Parcellaires
Version UNIVERSELLE - Gère TOUS les formats de geopackage
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import json
import io
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Configuration
DATABASE_PATH = 'data/enquete_parcellaire.db'
UPLOAD_FOLDER = 'data/uploads'
os.makedirs('data', exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuration des zones
ZONES_CONFIG = {
    'Tetouan': [
        {'code': 'Tet1', 'nom': 'Zaouiat sidi kacem'},
        {'code': 'Tet2', 'nom': 'Oulad ali mansour'},
        {'code': 'Tet3', 'nom': 'Iahyout bni leit'},
        {'code': 'Tet4', 'nom': 'Beni leit'}
    ],
    'Larache': [
        {'code': 'L1', 'nom': 'Bni Bourahou bni Garfett'},
        {'code': 'L2', 'nom': 'Ayacha'},
        {'code': 'L3', 'nom': 'Tatoft'}
    ],
    'Ouazzane': [
        {'code': 'Ouz1', 'nom': 'Zone 1'},
        {'code': 'Ouz2', 'nom': 'Zone 2'},
        {'code': 'Ouz3', 'nom': 'Zone 3'},
        {'code': 'Ouz4', 'nom': 'Zone 4'}
    ],
    'Hoceima': [
        {'code': 'Hoc1', 'nom': 'Nekour'},
        {'code': 'Hoc2', 'nom': 'PMH'},
        {'code': 'Hoc3', 'nom': 'Arbaa Taourirt'},
        {'code': 'Hoc4', 'nom': 'Ait Karma'}
    ],
    'Chefchaouen': [
        {'code': 'Chef1', 'nom': 'Zone 1'},
        {'code': 'Chef2', 'nom': 'Zone 2'},
        {'code': 'Chef3', 'nom': 'Zone 3'},
        {'code': 'Chef4', 'nom': 'Zone 4'},
        {'code': 'Chef5', 'nom': 'Dar akoubaa'}
    ],
    'Tanger': [
        {'code': 'Tang1', 'nom': 'Anjra1'},
        {'code': 'Tang2', 'nom': 'Anjra2'},
        {'code': 'Tang3', 'nom': 'Mallousa sapement des berges'}
    ]
}

# ============================================================================
# HELPER: MAPPING NOMS DE COLONNES (Gère format ancien et nouveau)
# ============================================================================

def get_field_value(row, field_mappings):
    """
    Récupère une valeur depuis un row, en testant plusieurs noms possibles
    field_mappings: liste de noms possibles pour le champ
    """
    for field_name in field_mappings:
        if field_name in row.index:
            val = row.get(field_name)
            if pd.notna(val):
                return val
    return ''

# Mappings: [nouveau_format, ancien_format_avec_\n, ancien_format_avec_espaces]
FIELD_MAPPINGS = {
    'sous_zone': ['sous_zone', 'Sous zone \n', 'Sous zone'],
    'ordre': ['ordre', 'Ordre \n', 'Ordre'],
    'plle': ['plle', 'Plle'],
    'num_tf_req': ['num_tf_req', 'N° TF/Req\n', 'N° TF/Req'],
    'indice': ['indice', 'Indice\n', 'Indice'],
    'adresse_francais': ['adresse_francais', 'Adresse Français\n', 'Adresse Français'],
    'adresse_arabe': ['adresse_arabe', 'Adresse Arabe\n', 'Adresse Arabe'],
    'nom_parcelle_f': ['nom_parcelle_f', 'Nom Parcelle(F)\n', 'Nom Parcelle(F)'],
    'nature_principale_a': ['nature_principale_a', 'Nature Principale(A)\n', 'Nature Principale(A)'],
    'consist_materielle': ['consist_materielle', 'consist_matrielle', 'Consist Matrielle\n', 'Consist Matrielle'],
    'consist_mat_a': ['consist_mat_a', 'CONSIST MAT (A)'],
    'type_speculation': ['type_speculation', 'Type de Spéculation\n', 'Type de Spéculation'],
    'type_sol': ['type_sol', 'Type de sol\n', 'Type de sol'],
    'regime_foncier': ['regime_foncier'],
    'droits_reels': ['droits_reels', 'Droits Réels\n', 'Droits Réels'],
    'oppositions': ['oppositions', 'Oppositions\n', 'Oppositions'],
    'charges_servitudes': ['charges_servitudes', 'Charges et Servitudes\n', 'Charges et Servitudes'],
    'quote_denominateur': ['quote_denominateur', 'Quote Dénominateur\n', 'Quote Dénominateur'],
    'mappe': ['mappe', 'Mappe\n', 'Mappe'],
    'centroid_x': ['centroid_x', 'Coordonnées du centroîde (X)', 'Coordonnées du centroide (X)'],
    'centroid_y': ['centroid_y', 'Coordonnées du centroîde (Y)', 'Coordonnées du centroide (Y)'],
    'observations': ['observations', 'Observations \n', 'Observations'],
    'autre': ['autre', 'Autre \n', 'Autre'],
    
    # Propriétaires
    'nom_arabe': ['nom_arabe', 'Nom Arabe \n', 'Nom Arabe'],
    'prenom_arabe': ['prenom_arabe', 'Prenom Arabe \n', 'Prenom Arabe'],
    'autre_nom_arabe': ['autre_nom_arabe', 'Autre Nom Arabe\n', 'Autre Nom Arabe'],
    'nom_francais': ['nom_francais', 'Nom français \n', 'Nom français'],
    'prenom_francais': ['prenom_francais', 'Prenom français\n', 'Prenom français'],
    'autre_nom_francais': ['autre_nom_francais', 'Autre Nom français\n', 'Autre Nom français'],
    'date_naissance': ['date_naissance', 'Date Naissance\n', 'Date Naissance'],
    'CINE': ['CINE', 'C.I.N.E\n', 'C.I.N.E'],
    'situation_famille': ['situation_famille', 'Situation Famille\n', 'Situation Famille'],
    'nom_conjoint': ['nom_conjoint', 'Nom Conjoint\n', 'Nom Conjoint'],
    'num_tel': ['num_tel', 'N° de Tel\n', 'N° de Tel'],
    'adresse_proprietaire': ['adresse_proprietaire', 'ADRESSE PROPRIETAIRE', 'Adresse Proprietaire']
}

# ============================================================================
# BASE DE DONNÉES
# ============================================================================

def init_database():
    """Initialiser la base de données"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT NOT NULL,
            code_zone TEXT NOT NULL,
            nom_zone TEXT NOT NULL,
            enqueteur TEXT,
            date_debut_enquete DATE,
            surface_totale_ha REAL,
            geom_limite TEXT,
            cloturee INTEGER DEFAULT 0,
            date_cloture DATE,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(province, code_zone)
        )
    ''')
    
    # MIGRATION: Ajouter colonnes si elles manquent
    try:
        cursor.execute("SELECT cloturee FROM zones LIMIT 1")
    except sqlite3.OperationalError:
        print("🔧 Migration: Ajout colonne 'cloturee'")
        cursor.execute("ALTER TABLE zones ADD COLUMN cloturee INTEGER DEFAULT 0")
    
    try:
        cursor.execute("SELECT date_cloture FROM zones LIMIT 1")
    except sqlite3.OperationalError:
        print("🔧 Migration: Ajout colonne 'date_cloture'")
        cursor.execute("ALTER TABLE zones ADD COLUMN date_cloture DATE")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enquete_actuelle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT NOT NULL,
            code_zone TEXT NOT NULL,
            numero_jour INTEGER,
            date_enquete DATE,
            nb_parcelles INTEGER,
            surface_enquetee_ha REAL,
            surface_restante_ha REAL,
            pourcentage_avancement REAL,
            geopackage_path TEXT,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(province, code_zone)
        )
    ''')
    
    # Table historique pour garder trace de chaque upload
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historique_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT NOT NULL,
            code_zone TEXT NOT NULL,
            numero_jour INTEGER,
            date_maj DATE,
            nb_parcelles INTEGER,
            surface_enquetee_ha REAL,
            parcelles_ajoutees INTEGER,
            surface_ajoutee_ha REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée!")

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Page d'accueil avec vue d'ensemble des zones"""
    return render_template('home.html')

@app.route('/zone/<province>/<code_zone>')
def zone_detail(province, code_zone):
    """Page détail zone"""
    return render_template('zone.html')

@app.route('/api/provinces', methods=['GET'])
def get_provinces():
    return jsonify(list(ZONES_CONFIG.keys()))

@app.route('/api/zones/all', methods=['GET'])
def get_all_zones():
    """Récupérer toutes les zones configurées avec leurs stats"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT z.province, z.code_zone, z.nom_zone, z.enqueteur, 
               z.date_debut_enquete, z.surface_totale_ha, z.cloturee, z.date_cloture,
               e.numero_jour, e.nb_parcelles, e.surface_enquetee_ha, 
               e.surface_restante_ha, e.pourcentage_avancement
        FROM zones z
        LEFT JOIN enquete_actuelle e ON z.province = e.province AND z.code_zone = e.code_zone
        ORDER BY z.province, z.code_zone
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    # Organiser par province
    zones_by_province = {}
    for row in rows:
        province = row[0]
        if province not in zones_by_province:
            zones_by_province[province] = []
        
        zone_data = {
            'province': row[0],
            'code_zone': row[1],
            'nom_zone': row[2],
            'enqueteur': row[3] or '-',
            'date_debut_enquete': row[4] or '-',
            'surface_totale_ha': round(row[5], 2) if row[5] else 0,
            'cloturee': bool(row[6]),
            'date_cloture': row[7],
            'numero_jour': row[8] or 0,
            'nb_parcelles': row[9] or 0,
            'surface_enquetee_ha': round(row[10], 2) if row[10] else 0,
            'surface_restante_ha': round(row[11], 2) if row[11] else 0,
            'pourcentage_avancement': round(row[12], 1) if row[12] else 0,
            'statut': 'cloturee' if row[6] else 'en_cours'
        }
        zones_by_province[province].append(zone_data)
    
    return jsonify(zones_by_province)

@app.route('/api/zones/<province>', methods=['GET'])
def get_zones(province):
    zones = ZONES_CONFIG.get(province, [])
    return jsonify(zones)

@app.route('/api/zone/info', methods=['POST'])
def get_zone_info():
    data = request.json
    province = data.get('province')
    code_zone = data.get('code_zone')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT nom_zone, enqueteur, surface_totale_ha, date_debut_enquete, cloturee, date_cloture
        FROM zones
        WHERE province = ? AND code_zone = ?
    ''', (province, code_zone))
    
    zone = cursor.fetchone()
    
    if not zone:
        conn.close()
        return jsonify({'configured': False})
    
    cursor.execute('''
        SELECT numero_jour, date_enquete, nb_parcelles,
               surface_enquetee_ha, surface_restante_ha, pourcentage_avancement
        FROM enquete_actuelle
        WHERE province = ? AND code_zone = ?
    ''', (province, code_zone))
    
    stats = cursor.fetchone()
    
    # Récupérer historique
    cursor.execute('''
        SELECT date_maj, numero_jour, nb_parcelles, surface_enquetee_ha,
               parcelles_ajoutees, surface_ajoutee_ha
        FROM historique_uploads
        WHERE province = ? AND code_zone = ?
        ORDER BY date_maj ASC
    ''', (province, code_zone))
    
    historique_rows = cursor.fetchall()
    historique = []
    for row in historique_rows:
        historique.append({
            'date_maj': row[0],
            'numero_jour': row[1],
            'nb_parcelles': row[2],
            'surface_enquetee_ha': round(row[3], 2) if row[3] else 0,
            'parcelles_ajoutees': row[4],
            'surface_ajoutee_ha': round(row[5], 2) if row[5] else 0
        })
    
    conn.close()
    
    result = {
        'configured': True,
        'province': province,
        'code_zone': code_zone,
        'nom_zone': zone[0],
        'enqueteur': zone[1],
        'surface_totale_ha': round(zone[2], 2) if zone[2] else 0,
        'date_debut_enquete': zone[3],
        'cloturee': bool(zone[4]),
        'date_cloture': zone[5],
        'historique': historique
    }
    
    if stats:
        result.update({
            'numero_jour': stats[0],
            'date_enquete': stats[1],
            'nb_parcelles': stats[2],
            'surface_enquetee_ha': round(stats[3], 2) if stats[3] else 0,
            'surface_restante_ha': round(stats[4], 2) if stats[4] else 0,
            'pourcentage_avancement': round(stats[5], 1) if stats[5] else 0
        })
        
        # Calculer avancement journalier (dernier upload)
        if len(historique) > 0:
            dernier = historique[-1]
            result['parcelles_ajoutees_aujourd_hui'] = dernier['parcelles_ajoutees']
            result['surface_ajoutee_aujourd_hui'] = dernier['surface_ajoutee_ha']
        else:
            result['parcelles_ajoutees_aujourd_hui'] = 0
            result['surface_ajoutee_aujourd_hui'] = 0
    else:
        result.update({
            'numero_jour': 0,
            'date_enquete': None,
            'nb_parcelles': 0,
            'surface_enquetee_ha': 0,
            'surface_restante_ha': zone[2],
            'pourcentage_avancement': 0,
            'parcelles_ajoutees_aujourd_hui': 0,
            'surface_ajoutee_aujourd_hui': 0
        })
    
    return jsonify(result)

@app.route('/api/zone/cloturer', methods=['POST'])
def cloturer_zone():
    """Clôturer une zone"""
    try:
        data = request.json
        province = data.get('province')
        code_zone = data.get('code_zone')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE zones
            SET cloturee = 1, date_cloture = ?
            WHERE province = ? AND code_zone = ?
        ''', (datetime.now().strftime('%Y-%m-%d'), province, code_zone))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Zone clôturée avec succès'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zone/decloturer', methods=['POST'])
def decloturer_zone():
    """Dé-clôturer une zone (annuler la clôture)"""
    try:
        data = request.json
        province = data.get('province')
        code_zone = data.get('code_zone')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE zones
            SET cloturee = 0, date_cloture = NULL
            WHERE province = ? AND code_zone = ?
        ''', (province, code_zone))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Zone dé-clôturée avec succès'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload/limite', methods=['POST'])
def upload_limite():
    try:
        file = request.files['file']
        province = request.form['province']
        code_zone = request.form['code_zone']
        enqueteur = request.form['enqueteur']
        date_debut_enquete = request.form['date_debut_enquete']
        
        temp_path = os.path.join(UPLOAD_FOLDER, f'limite_{province}_{code_zone}.gpkg')
        file.save(temp_path)
        
        gdf = gpd.read_file(temp_path)
        
        if gdf.crs is None:
            gdf.set_crs('EPSG:26191', inplace=True)
        elif gdf.crs.to_string() != 'EPSG:26191':
            gdf = gdf.to_crs('EPSG:26191')
        
        geom_union = unary_union(gdf.geometry)
        surface_totale_ha = geom_union.area / 10000
        geom_json = json.dumps(mapping(geom_union))
        
        zone_info = next((z for z in ZONES_CONFIG.get(province, []) if z['code'] == code_zone), None)
        nom_zone = zone_info['nom'] if zone_info else code_zone
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO zones 
            (province, code_zone, nom_zone, enqueteur, date_debut_enquete, surface_totale_ha, geom_limite, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (province, code_zone, nom_zone, enqueteur, date_debut_enquete, round(surface_totale_ha, 2), geom_json))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'surface_totale_ha': round(surface_totale_ha, 2),
            'message': f'Zone configurée: {surface_totale_ha:.2f} ha'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload/enquete', methods=['POST'])
def upload_enquete():
    try:
        file = request.files['file']
        province = request.form['province']
        code_zone = request.form['code_zone']
        numero_jour = int(request.form['numero_jour'])
        
        # Date = date système automatique
        date_enquete = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT surface_totale_ha, geom_limite
            FROM zones
            WHERE province = ? AND code_zone = ?
        ''', (province, code_zone))
        
        zone = cursor.fetchone()
        
        if not zone:
            conn.close()
            return jsonify({
                'success': False, 
                'error': 'Zone non configurée, veuillez d\'abord uploader la limite'
            }), 400
        
        surface_totale_ha = zone[0]
        geom_limite_json = zone[1]
        
        # Récupérer stats précédentes pour calcul différentiel
        cursor.execute('''
            SELECT nb_parcelles, surface_enquetee_ha
            FROM enquete_actuelle
            WHERE province = ? AND code_zone = ?
        ''', (province, code_zone))
        
        stats_precedentes = cursor.fetchone()
        if stats_precedentes:
            nb_parcelles_precedent = stats_precedentes[0]
            surface_precedente_ha = stats_precedentes[1]
        else:
            nb_parcelles_precedent = 0
            surface_precedente_ha = 0
        
        geom_limite = shape(json.loads(geom_limite_json))
        limite_gdf = gpd.GeoDataFrame([1], geometry=[geom_limite], crs='EPSG:26191')
        
        gpkg_path = os.path.join(UPLOAD_FOLDER, f'enquete_{province}_{code_zone}.gpkg')
        file.save(gpkg_path)
        
        parcelles_gdf = gpd.read_file(gpkg_path, layer='PARCELLES')
        
        if parcelles_gdf.crs is None:
            parcelles_gdf.set_crs('EPSG:26191', inplace=True)
        elif parcelles_gdf.crs.to_string() != 'EPSG:26191':
            parcelles_gdf = parcelles_gdf.to_crs('EPSG:26191')
        
        parcelles_clipped = gpd.overlay(parcelles_gdf, limite_gdf, how='intersection')
        
        nb_parcelles = len(parcelles_clipped)
        surface_enquetee_ha = parcelles_clipped.geometry.area.sum() / 10000
        surface_restante_ha = surface_totale_ha - surface_enquetee_ha
        pourcentage_avancement = min((surface_enquetee_ha / surface_totale_ha) * 100, 100)
        
        # Calculer différence avec précédent
        parcelles_ajoutees = nb_parcelles - nb_parcelles_precedent
        surface_ajoutee_ha = surface_enquetee_ha - surface_precedente_ha
        
        # Mettre à jour stats actuelles
        cursor.execute('''
            INSERT OR REPLACE INTO enquete_actuelle
            (province, code_zone, numero_jour, date_enquete, nb_parcelles,
             surface_enquetee_ha, surface_restante_ha, pourcentage_avancement,
             geopackage_path, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (province, code_zone, numero_jour, date_enquete, nb_parcelles,
              round(surface_enquetee_ha, 2), round(surface_restante_ha, 2),
              round(pourcentage_avancement, 1), gpkg_path))
        
        # Ajouter dans historique
        cursor.execute('''
            INSERT INTO historique_uploads
            (province, code_zone, numero_jour, date_maj, nb_parcelles,
             surface_enquetee_ha, parcelles_ajoutees, surface_ajoutee_ha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (province, code_zone, numero_jour, date_enquete, nb_parcelles,
              round(surface_enquetee_ha, 2), parcelles_ajoutees, round(surface_ajoutee_ha, 2)))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'nb_parcelles': nb_parcelles,
            'surface_enquetee_ha': round(surface_enquetee_ha, 2),
            'surface_restante_ha': round(surface_restante_ha, 2),
            'pourcentage_avancement': round(pourcentage_avancement, 1),
            'parcelles_ajoutees': parcelles_ajoutees,
            'surface_ajoutee_ha': round(surface_ajoutee_ha, 2),
            'message': f'{nb_parcelles} parcelles analysées (+{parcelles_ajoutees} aujourd\'hui)'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/ph1/<province>/<code_zone>', methods=['GET'])
def export_ph1(province, code_zone):
    """Export PH1 Excel - UNIVERSEL (gère TOUS les formats)"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT geopackage_path
            FROM enquete_actuelle
            WHERE province = ? AND code_zone = ?
        ''', (province, code_zone))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return jsonify({'error': 'Aucune donnée d\'enquête disponible'}), 404
        
        gpkg_path = result[0]
        
        if not os.path.exists(gpkg_path):
            return jsonify({'error': 'Fichier geopackage introuvable'}), 404
        
        # Lire PROPRIETAIRES
        proprietaires_gdf = gpd.read_file(gpkg_path, layer='PROPRIETAIRES')
        
        # Construire dictionnaire propriétaires (UNIVERSEL)
        proprietaires_dict = {}
        for idx, row in proprietaires_gdf.iterrows():
            id_prop_raw = row.get('id_proprietaire')
            if pd.notna(id_prop_raw):
                id_prop = str(int(id_prop_raw))
            else:
                continue
            
            proprietaires_dict[id_prop] = {
                'nom_arabe': get_field_value(row, FIELD_MAPPINGS['nom_arabe']),
                'prenom_arabe': get_field_value(row, FIELD_MAPPINGS['prenom_arabe']),
                'autre_nom_arabe': get_field_value(row, FIELD_MAPPINGS['autre_nom_arabe']),
                'nom_francais': get_field_value(row, FIELD_MAPPINGS['nom_francais']),
                'prenom_francais': get_field_value(row, FIELD_MAPPINGS['prenom_francais']),
                'autre_nom_francais': get_field_value(row, FIELD_MAPPINGS['autre_nom_francais']),
                'date_naissance': str(get_field_value(row, FIELD_MAPPINGS['date_naissance'])) if pd.notna(get_field_value(row, FIELD_MAPPINGS['date_naissance'])) else '',
                'CINE': get_field_value(row, FIELD_MAPPINGS['CINE']),
                'situation_famille': get_field_value(row, FIELD_MAPPINGS['situation_famille']),
                'nom_conjoint': get_field_value(row, FIELD_MAPPINGS['nom_conjoint']),
                'num_tel': get_field_value(row, FIELD_MAPPINGS['num_tel']),
                'adresse_proprietaire': get_field_value(row, FIELD_MAPPINGS['adresse_proprietaire'])
            }
        
        # Lire PARCELLES
        parcelles_gdf = gpd.read_file(gpkg_path, layer='PARCELLES')
        
        if parcelles_gdf.crs is None:
            parcelles_gdf.set_crs('EPSG:26191', inplace=True)
        elif parcelles_gdf.crs.to_string() != 'EPSG:26191':
            parcelles_gdf = parcelles_gdf.to_crs('EPSG:26191')
        
        # Construire données PH1
        ph1_rows = []
        
        for idx, parcel in parcelles_gdf.iterrows():
            # Récupérer propriétaire
            id_prop_raw = parcel.get('id_proprietaire')
            if pd.notna(id_prop_raw):
                id_prop = str(int(id_prop_raw))
            else:
                id_prop = ''
            owner = proprietaires_dict.get(id_prop, {})
            
            # Calculer Ha/A/Ca depuis GÉOMÉTRIE
            superficie_m2 = parcel.geometry.area
            ha = int(superficie_m2 // 10000)
            reste = superficie_m2 % 10000
            a = int(reste // 100)
            ca = int(reste % 100)
            
            # Calculer centroïde
            centroid = parcel.geometry.centroid
            centroid_x = round(centroid.x, 2)
            centroid_y = round(centroid.y, 2)
            
            # Construire ligne PH1 (UNIVERSEL - gère tous formats)
            row = {
                'fid': idx + 1,
                'SousZone': get_field_value(parcel, FIELD_MAPPINGS['sous_zone']),
                'Ordre': get_field_value(parcel, FIELD_MAPPINGS['ordre']),
                'Plle': get_field_value(parcel, FIELD_MAPPINGS['plle']),
                'N° TF/Req': get_field_value(parcel, FIELD_MAPPINGS['num_tf_req']),
                'Indice': get_field_value(parcel, FIELD_MAPPINGS['indice']),
                'Nom Arabe ': owner.get('nom_arabe', ''),
                'Prenom Arabe ': owner.get('prenom_arabe', ''),
                'Autre Nom Arabe': owner.get('autre_nom_arabe', ''),
                'Nom français ': owner.get('nom_francais', ''),
                'Prenom français': owner.get('prenom_francais', ''),
                'Autre Nom français': owner.get('autre_nom_francais', ''),
                'Date Naissance': owner.get('date_naissance', ''),
                'C.I.N.E': owner.get('CINE', ''),
                'Situation Famille': owner.get('situation_famille', ''),
                'Nom Conjoint': owner.get('nom_conjoint', ''),
                'N° de Tel': owner.get('num_tel', ''),
                'Quote Dénominateur': get_field_value(parcel, FIELD_MAPPINGS['quote_denominateur']),
                'Adresse Français': get_field_value(parcel, FIELD_MAPPINGS['adresse_francais']),
                'Adresse Arabe': get_field_value(parcel, FIELD_MAPPINGS['adresse_arabe']),
                'Ha': ha,
                'A': a,
                'Ca': ca,
                'Nom Parcelle(F)': get_field_value(parcel, FIELD_MAPPINGS['nom_parcelle_f']),
                'Nature Principale(A)': get_field_value(parcel, FIELD_MAPPINGS['nature_principale_a']),
                'Consist Matrielle': get_field_value(parcel, FIELD_MAPPINGS['consist_materielle']),
                'Type de Spéculation': get_field_value(parcel, FIELD_MAPPINGS['type_speculation']),
                'Type de sol': get_field_value(parcel, FIELD_MAPPINGS['type_sol']),
                'Droits Réels': get_field_value(parcel, FIELD_MAPPINGS['droits_reels']),
                'Oppositions': get_field_value(parcel, FIELD_MAPPINGS['oppositions']),
                'Charges et Servitudes': get_field_value(parcel, FIELD_MAPPINGS['charges_servitudes']),
                'Mappe': get_field_value(parcel, FIELD_MAPPINGS['mappe']),
                'Coordonnées du centroide (X)': centroid_x,
                'Coordonnées du centroide (Y)': centroid_y,
                'Observations': get_field_value(parcel, FIELD_MAPPINGS['observations'])
            }
            
            ph1_rows.append(row)
        
        df = pd.DataFrame(ph1_rows)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='PH1', index=False)
        
        output.seek(0)
        
        filename = f'PH1_{province}_{code_zone}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_database()
    print("\n" + "="*60)
    print("🚀 Application UNIVERSELLE démarrée!")
    print("✅ Gère TOUS les formats de geopackage (ancien + nouveau)")
    print("📍 http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)