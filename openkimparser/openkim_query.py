#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD.
# See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import requests
import json
import re
import os
from nomad.client import api


openkim_url = 'https://query.openkim.org/api'
openkim_ids = ['meta.uuid', 'property-id', 'meta.test-result-id', 'meta.subject.short-id', 'created_on']


def get_nomad_openkim_entries(element):
    entries = []
    page_after_value = None
    # TODO get the openkim uuid
    query = {'owner': 'all', 'query': {'parser_name': 'parsers/openkim', 'results.material.elements': [element]}}
    while True:
        response = api.post('entries/query', data=json.dumps({
            'owner': 'all',
            'query': query,
            'aggregations': {
                'mainfiles': {
                    'terms': {
                        'quantity': 'mainfile',
                        'pagination': {
                            'page_size': 1000,
                            'page_after_value': page_after_value
                        }
                    }
                }
            }
        }))
        assert response.status_code == 200
        aggregation = response.json()['aggregations']['mainfiles']['terms']
        page_after_value = aggregation['pagination']['next_page_after_value']
        for bucket in aggregation['data']:
            entries.append(bucket['value'])
        if len(aggregation['data']) < 1000 or page_after_value is None:
            break


def query(element: str, check_nomad: bool = False, convert_to_nomad_archive: bool = False):
    '''
    Query the openkim api for all entries containing the element provided. Writes each of
    the entries as separate files prefixed by one of the openkim ids. Will check the nomad
    database if the entry exists with the filename as mainfile.
    '''
    results = requests.post(openkim_url, data={
        'query': '{"species.source-value":"%s"}' % element,
        'fields': '{}', 'database': 'data', 'limit': '0', 'flat': 'on'}).json()

    for n, result in enumerate(results):
        uuid = None
        for key in openkim_ids:
            uuid = result.get(key)
            if uuid is not None:
                break

        if uuid is None:
            print('Cannot resolve entry ID for entry %d, skipping.' % n)
            continue

        filename = '%s.json' % re.sub(r'\W', '_', uuid)
        if check_nomad:
            # generate nomad list and compare uuid
            nomad_query = api.post('entries/query', data=json.dumps(
                {'owner': 'all', 'query': {'mainfile': filename}}))
            result = nomad_query.json().get('pagination', {}).get('total', 0) > 0

        if result and not os.path.isfile(filename):
            with open(filename, 'w') as f:
                json.dump([result], f, indent=4)
