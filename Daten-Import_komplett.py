# -*- coding: utf-8 -*-
"""
Created on Fri Feb 19 14:46:39 2021

@author: Robert
"""


import os, glob, shutil, requests, json, sys, io, calendar, locale
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# deutsche Datumsbezeichnungen verwenden
locale.setlocale(locale.LC_TIME, "de_DE") 

#Server-Key für Trello angeben (MUSS VOM KUNDEN ANGEPASST WERDEN)
key = "cf96243c3494a8473e5caccd2d0f906c"

#Token für Trello angeben (MUSS VOM KUNDEN REGELMÄSSIG AKTUALISIERT WERDEN)
token = "11cb90ee1fbb4081bb760fdba3f70fbb6112177df1921e8d2215d0e1644a7228"

#Board-ID des Produktionsboard eingeben, in dem die Produktionskarten angelegt werden sollen (MUSS VOM KUNDEN ANGEPASST WERDEN)
produktion_board_id = 'bE8Wi83G'

#Board-ID des Logistikboard eingeben, in dem die Logistikkarten angelegt werden sollen (MUSS VOM KUNDEN ANGEPASST WERDEN)
logistik_board_id = '9WeW7Q9E'

#Bezeichnungen der Produktions-Listen der jeweiligen Arbeitsplätze, in die die Karten hereingeladen werden sollen
#(MÜSSEN VOM KUNDEN ANGEPASST WERDEN)
P_list_name_StortiX = 'StortiX'
P_list_name_21X = '21X'
#weitere Listen-Bezeichnungen

#Bezeichnungen der Logistik-Listen der jeweiligen Arbeitsplätze, in die die Karten hereingeladen werden sollen
#(MÜSSEN VOM KUNDEN ANGEPASST WERDEN)
L_list_name_StortiX = 'StortiX'
L_list_name_21X = '21X'
#weitere Listen-Bezeichnungen

#Bezeichnung der Exportdateien, nach der in den Ordnern gesucht werden soll (MUSS VOM KUNDEN ANGEPASST WERDEN)
search_for = "*export*"

#Bezeichnungen der Spalten, nach denen in Exportdateien zur Erstellung von Produktionskarten gesucht werden soll 
search_list_P = ['Pos_Bezugsquelle', 
                 'F2:Kunde:Name', 
                 'Pos_Bezeichnung', 
                 'Pos_Menge', 
                 'Pos_Artikel_Deutsch_SachmerkmalFeld1',
                 'Pos_Wunschtermin']

#Bezeichnungen, nach denen in Exportdateien zur Erstellung von Logistikkarten gesucht werden soll 
search_list_L = ['F2:Auftragsnummer', 
                 'F2:Kunde:Name', 
                 'F2:Versandanschrift4', 
                 'F2:Versandanschrift3', 
                 'F2:Versandart',
                 'Pos_Wunschtermin',
                 'Pos_Bezeichnung',
                 'Pos_Bezugsquelle',
                 'Pos_Artikel_Deutsch_Bezeichnung']

#Pfad, wo sich die Exportdateien befinden (MUSS VOM KUNDEN ANGEPASST WERDEN)
root = 'C:/path/to/your/project/Produktionsaufträge'
os.chdir(root)

###########################
   
#Anlegen von neuen Ordnern
def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Error: Creating directory. ' + directory)
    
def evaluate_field(record, field_spec):
        """
        Evaluate a field of a record using the type of the field_spec as a guide.
        """
        if type(field_spec) is int:
            return str(record[field_spec])
        elif type(field_spec) is str:
            return str(getattr(record, field_spec))
        else:
            return str(field_spec(record))
        
