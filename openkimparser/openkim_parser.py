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

from nomad.datamodel.metainfo.common_dft import Run, SingleConfigurationCalculation, System


class OpenKIMParser(FairdiParser):
    def __init__(self):
        super().__init__(
            name='parsers/openkim', code_name='OpenKIM', domain='dft',
            mainfile_contents_re=r'OPENKIM')

    def parse(self, filepath, archive, logger):
        self.filepath = os.path.abspath(filepath)
        self.archive = archive
        self.logger = logger if logger is not None else logging.getLogger('__name__')

        with open(self.filepath) as f:
            self.json = json.load(f)

        def set_value(section, key, val, unit=None):
            if val is None:
                return
            val = val * unit if unit is not None else val
            setattr(section, key, val)

        def get_value_list(entry, key):
            val = entry.get(key, [])
            return val if isinstance(val, list) else [val]

        def get_crystal(entry):
            symbols = entry.get('species.source-value', [])
            basis = entry.get('basis-atom-coordinates.source-value', [])
            spacegroup = entry.get('space-group.source-value', 1)
            cellpar_a = entry.get('a.si-value', 1)
            cellpar_b = entry.get('a.si-value', cellpar_a)
            cellpar_c = entry.get('b.si-value', cellpar_a)
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

        for entry in self.json:
            sec_run = self.archive.m_create(Run)
            sec_run.program_name = 'OpenKIM'
            set_value(sec_run, 'program_version', entry.get('meta.runner.short-id'))

            compile_date = entry.get('meta.created_on')
            if compile_date is not None:
                dt = datetime.strptime(compile_date, '%Y-%m-%d %H:%M:%S.%f') - datetime(1970, 1, 1)
                sec_run.program_compilation_datetime = dt.total_seconds()

            crystals = get_crystal(entry)
            for crystal in crystals:
                sec_system = sec_run.m_create(System)
                sec_system.atom_labels = crystal.get_chemical_symbols()
                sec_system.atom_positions = crystal.get_positions()
                sec_system.lattice_vectors = crystal.get_cell().array
                sec_system.configuration_periodic_dimensions = [True, True, True]

            energies = get_value_list(entry, 'cohesive-potential-energy.si-value')
            temperatures = get_value_list(entry, 'temperature.si-value')
            for n, energy in enumerate(energies):
                sec_scc = sec_run.m_create(SingleConfigurationCalculation)
                sec_scc.energy_total = energy
                if temperatures:
                    sec_scc.temperature = temperatures[n]

            stress = entry.get('cauchy-stress.si-value')
            if stress is not None:
                stress_tensor = np.zeros((3, 3))
                stress_tensor[0][0] = stress[0]
                stress_tensor[1][1] = stress[1]
                stress_tensor[2][2] = stress[2]
                stress_tensor[1][2] = stress[2][1] = stress[3]
                stress_tensor[0][2] = stress[2][0] = stress[4]
                stress_tensor[0][1] = stress[1][0] = stress[5]

        # TODO implement openkim specific metainfo
