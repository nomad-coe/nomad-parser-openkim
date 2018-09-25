import requests
from requests.exceptions import Timeout, TooManyRedirects, RequestException, HTTPError
from datetime import datetime
import re
import sys
import numpy as np
import json
from tinydb import TinyDB, Query

dbasefile = "openkim_query_database.json"

kimdb = TinyDB(dbasefile)

atomlabel = 'Al'
structure = 'fcc'

#nomad_space_group_map={
#    'sc'     : '221',
#    "fcc"    : '225',
#    'bcc'    : '229',
#    'diamond': '227'
#}

def secondsFromEpoch(date):
    epoch = datetime(1970,1,1)
    ts=date-epoch
    return ts.seconds + ts.microseconds/1000.0

def get_timestep(kim_date):
    pdate = None
    if kim_date:
        pdate = datetime.strptime(kim_date.strip(), "%Y-%m-%d %H:%M:%S.%f")
    if pdate:
        pdate = secondsFromEpoch(pdate)
    return pdate

def OPENKIM_query(atomlabel, structure, properties=None):
    """
    atomlabel:
    ----------
    string : element symbol
    
    structure:
    ----------
    string : fcc, bcc, sc, diamond

    properties:
    -----------
    string : lattice_energy, elastic_constants

    returns:
    --------
    dictionary of OpenKIM entry
    """
    openkim_query = None
    try:
        query = requests.post(
                url="https://query.openkim.org/api",
                data={
                    'flat'    : 'on',
                    'database': 'data',
                    'limit'   : '0',
                    'fields'  : json.dumps({
                        #"a.si-value": "1",
                        #"cohesive-potential-energy.si-value" : "1",
                        #"meta.subject.kimcode": "1"
                        }),
                    'query' : json.dumps({
                        "meta.type"   : "tr",
                    #"property-id" : {
                    #    "$regex"  : ":property/structure-cubic-crystal-npt"
                    #},
                    #"meta.runner.kimcode" : {
                    #    "$regex"  : "^LatticeConstantCubicEnergy"
                    #},
                    #"species.source-value": {
                    #    "$all" : [atomlabel], 
                    #    "$not" : {
                    #        "$elemMatch" : {
                    #            "$nin" : [atomlabel]
                    #            }
                    #        }
                    #    },
                    "short-name.source-value": structure
                    })
                }
            )
        query.raise_for_status()
        openkim_query = query.json()
    except(ConnectionError, HTTPError, Timeout, TooManyRedirects, RequestException):
        print("OpenKIM request exception: %s" % sys.exc_info()[1])

    return openkim_query
   
openkim_data  = OPENKIM_query(atomlabel, structure)
if openkim_data:
    
    now = datetime.today().strftime("%Y-%m-%d %H:%M:%S.%f")

    updated_data = []
    kim_item = Query()
    for item in openkim_data:
        kim_instance_id = item["instance-id"]
        kim_unique_code = item["meta._id"]
        kim_result_code = item["meta.test-result-id"]
        kim_unique_code = kim_unique_code + '-' + str(kim_instance_id)
        kim_result_code = kim_result_code + '-' + str(kim_instance_id)
        kim_create_date = get_timestep(item["meta.created_on"])
        kim_insert_date = get_timestep(item["inserted_on"])
        db_entry = kimdb.search((kim_item.unique_id == kim_unique_code and 
            kim_item.result_id == kim_result_code))
        if db_entry:
            if db_entry[0]["insert_timestep"] < kim_insert_date:
                kimdb.update({
                    'insert_timestep': kim_insert_date, 
                    }, 
                    (kim_item.unique_id == kim_unique_code and
                     kim_item.result_id == kim_result_code))
                updated_data.append(item)
        else:
            kimdb.insert({
                'unique_id': kim_unique_code, 
                'result_id': kim_unique_code, 
                'insert_timestep': kim_insert_date, 
                })
            updated_data.append(item)
   
    if updated_data:
        openkim_query = {}
        openkim_query['OPENKIM_QUERY_OUTPUT'] = 'OPENKIM_QUERY_OUTPUT'
        openkim_query['QUERY'] = updated_data

        with open('data.json', 'w') as outfile:
            json.dump(openkim_query, outfile, 
                    sort_keys = True, indent = 4,
                    ensure_ascii = True)
        with open('data.json', 'r') as databfile:
            qdata = json.load(databfile)