#Umwandeln von Daten ins Markdown-Format
def table(file, records, fields, headings, alignment = None):
    """
    Generate a Doxygen-flavor Markdown table from records.

    file -- Any object with a 'write' method that takes a single string
        parameter.
    records -- Iterable.  Rows will be generated from this.
    fields -- List of fields for each row.  Each entry may be an integer,
        string or a function.  If the entry is an integer, it is assumed to be
        an index of each record.  If the entry is a string, it is assumed to be
        a field of each record.  If the entry is a function, it is called with
        the record and its return value is taken as the value of the field.
    headings -- List of column headings.
    alignment - List of pairs alignment characters.  The first of the pair
        specifies the alignment of the header, (Doxygen won't respect this, but
        it might look good, the second specifies the alignment of the cells in
        the column.

        Possible alignment characters are:
            '<' = Left align (default for cells)
            '>' = Right align
            '^' = Center (default for column headings)
    """

    # Translation dictionaries for table alignment
    left_rule = {'<': ':', '^': ':', '>': '-'}
    right_rule = {'<': '-', '^': ':', '>': ':'}

    num_columns = len(fields)
    assert len(headings) == num_columns

    # Compute the table cell data
    columns = [[] for i in range(num_columns)]
    for record in records:
        for i, field in enumerate(fields):
            columns[i].append(evaluate_field(record, field))

    # Fill out any missing alignment characters.
    extended_align = alignment if alignment != None else []
    if len(extended_align) > num_columns:
        extended_align = extended_align[0:num_columns]
    elif len(extended_align) < num_columns:
        extended_align += [('^', '<')
                           for i in range[num_columns-len(extended_align)]]

    heading_align, cell_align = [x for x in zip(*extended_align)]

    field_widths = [len(max(column, key=len)) if len(column) > 0 else 0
                    for column in columns]
    heading_widths = [max(len(head), 2) for head in headings]
    column_widths = [max(x) for x in zip(field_widths, heading_widths)]

    _ = ' | '.join(['{:' + a + str(w) + '}'
                    for a, w in zip(heading_align, column_widths)])
    heading_template = '| ' + _ + ' |'
    _ = ' | '.join(['{:' + a + str(w) + '}'
                    for a, w in zip(cell_align, column_widths)])
    row_template = '| ' + _ + ' |'

    _ = ' | '.join([left_rule[a] + '-'*(w-2) + right_rule[a]
                    for a, w in zip(cell_align, column_widths)])
    ruling = '| ' + _ + ' |'

    file.write(heading_template.format(*headings).rstrip() + '\n')
    file.write(ruling.rstrip() + '\n')
    for row in zip(*columns):
        file.write(row_template.format(*row).rstrip() + '\n')
            
#Zwei Ordner für erledigte und noch nicht erledigte Dateien anlegen
createFolder(root + './Erledigt/')
createFolder(root +'./Noch zu erledigen/')

#Directory erstellen, in dem sich noch zu erledigende Dateien befinden sollen
dst_dirname = root + '/Noch zu erledigen/'

