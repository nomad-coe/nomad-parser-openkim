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
import re
import logging
import json
from datetime import datetime
from ase.cell import Cell as asecell
from ase.atoms import Atoms as aseatoms
import numpy as np

from nomad.units import ureg
from nomad.parsing import FairdiParser
from nomad.datamodel import EntryArchive

from nomad.datamodel.metainfo.simulation.run import Run, Program
from nomad.datamodel.metainfo.simulation.system import System, Atoms
from nomad.datamodel.metainfo.simulation.calculation import (
    BandEnergies, BandStructure, Calculation, Energy, EnergyEntry, Thermodynamics, Stress, StressEntry)
from nomad.datamodel.metainfo.workflow import Phonon, Workflow, Elastic, Interface
import openkimparser.metainfo  # pylint: disable=unused-import


class Converter:
    def __init__(self, entries, logger=None):
        self.entries = entries
        self.logger = logger if logger is not None else logging.getLogger('__name__')

    @property
    def entries(self):
        return self._entries

    @entries.setter
    def entries(self, value):
        self._entries = value
        self.archive = EntryArchive()

    def convert(self, filename='openkim_archive.json'):
        def get_value(entry, key, array=False, default=None):
            val = entry.get(key, [] if array else default)
            return [val] if array and not isinstance(val, list) else val
            # unit = entry.get(re.sub('-value', '-unit', key))
            # return val * ureg(unit) if unit is not None else val

        def symmetrize_matrix(matrix):
            return np.tril(matrix) + np.triu(np.transpose(matrix), 1)

        def get_atoms(entry):
            symbols = entry.get('species.source-value', [])
            basis = entry.get('basis-atom-coordinates.source-value', [[0., 0., 0.]])
            spacegroup = entry.get('space-group.source-value', 1)
            cellpar = []
            for x in ['a', 'b', 'c']:
                value = entry.get(f'{x}.si-value', cellpar[0] if cellpar else 1)
                cellpar.append([value] if not isinstance(value, list) else value)
            cellpar = (cellpar * ureg.m).to('angstrom').magnitude

            # TODO are angles denoted by alpha, beta, gamma in openkim? can they be lists?
            alpha = entry.get('alpha.source-value', 90)
            beta = entry.get('beta.source-value', 90)
            gamma = entry.get('gamma.source-value', 90)

            atoms = []
            for n in range(len(cellpar[0])):
                try:
                    cell = asecell.fromcellpar([cellpar[0][n], cellpar[1][n], cellpar[2][n], alpha, beta, gamma])
                    atom = aseatoms(scaled_positions=basis, cell=cell, pbc=True)
                    if len(symbols) == len(atom.numbers):
                        atom.symbols = symbols
                    else:
                        atom.symbols = ['X' for _ in atom.numbers] if len(symbols) == 0 else symbols
                    atoms.append(atom)
                except Exception:
                    self.logger.error('Error generating structure.')
            return atoms

        # first entry is the parser-generated header used identify an  open-kim
        for entry in self.entries:
            sec_run = self.archive.m_create(Run)
            sec_run.program = Program(name='OpenKIM', version=entry.get('meta.runner.short-id'))

            compile_date = entry.get('meta.created_on')
            if compile_date is not None:
                dt = datetime.strptime(compile_date, '%Y-%m-%d %H:%M:%S.%f') - datetime(1970, 1, 1)
                sec_run.program.compilation_datetime = dt.total_seconds()

            # openkim metadata
            sec_run.x_openkim_meta = {key: entry.pop(key) for key in list(entry.keys()) if key.startswith('meta.')}

            atoms = get_atoms(entry)
            for atom in atoms:
                sec_system = sec_run.m_create(System)
                sec_atoms = sec_system.m_create(Atoms)
                sec_atoms.labels = atom.get_chemical_symbols()
                sec_atoms.positions = atom.get_positions() * ureg.angstrom
                sec_atoms.lattice_vectors = atom.get_cell().array * ureg.angstrom
                sec_atoms.periodic = [True, True, True]

            energies = get_value(entry, 'cohesive-potential-energy.si-value', True)
            for n, energy in enumerate(energies):
                sec_scc = sec_run.m_create(Calculation)
                sec_scc.energy = Energy(total=EnergyEntry(value=energy))

            temperatures = get_value(entry, 'temperature.si-value', True)
            for n, temperature in enumerate(temperatures):
                sec_scc = sec_run.calculation[n] if sec_run.calculation else sec_run.m_create(Calculation)
                sec_scc.thermodynamics.append(Thermodynamics(temperature=temperature))

            stress = get_value(entry, 'cauchy-stress.si-value')
            if stress is not None:
                sec_scc = sec_run.calculation[-1] if sec_run.calculation else sec_run.m_create(Calculation)
                stress_tensor = np.zeros((3, 3))
                stress_tensor[0][0] = stress[0]
                stress_tensor[1][1] = stress[1]
                stress_tensor[2][2] = stress[2]
                stress_tensor[1][2] = stress_tensor[2][1] = stress[3]
                stress_tensor[0][2] = stress_tensor[2][0] = stress[4]
                stress_tensor[0][1] = stress_tensor[1][0] = stress[5]
                sec_scc.stress = Stress(total=StressEntry(value=symmetrize_matrix(stress_tensor)))

            for key, val in entry.items():
                key = 'x_openkim_%s' % re.sub(r'\W', '_', key)
                try:
                    setattr(sec_run, key, val)
                except Exception:
                    pass

            # workflow
            property_id = entry.get('property-id', '')
            # elastic constants
            if 'elastic-constants' in property_id:
                sec_workflow = self.archive.m_create(Workflow)
                sec_workflow.type = 'elastic'
                sec_elastic = sec_workflow.m_create(Elastic)
                cij = [[get_value(entry, f'c{i}{j}.si-value', default=0) for i in range(1, 7)] for j in range(1, 7)]
                sec_elastic.elastic_constants_matrix_second_order = symmetrize_matrix(cij)

                if 'strain-gradient' in property_id:
                    dij = [[get_value(entry, f'd-{i}-{j}.si-value', default=0) for i in range(1, 19)] for j in range(1, 19)]
                    sec_elastic.elastic_constants_gradient_matrix_second_order = symmetrize_matrix(dij)

                if 'excess.si-value' in entry:
                    sec_elastic.x_openkim_excess = entry['excess.si-value']

            if 'gamma-surface' in property_id or 'stacking-fault' in property_id or 'twinning-fault' in property_id:
                sec_workflow = self.archive.m_create(Workflow)
                sec_workflow.type = 'interface'
                sec_interface = sec_workflow.m_create(Interface)
                if 'gamma-surface.si-value' in entry:
                    directions, displacements = [], []
                    for key in entry.keys():
                        direction = re.match(r'fault-plane-shift-fraction-(\d+).source-value', key)
                        if direction:
                            directions.append(direction.group(1))
                            displacements.append(entry[key])
                    sec_interface.dimensionality = len(directions)
                    sec_interface.shift_direction = directions
                    sec_interface.displacement_fraction = displacements
                    sec_interface.gamma_surface = entry['gamma-surface.si-value']

                if 'fault-plane-energy.si-value' in entry:
                    sec_interface.dimensionality = 1
                    sec_interface.displacement_fraction = [entry['fault-plane-shift-fraction.source-value']]
                    sec_interface.energy_fault_plane = entry['fault-plane-energy.si-value']

                sec_interface.energy_extrinsic_stacking_fault = entry.get('extrinsic-stacking-fault-energy.si-value')
                sec_interface.energy_intrinsic_stacking_fault = entry.get('intrinsic-stacking-fault-energy.si-value')
                sec_interface.energy_unstable_stacking_fault = entry.get('unstable-stacking-energy.si-value')
                sec_interface.energy_unstable_twinning_fault = entry.get('unstable-twinning-energy.si-value')
                sec_interface.slip_fraction = entry.get('unstable-slip-fraction.source-value')

            if 'phonon-dispersion' in property_id:
                sec_workflow = self.archive.m_create(Workflow)
                sec_workflow.type = 'phonon'
                sec_phonon = sec_workflow.m_create(Phonon)
                if 'response-frequency.si-value' in entry:
                    sec_scc = sec_run.calculation[-1] if sec_run.calculation else sec_run.m_create(Calculation)
                    sec_bandstructure = sec_scc.m_create(BandStructure, Calculation.band_structure_phonon)
                    # TODO find a way to segment the frequencies
                    sec_segment = sec_bandstructure.m_create(BandEnergies)
                    energies = entry['response-frequency.si-value']
                    if len(np.shape(energies)) == 1:
                        energies = energies[0]
                    sec_segment.energies = [entry['response-frequency.si-value']]
                    try:
                        wavevector = entry['wave-vector-direction.si-value']
                        cell = sec_run.system[-1].atoms.lattice_vectors.magnitude
                        # TODO how about spin-polarized case, not sure about calculation of kpoints value
                        sec_segment.kpoints = np.dot(wavevector, cell)
                    except Exception:
                        pass
                if 'wave-number.si-value' in entry:
                    sec_phonon.x_openkim_wave_number = [entry['wave-number.si-value']]
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

        converter = Converter(archive_data, logger)
        converter.archive = archive
        converter.convert()


def openkim_entries_to_nomad_archive(entries, filename=None):
    if isinstance(entries, str):
        if filename is None:
            filename = 'openkim_archive_%s.json' % os.path.basename(entries).rstrip('.json')
        with open(entries) as f:
            entries = json.load(f)

    Converter(entries).convert(filename)
