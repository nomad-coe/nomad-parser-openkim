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

import os
import logging
import json
from datetime import datetime
from ase.spacegroup import crystal as asecrystal
import numpy as np

from nomad.parsing import FairdiParser
from nomad.datamodel import EntryArchive

from nomad.datamodel.metainfo.simulation.run import Run, Program
from nomad.datamodel.metainfo.simulation.system import System, Atoms
from nomad.datamodel.metainfo.simulation.calculation import (
    Calculation, Energy, EnergyEntry, Thermodynamics, Stress, StressEntry)
import openkimparser.metainfo  # pylint: disable=unused-import


class Converter:
    def __init__(self, entries):
        self.entries = entries

    @property
    def entries(self):
        return self._entries

    @entries.setter
    def entries(self, value):
        self._entries = value
        self.archive = EntryArchive()

    def convert(self, filename='openkim_archive.json'):
        def get_value_list(entry, key):
            val = entry.get(key, [])
            return val if isinstance(val, list) else [val]

        def get_crystal(entry):
            symbols = entry.get('species.source-value', [])
            basis = entry.get('basis-atom-coordinates.source-value', [])
            spacegroup = entry.get('space-group.source-value', 1)
            cellpar_a = entry.get('a.si-value', 1)
            cellpar_b = entry.get('b.si-value', cellpar_a)
            cellpar_c = entry.get('c.si-value', cellpar_a)
            # TODO are angles denoted by alpha, beta, gamma in openkim? can they be lists?
            alpha = entry.get('alpha.source-value', 90)
            beta = entry.get('beta.source-value', 90)
            gamma = entry.get('gamma.source-value', 90)

            if isinstance(cellpar_a, float):
                cellpar_a, cellpar_b, cellpar_c = [cellpar_a], [cellpar_b], [cellpar_c]

            atoms = []
            for n in range(len(cellpar_a)):
                try:
                    atoms.append(asecrystal(
                        symbols=symbols, basis=basis, spacegroup=spacegroup, cellpar=[
                            cellpar_a[n], cellpar_b[n], cellpar_c[n], alpha, beta, gamma]))
                except Exception:
                    pass
            return atoms

        # first entry is the parser-generated header used identify an  open-kim
        for entry in self.entries:
            sec_run = self.archive.m_create(Run)
            sec_run.program = Program(name='OpenKIM', version=entry.get('meta.runner.short-id'))

            compile_date = entry.get('meta.created_on')
            if compile_date is not None:
                dt = datetime.strptime(compile_date, '%Y-%m-%d %H:%M:%S.%f') - datetime(1970, 1, 1)
                sec_run.program.compilation_datetime = dt.total_seconds()

            crystals = get_crystal(entry)
            for crystal in crystals:
                sec_system = sec_run.m_create(System)
                sec_atoms = sec_system.m_create(Atoms)
                sec_atoms.labels = crystal.get_chemical_symbols()
                sec_atoms.positions = crystal.get_positions()
                sec_atoms.lattice_vectors = crystal.get_cell().array
                sec_atoms.periodic = [True, True, True]

            energies = get_value_list(entry, 'cohesive-potential-energy.si-value')
            temperatures = get_value_list(entry, 'temperature.si-value')
            for n, energy in enumerate(energies):
                sec_scc = sec_run.m_create(Calculation)
                sec_scc.energy = Energy(total=EnergyEntry(value=energy))
                if temperatures:
                    sec_scc.thermodynamics = Thermodynamics(temperature=temperatures[n])

            stress = entry.get('cauchy-stress.si-value')
            if stress is not None:
                sec_scc = sec_run.calculation[-1] if sec_run.calculation else sec_run.m_create(Calculation)
                stress_tensor = np.zeros((3, 3))
                stress_tensor[0][0] = stress[0]
                stress_tensor[1][1] = stress[1]
                stress_tensor[2][2] = stress[2]
                stress_tensor[1][2] = stress_tensor[2][1] = stress[3]
                stress_tensor[0][2] = stress_tensor[2][0] = stress[4]
                stress_tensor[0][1] = stress_tensor[1][0] = stress[5]
                sec_scc.stress = Stress(total=StressEntry(value=stress_tensor))
        # TODO implement openkim specific metainfo

        # write archive to file
        if filename is not None:
            with open(filename, 'w') as f:
                json.dump(self.archive.m_to_dict(), f, indent=4)


class OpenKIMParser(FairdiParser):
    def __init__(self):
        super().__init__(
            name='parsers/openkim', code_name='OpenKIM', domain='dft',
            mainfile_mime_re=r'(application/json)|(text/.*)',
            mainfile_contents_re=r'openkim|OPENKIM|OpenKIM')

    def parse(self, filepath, archive, logger):
        logger = logger if logger is not None else logging.getLogger('__name__')

        try:
            with open(os.path.abspath(filepath), 'rt') as f:
                archive_data = json.load(f)
        except Exception:
            logger.error('Error reading openkim archive')
            return

        if isinstance(archive_data, dict) and archive_data.get('run') is not None:
            archive.m_update_from_dict(archive_data)
            return

        # support for old version
        if isinstance(archive_data, dict) and archive_data.get('QUERY') is not None:
            archive_data = archive_data['QUERY']

        converter = Converter(archive_data)
        converter.archive = archive
        converter.convert()


def openkim_entries_to_nomad_archive(entries, filename=None):
    if isinstance(entries, str):
        if filename is None:
            filename = 'openkim_archive_%s.json' % entries.rstrip('.json')
        with open(entries) as f:
            entries = json.load(f)

    Converter(entries).convert(filename)