#Klasse mit Funktionen zum Hochladen von Daten in Trello
class Trello:

    #Erstellen von neuen Karten in Trello-Liste   
    def create_card(self, card_name, list_id):
        
        querystring = {
            "name": card_name, 
            "idList": list_id, 
            "key": key, 
            "token": token
        }

        response = requests.request(
            "POST", 
            url = f"https://api.trello.com/1/cards", 
            params=querystring
        )

        card_id = response.json()["id"]
        return card_id

    #Bestimmen der List-ID eines Boards anhand der Listen-Bezeichnung
    def get_list_id(self, board_id, list_name):

        query = {
           'key': key,
           'token': token
        }

        response = requests.request(
           "GET",
           url = "https://api.trello.com/1/boards/" + board_id + "/lists",
           params=query
        )

        list_id_index = [*range(len(json.loads(response.text)))]

        keys = []
        for i in list_id_index:
            keys.append(json.loads(response.text)[i]['name'])

        values = []
        for i in list_id_index:
            values.append(json.loads(response.text)[i]['id'])

        list_id_dict = {}
        for i in list_id_index:
            list_id_dict[keys[i]] = values[i]

        return list_id_dict[list_name]

    #Bestimmen der Ankerpunkte in einer Exportdatei
    def get_anker_punkte(self, export_data):
        ankerpunkte = np.where(pd.notna(export_data.drop([0,1,2])[1]))
        ankerpunkte = np.asarray(ankerpunkte).tolist()[0][0:]
        ankerpunkte.remove(0)
        return ankerpunkte

    #Abprüfen, ob zu einem Suchbegriff in der Exportdatei Daten vorhanden sind und wenn nein, 
    #die Datei in den Ordner 'Noch zu erledigen' kopieren
    def move_excel(self, search, export_data, position):
        row = export_data.loc[export_data.isin([search]).any(axis=1)].index[0]
        col = export_data.T.loc[export_data.T.isin([search]).any(axis=1)].index[0] 
        if pd.isnull(export_data.iloc[row+position, col]) is True:
            dst_filename = os.path.join(dst_dirname, os.path.basename(source_file))
            shutil.copy(source_file, dst_filename)

    #Auflisten aller Dateien im aktuellen Verzeichnis, die einen Suchbegriff im Dateinamen enthalten
    def get_files(self, search_term):
        liste_file = []
        for file in glob.glob(search_term):
            liste_file.append(file)
        return liste_file  
    
    #Auslesen der Infos aus einer Spalte anhand eines Suchbegriffs
    def get_info(self, export, search, liste, position):
        row = export.loc[export.isin([search]).any(axis=1)].index[0]
        col = export.T.loc[export.T.isin([search]).any(axis=1)].index[0]
        liste.append(str(export.iloc[row+position, col]))
        return liste      

    #Einlesen der Daten, die in den Kopf der Produktionskarte sollen
    def trello_head_P(self, export, ankerpunkte, search):
        
        liste_head = []

        #(8) Maschine hinzufügen
        liste_maschine = []
        for i in ankerpunkte:
            search = 'Pos_Artikel_Deutsch_SachmerkmalFeld1' 
            row = export.loc[export.isin([search]).any(axis=1)].index[0]
            col = export.T.loc[export.T.isin([search]).any(axis=1)].index[0]
            strg = export.iloc[row+i,col].split('*')[5]
            liste_maschine.append(strg)

        liste_head.append(liste_maschine)

        #(2) Kunde hinzufügen
        liste_kunde = []
        for i in ankerpunkte:
            new_object.get_info(export, 'F2:Kunde:Name', liste_kunde, 1)

        liste_head.append(liste_kunde)

        liste_head = np.array(liste_head).T.tolist()

        return liste_head   
    
    #Einlesen der Daten, die in den Body der Produktionskarte sollen
    def trello_body_P(self, export, ankerpunkte, search):
        
        liste_body = []
        
        #(6) Fälligkeitsdatum hinzufügen
        liste_fälligkeitsdatum = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Wunschtermin', liste_fälligkeitsdatum, i)

        liste_body.append(liste_fälligkeitsdatum)

        liste_body = np.array(liste_body).T.tolist()

        return liste_body
    
    #Einlesen der Daten, die in die Beschreibung der Produktionskarte sollen
    def trello_footer_P(self, export, ankerpunkte, search):
        
        liste_footer = []

        #(0) Position hinzufügen
        liste_position = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Position', liste_position, i)

        liste_footer.append(liste_position)

        #(1) Auftragsnummer Produktion hinzufügen
        liste_auftragsnummerproduktion = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Bezugsquelle', liste_auftragsnummerproduktion, i)

        liste_footer.append(liste_auftragsnummerproduktion)

        #(3) Artikelnummer hinzufügen
        liste_artikelnummer = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Bezeichnung', liste_artikelnummer, i)

        liste_footer.append(liste_artikelnummer)

        #(5) Beschreibung hinzufügen
        liste_beschreibung = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Bezeichnung', liste_beschreibung, i+1)

        liste_footer.append(liste_beschreibung)

        #(7) Workload hinzufügen
        liste_workload = []
        for i in ankerpunkte: 
            search = 'Pos_Artikel_Deutsch_SachmerkmalFeld1' 
            row = export.loc[export.isin([search]).any(axis=1)].index[0]
            col = export.T.loc[export.T.isin([search]).any(axis=1)].index[0]
            #Workload berechnen
            str1 = export.iloc[row+i,col].split('*')[4]
            int1 = (int(str1)*3 +45)/60
            round_up = lambda num: int(num + 1) if int(num) != num else int(num)
            int1 = round_up(int1)
            str2 = '(' + str(int1) + ')'
            liste_workload.append(str2)

        liste_footer.append(liste_workload)

        #(10) Verladetermin hinzufügen
        liste_verladetermin = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Wunschtermin', liste_verladetermin, i)

        liste_footer.append(liste_verladetermin)

        liste_footer = np.array(liste_footer).T.tolist()

        return liste_footer
        
    #Einlesen der Daten, die in den Kopf der Logistikkarte sollen
    def trello_head_L(self, export, ankerpunkte, search):
        
        liste_head = []
        
        #(8) Maschine hinzufügen
        liste_maschine = []
        for i in ankerpunkte:
            search = 'Pos_Artikel_Deutsch_SachmerkmalFeld1' 
            row = export.loc[export.isin([search]).any(axis=1)].index[0]
            col = export.T.loc[export.T.isin([search]).any(axis=1)].index[0]
            strg = export.iloc[row+i,col].split('*')[5]
            liste_maschine.append(strg)

        liste_head.append(liste_maschine)
        
        #(1) Auftragsnummer hinzufügen
        liste_auftragsnummer = []
        for i in ankerpunkte:
            new_object.get_info(export, 'F2:Auftragsnummer', liste_auftragsnummer, 1)

        liste_head.append(liste_auftragsnummer)
            
        #(2) Kunde hinzufügen
        liste_kunde = []
        for i in ankerpunkte:
            new_object.get_info(export, 'F2:Kunde:Name', liste_kunde, 1)

        liste_head.append(liste_kunde)

        #(3) Versandadresse hinzufügen
        liste_versandadresse = []
        for i in ankerpunkte:
            new_object.get_info(export, 'F2:Versandanschrift4', liste_versandadresse, 1)

        liste_head.append(liste_versandadresse)

        #(4) Erweiterung Versandadresse hinzufügen
        liste_erweiterung_versandadresse = []
        for i in ankerpunkte:
            new_object.get_info(export, 'F2:Versandanschrift3', liste_erweiterung_versandadresse, 1)

        liste_head.append(liste_erweiterung_versandadresse)

        #(5) Versandart hinzufügen
        liste_versandart = []
        for i in ankerpunkte:
            new_object.get_info(export, 'F2:Versandart', liste_versandart, 1)

        liste_head.append(liste_versandart)

        liste_head = np.array(liste_head).T.tolist()

        return liste_head      
    
    #Einlesen der Daten, die in den Body der Produktionskarte sollen
    def trello_body_L(self, export, ankerpunkte, search):
        
        liste_body = []
        
        #(6) Fälligkeitsdatum hinzufügen
        liste_fälligkeitsdatum = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Wunschtermin', liste_fälligkeitsdatum, i)

        liste_body.append(liste_fälligkeitsdatum)

        liste_body = np.array(liste_body).T.tolist()

        return liste_body 
    
    #Einlesen der Daten, die in die Beschreibung der Produktionskarte sollen
    def trello_footer_L(self, export, ankerpunkte, search):
        
        liste_footer = []
        
        #(0) Position hinzufügen
        liste_position = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Position', liste_position, i)
            
        liste_footer.append(liste_position)
        
        #(7) Artikelnummer hinzufügen
        liste_artikelnummer = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Bezeichnung', liste_artikelnummer, i)     

        liste_footer.append(liste_artikelnummer)
      
        #(8) Bezugsquelle hinzufügen
        liste_bezugsquelle = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Bezugsquelle', liste_bezugsquelle, i)     

        liste_footer.append(liste_bezugsquelle)

        #(9) Artikelbeschreibung hinzufügen
        liste_artikelbeschreibung = []
        for i in ankerpunkte:
            new_object.get_info(export, 'Pos_Artikel_Deutsch_Bezeichnung', liste_artikelbeschreibung, i) 

        liste_footer.append(liste_artikelbeschreibung)
    
        #(10) Verladetag hinzufügen
        liste_verladetag = []
        for i in ankerpunkte:
            search = 'Pos_Wunschtermin' 
            row = export.loc[export.isin([search]).any(axis=1)].index[0]
            col = export.T.loc[export.T.isin([search]).any(axis=1)].index[0]
            ts = str(export.iloc[row+i,col])
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            verladetag = calendar.day_name[dt.weekday()]
            liste_verladetag.append(verladetag)

        liste_footer.append(liste_verladetag)

        liste_footer = np.array(liste_footer).T.tolist()

        return liste_footer
    
    #Hinzufügen von Daten in vorhandene Produktionskarte
    def add_to_production_card(self, export, ankerpunkte, search, P_list_id, head_P, dt, trello_card_id):
        
        #Produktionskarte ohne Beschreibung erzeugen
        headers = {
           "Accept": "application/json"
        }

        query = {
           'key': key,                                   #API-Schlüssel von Trello
           'token': token,                               #API-Token von Trello
           'idList': P_list_id,                          #ID der Produktionsliste, in der die Karte eingefügt werden soll
           'name': head_P,                               #neuer Name der Karte 
           'desc': '',                                   #neue Beschreibung der Karte
           'due':  dt - timedelta(hours=6, minutes=0),   #Frist, bis wann Kartenauftrag erledigt sein muss
           'pos': 'bottom'                               #Position, wo neue Karte in Liste erzeugt werden soll
        }

        response = requests.request(
           "PUT",
           url = "https://api.trello.com/1/cards/" + trello_card_id,
           headers=headers,
           params=query
        )

        card_id = response.json()["id"]

        return card_id 
    
    #Hinzufügen von Daten in vorhandene Logistikkarte
    def add_to_logistic_card(self, export, ankerpunkte, search, L_list_id, head_L, dt, trello_card_id):
        
        #Logistikkarte ohne Beschreibung erzeugen
        headers = {
           "Accept": "application/json"
        }

        query = {
           'key': key,                                   #API-Schlüssel von Trello
           'token': token,                               #API-Token von Trello
           'idList': L_list_id,                          #ID der Produktionsliste, in der die Karte eingefügt werden soll
           'name': head_L,                              #neuer Name der Karte 
           'desc': '',                                  #neue Beschreibung der Karte
           'due':  dt - timedelta(hours=6, minutes=0),  #Frist, bis wann Kartenauftrag erledigt sein muss
           'pos': 'bottom'                              #Position, wo neue Karte in Liste erzeugt werden soll
        }

        response = requests.request(
           "PUT",
           url = "https://api.trello.com/1/cards/" + trello_card_id,
           headers=headers,
           params=query
        )

        card_id = response.json()["id"]

        return card_id
    
    #Auffüllen der Tabelle in der Beschreibung der Produktionskarte mit Daten zu allen Positionen,
    #die zum selben Arbeitsplatz gehören
    def add_description_P(self, maschine, liste_maschine, output, P_list_id, head_P, dt, trello_card_id):

        #Indizes der Maschinen bestimmen, die zum selben Arbeitsplatz gehören
        def condition(x): return x == maschine

        description_index = [idx for idx, element in enumerate(liste_maschine) if condition(element)]

        liste_output = []
        liste_output.append(output.split('\n')[0])
        liste_output.append(output.split('\n')[1])
        for i in description_index:
            liste_output.append(output.split('\n')[i+2])

        #Beschreibung um Tabelle ergänzen
        headers = {
           "Accept": "application/json"
        }

        query = {
           'key': key,                                   
           'token': token,                               
           'idList': P_list_id,                                   #ID der Produktionsliste, in die die Karte eingefügt werden soll
           'name': head_P,                                        #neuer Name der Karte 
           'desc': "```\n" + '\n'.join(liste_output) + "\n```",   #neue Beschreibung der Karte
           'due':  dt - timedelta(hours=6, minutes=0),            #Frist, bis wann Kartenauftrag erledigt sein muss
           'pos': 'bottom'                                        #Position, wo neue Karte in Liste erzeugt werden soll
        }

        response = requests.request(
           "PUT",
           url = "https://api.trello.com/1/cards/" + trello_card_id,
           headers=headers,
           params=query
        )

        card_id = response.json()["id"]

        return card_id
    
    #Auffüllen der Tabelle in der Beschreibung der Logistikkarte mit Daten zu allen Positionen,
    #die zum selben Arbeitsplatz gehören
    def add_description_L(self, maschine, liste_maschine, output, L_list_id, head_L, dt, trello_card_id):

        #Indizes der Maschinen bestimmen
        def condition(x): return x == maschine

        description_index = [idx for idx, element in enumerate(liste_maschine) if condition(element)]

        liste_output = []
        liste_output.append(output.split('\n')[0])
        liste_output.append(output.split('\n')[1])
        for i in description_index:
            liste_output.append(output.split('\n')[i+2])

        #Beschreibung ergänzen
        headers = {
           "Accept": "application/json"
        }

        query = {
           'key': key,                                   
           'token': token,                               
           'idList': L_list_id,                                  #ID der Logistikliste, in die die Karte eingefügt werden soll
           'name': head_L,                                       #neuer Name der Karte 
           'desc': "```\n" + '\n'.join(liste_output) + "\n```",  #neue Beschreibung der Karte
           'due':  dt - timedelta(hours=6, minutes=0),           #Frist, bis wann Kartenauftrag erledigt sein muss
           'pos': 'bottom'                                       #Position, wo neue Karte in Liste erzeugt werden soll
        }

        response = requests.request(
           "PUT",
           url = "https://api.trello.com/1/cards/" + trello_card_id,
           headers=headers,
           params=query
        )

        card_id = response.json()["id"]

        return card_id
    
    #Hinzufügen von Anhängen, die zum selben Arbeitsplatz gehören, an Produktionskarten
    def add_attachments(self, maschine, liste_maschine, files, trello_card_id):

        #Indizes der Maschinen bestimmen
        def condition(x): return x == maschine

        attachment_index = [idx for idx, element in enumerate(liste_maschine) if condition(element)]

        for i in attachment_index:

            #Stücklisten an Karten anhängen
            attachment = files[i]           #Datei, die angehängt werden soll

            name = files[i]                 #Bezeichnung des Anhangs in der Karte

            #MIME-Type der Datei (abhängig von Dateityp der hochzulandenden Datei)
            #.xls: application/vnd.ms-excel
            #.xlsx: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet 
            #.txt: text/plain
            mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

            #Datei im Working Directory auslesen
            fl = {'file': (name, open(attachment, 'rb'), mimeType)}

            #Stückliste anhängen
            headers = {
               "Accept": "application/json"
            }

            query = {
               'key': key,
               'token': token
            }

            response = requests.request(
               "POST",
               url = "https://api.trello.com/1/cards/" + trello_card_id + "/attachments",
               headers = headers,
               params = query,
               files = fl
            ) 
            
        return response
    
    #Anlegen einer leeren Checkliste
    def add_checklist(self, trello_card_id):

        #leere Checkliste erzeugen
        query = {
           'key': key,
           'token': token,
           'name': 'Pos. | Stückzahl | Verladen'    #Überschrift der Checkliste
        }

        response = requests.request(
           "POST",
           url = "https://api.trello.com/1/cards/" + trello_card_id + "/checklists",
           params=query
        )

        checklist_id = response.json()["id"]

        return checklist_id
    
    #Anhängen von Checklistenelementen an Checkliste für alle Positionen, die zum selben Arbeitsplatz gehören
    def add_checklist_elements(self, maschine, liste_maschine, liste_position, liste_stückzahl, listofzeros,
                               checklist_id):

        #Indizes der Maschinen bestimmen
        def condition(x): return x == maschine

        checklist_element_index = [idx for idx, element in enumerate(liste_maschine) if condition(element)]

        for i in checklist_element_index:

            #Checklistenelemente zusammenfügen
            checklist_item = list(zip(liste_position, liste_stückzahl, listofzeros))[i]

            #Checklisten-Elemente aneinanderketten
            checklist_item = " | ".join(checklist_item)

            #Checkliste befüllen
            query = {
               'key': key,
               'token': token,
               'name': checklist_item,
               'pos': 'bottom'
            }

            response = requests.request(
               "POST",
               url = "https://api.trello.com/1/checklists/" + checklist_id + "/checkItems",
               params=query
            )
            
        return response
    
    #Hochladen von Daten in eine Produktionskarte und/oder Logistikkarte in Abhängigkeit davon, ob es sich um einen 
    #Produktions- oder Logistikauftrag handelt
    def upload_data(self, liste_auftragsnummerproduktion, versandart, P_list_id, export, ankerpunkte, search,
                    head_P, dt, maschine, liste_maschine, output_P, files, liste_position, liste_stückzahl, 
                    listofzeros, L_list_id, head_L, output_L):

        #prüfen, ob Auftragnummer Produktion mit 'P' beginnt
        if liste_auftragsnummerproduktion[i].startswith('P'):
            
            #prüfen, ob Versandart = 'Lager' ist
            if versandart == 'Lager':
                
                #Produktionskarte erstellen und Produktionsdaten in diese hochladen
                trello_card_id = new_object.create_card('Produktionskarte', P_list_id)
                new_object.add_to_production_card(export, ankerpunkte, search, P_list_id, head_P, dt, trello_card_id)
                new_object.add_description_P(maschine, liste_maschine, output_P, P_list_id, head_P, dt, trello_card_id)
                new_object.add_attachments(maschine, liste_maschine, files, trello_card_id)
                checklist_id = new_object.add_checklist(trello_card_id)
                new_object.add_checklist_elements(maschine, liste_maschine, liste_position, liste_stückzahl, 
                                                  listofzeros, checklist_id)
                
            #falls Versandart nicht 'Lager' ist
            else:
                #Produktionskarte erstellen und Produktionsdaten in diese hochladen
                trello_card_id = new_object.create_card('Produktionskarte', P_list_id)
                new_object.add_to_production_card(export, ankerpunkte, search, P_list_id, head_P, dt, trello_card_id)
                new_object.add_description_P(maschine, liste_maschine, output_P, P_list_id, head_P, dt, trello_card_id)
                new_object.add_attachments(maschine, liste_maschine, files, trello_card_id)
                checklist_id = new_object.add_checklist(trello_card_id)
                new_object.add_checklist_elements(maschine, liste_maschine, liste_position, liste_stückzahl, 
                                                  listofzeros, checklist_id)
                
                #Logistikkarte erstellen und Logistikdaten in diese hochladen
                trello_card_id = new_object.create_card('Logistikkarte', L_list_id)
                new_object.add_to_logistic_card(export, ankerpunkte, search, L_list_id, head_L, dt, trello_card_id)
                new_object.add_description_L(maschine, liste_maschine, output_L, L_list_id, head_L, dt, trello_card_id)
                checklist_id = new_object.add_checklist(trello_card_id)
                new_object.add_checklist_elements(maschine, liste_maschine, liste_position, liste_stückzahl, 
                                                  listofzeros, checklist_id)

        #falls Auftragnummer Produktion nicht mit 'P' beginnt
        else:
            #Logistikkarte erstellen und Logistikdaten in diese hochladen
            trello_card_id = new_object.create_card('Logistikkarte', L_list_id)
            new_object.add_to_logistic_card(export, ankerpunkte, search, L_list_id, head_L, dt, trello_card_id)
            new_object.add_description_L(maschine, liste_maschine, output_L, L_list_id, head_L, dt, trello_card_id)
            checklist_id = new_object.add_checklist(trello_card_id)
            new_object.add_checklist_elements(maschine, liste_maschine, liste_position, liste_stückzahl, 
                                              listofzeros, checklist_id)
        
new_object = Trello()
        
############################
    
#alle Export-Dateien im aktuellen Working Directory auflisten
liste_files = new_object.get_files(search_for)

#Indizes der File-Liste bestimmen
file_index = [*range(len(liste_files))]

#List-IDs der Produktions-Listen der jeweiligen Arbeitsplätze, in die die Karten hereingeladen werden sollen, bestimmen
P_list_id_StortiX = new_object.get_list_id(produktion_board_id, P_list_name_StortiX)
P_list_id_21X = new_object.get_list_id(produktion_board_id, P_list_name_21X)
#weitere List-IDs

#List-IDs der Logistik-Listen der jeweiligen Arbeitsplätze, in die die Karten hereingeladen werden sollen, bestimmen
L_list_id_StortiX = new_object.get_list_id(logistik_board_id, L_list_name_StortiX)
L_list_id_21X = new_object.get_list_id(logistik_board_id, L_list_name_21X)
#weitere List-IDs

#Dateien mit fehlenden Angaben für Produktionskarten in Ordner 'Noch zu erledigen' kopieren
for index in file_index:
    
    source_file = liste_files[index]
    
    #Export-Datei einlesen
    export = pd.read_excel(source_file, header = None)
    
    #Ankerpunkte bestimmen
    ankerpunkte = new_object.get_anker_punkte(export)
    
    #Wenn Feld unterhalb Suchbegriff leer ist, zugehörige Exportdatei verschieben
    for i in ankerpunkte:
        for search in search_list_P:
            
            if ((search == 'Pos_Bezugsquelle') or (search == 'Pos_Menge') 
                or (search == 'Pos_Artikel_Deutsch_SachmerkmalFeld1') or (search == 'Pos_Wunschtermin')):
                new_object.move_excel(search, export, i)

            elif (search == 'F2:Kunde:Name'):
                new_object.move_excel(search, export, 1)
            
            elif (search == 'Pos_Bezeichnung'):
                new_object.move_excel(search, export, i)
                position = i+1
                new_object.move_excel(search, export, i+1)

#Dateien mit fehlenden Angaben für Logistikkarten in Ordner 'Noch zu erledigen' kopieren
for index in file_index:
    source_file = liste_files[index]
    
    #Export-Datei einlesen
    export = pd.read_excel(source_file, header = None)
    
    #Ankerpunkte bestimmen
    ankerpunkte = new_object.get_anker_punkte(export)
    
    #Wenn Feld unterhalb Suchbegriff leer ist, zugehörige Exportdatei verschieben
    for i in ankerpunkte:
        for search in search_list_L:
            
            if ((search == 'F2:Auftragsnummer') or (search == 'F2:Kunde:Name')
                or (search == 'F2:Versandanschrift4') or (search == 'F2:Versandanschrift3')
                or (search == 'F2:Versandart')):
                position = 1
                new_object.move_excel(search, export, position)
                
            elif ((search == 'Pos_Wunschtermin') or (search == 'Pos_Bezeichnung')
                  or (search == 'Pos_Bezugsquelle') or (search == 'Pos_Artikel_Deutsch_Bezeichnung')):
                position = i
                new_object.move_excel(search, export, position)

#Working Directory in Ordner 'Noch zu erledigen' ändern
os.chdir(dst_dirname)

#alle Exportdateien auflisten
liste_tobedone = new_object.get_files(search_for)

#dieselben Dateien im Ursprungsordner löschen
os.chdir(root)
for file in liste_tobedone:
    try:
        os.remove(file)
    except IOError:
        pass

#restliche Export-Dateien im aktuellen Working Directory auflisten
liste_files = new_object.get_files(search_for)

#für jede Export-Datei Karten in zugehöriger Liste in Produktions- und Logistikboard anlegen und befüllen
for file in liste_files:
    
    #Export-Datei einlesen
    export = pd.read_excel(file, header = None)
    
    #Ankerpunkte bestimmen
    ankerpunkte = new_object.get_anker_punkte(export)

    #Artikelbezeichnungen bestimmen
    liste_artikelnummer = []
    for i in ankerpunkte:
        new_object.get_info(export, 'Pos_Bezeichnung', liste_artikelnummer, i)  

    #Dateinamen der Stücklisten in Liste speichern
    files = [s + '-PA.xlsx' for s in liste_artikelnummer]
    
    #Auftragsnummern Produktion auflisten
    liste_auftragsnummerproduktion = []
    for i in ankerpunkte:
        new_object.get_info(export, 'Pos_Bezugsquelle', liste_auftragsnummerproduktion, i)  

    #Versandart bestimmen
    liste_versandart = []
    versandart = new_object.get_info(export, 'F2:Versandart', liste_versandart, 1)[0]
    
    #Auftragspositionen auflisten
    liste_position = []
    for i in ankerpunkte: 
        new_object.get_info(export, 'Pos_Position', liste_position, i)  
    
    #Stückzahlen auflisten
    liste_stückzahl = []
    for i in ankerpunkte:
        new_object.get_info(export, 'Pos_Menge', liste_stückzahl, i)  
        
    #Liste mit Nullen erzeugen
    listofzeros = ['0'] * len(liste_stückzahl)
    
    #Maschinen auflisten
    liste_maschine = []
    for i in ankerpunkte:
        search = 'Pos_Artikel_Deutsch_SachmerkmalFeld1' 
        row = export.loc[export.isin([search]).any(axis=1)].index[0]
        col = export.T.loc[export.T.isin([search]).any(axis=1)].index[0]
        strg = export.iloc[row+i,col].split('*')[5]
        liste_maschine.append(strg)

    #Indizes der Maschinen-Liste bestimmen
    machine_index = [*range(len(liste_maschine))]
    
    #Indizes der Maschinen, die nur einmal vorkommen
    machine_index_unique = [liste_maschine.index(x) for x in set(liste_maschine)]
    
    #Header für Produktionskarte zusammenfügen
    liste_head_P = []
    head_P = new_object.trello_head_P(export, ankerpunkte, search)
    for i in machine_index:
        head = " | ".join(head_P[i])
        liste_head_P.append(head)
    
    #Header für Logistikkarte zusammenfügen
    liste_head_L = []
    head_L = new_object.trello_head_L(export, ankerpunkte, search)
    for i in machine_index:
        head = " | ".join(head_L[i])
        liste_head_L.append(head)
        
    #Datumsformat des Fälligkeitsdatums umwandeln
    ts = new_object.trello_body_P(export, ankerpunkte, search)[0][0]
    dt = datetime.strptime(str(ts), '%Y-%m-%d %H:%M:%S')
     
    #Spaltenüberschriften in Beschreibung der Produktionskarten    
    headings_P = ['Pos.', 
                 'Auftragsnr. Produktion', 
                 'Artikelnummer', 
                 'Beschreibung', 
                 'Workload',
                 'Verladetermin'] 
    
    #Daten für die Beschreibung der Produktionskarte
    data_P = new_object.trello_footer_P(export, ankerpunkte, search)
    
    #Daten in Markdown-Form umwandeln
    fields_P = [0, 1, 2, 3, 4, 5]

    align_P = [('^', '<'), ('^', '^'), ('^', '<'), ('^', '^'), ('^', '>'), ('^','^')]

    table(sys.stdout, data_P, fields_P, headings_P, align_P)

    #Wert der Funktionsausgabe als String auslesen
    old_stdout = sys.stdout

    new_stdout = io.StringIO()

    sys.stdout = new_stdout

    print(table(sys.stdout, data_P, fields_P, headings_P, align_P))

    output_P = new_stdout.getvalue()

    sys.stdout = old_stdout
    
    #Spaltenüberschriften in Beschreibung der Logistikkarten
    headings_L = ['Pos.', 
                 'Artikelnummer', 
                 'Bezugsquelle', 
                 'Artikelbeschreibung',
                 'Verladetag']
    
    #Daten für die Beschreibung der Logistikkarte
    data_L = new_object.trello_footer_L(export, ankerpunkte, search)
    
    #Daten in Markdown-Form umwandeln
    fields_L = [0, 1, 2, 3, 4]

    align_L = [('^', '<'), ('^', '^'), ('^', '<'), ('^', '^'), ('^', '^')]

    table(sys.stdout, data_L, fields_L, headings_L, align_L)

    #Wert der Funktionsausgabe als String auslesen
    old_stdout = sys.stdout

    new_stdout = io.StringIO()

    sys.stdout = new_stdout

    print(table(sys.stdout, data_L, fields_L, headings_L, align_L))

    output_L = new_stdout.getvalue()

    sys.stdout = old_stdout
    
    #für jede Maschine Daten in Karte hochladen, Tabelle in Beschreibung ergänzen, Stücklisten als Anhänge hinzufügen
    #und Checklisten mit Stückzahlen auffüllen
    for i in machine_index_unique:    
        
        if (liste_maschine[i] == 'StortiX'):
            
            P_list_id = P_list_id_StortiX
            head_P = liste_head_P[i]
            maschine = "StortiX"
            L_list_id = L_list_id_StortiX
            head_L = liste_head_L[i]
            
            new_object.upload_data(liste_auftragsnummerproduktion, versandart, P_list_id, export, ankerpunkte,
                                   search, head_P, dt, maschine, liste_maschine, output_P, files,
                                   liste_position, liste_stückzahl, listofzeros, L_list_id, head_L, output_L)

        elif (liste_maschine[i] == '21X'): 

            P_list_id = P_list_id_21X
            head_P = liste_head_P[i]
            maschine = "21X"
            L_list_id = L_list_id_21X
            head_L = liste_head_L[i]
            
            new_object.upload_data(liste_auftragsnummerproduktion, versandart, P_list_id, export, ankerpunkte,
                                   search, head_P, dt, maschine, liste_maschine, output_P, files,
                                   liste_position, liste_stückzahl, listofzeros, L_list_id, head_L, output_L)
            
        #weitere elif-Abschnitte für die anderen Maschinen
        
    #zugehörige Stücklisten in in Ordner 'Erledigt' verschieben, es sei denn sie sind schon dort vorhanden
    dst_dirname = root + '/Erledigt/'
    for s in files:
        try:
            shutil.move(s, dst_dirname)
        except IOError:
            pass
                
#in Trello eingelesene Auftragsdateien in Ordner 'Erledigt' verschieben, es sei denn sie sind schon dort vorhanden
dst_dirname = root + '/Erledigt/'
for file in liste_files:
    try: 
        shutil.move(file, dst_dirname)
    except IOError:
        pass
    
#alle Exportdateien im Ordner 'Erledigt' auflisten
os.chdir(dst_dirname)

liste_tobedone = new_object.get_files(search_for)

#dieselben Dateien im Ursprungsordner löschen
os.chdir(root)
for file in liste_tobedone:
    try:
        os.remove(file)
    except IOError:
        pass
