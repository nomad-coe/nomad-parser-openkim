#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
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

import pytest

from nomad.datamodel import EntryArchive
from openkimparser import OpenKIMParser


def approx(value, abs=0, rel=1e-6):
    return pytest.approx(value, abs=abs, rel=rel)


@pytest.fixture(scope='module')
def parser():
    return OpenKIMParser()


def test_entry1(parser):
    archive = EntryArchive()
    parser.parse('tests/data/data.json', archive, None)

    sec_runs = archive.run
    assert len(sec_runs) == 10
    assert sec_runs[1].program.version == 'TE_929921425793_007'

    sec_system = sec_runs[3].system[0]
    assert sec_system.atoms.labels == ['Ag', 'Ag']
    assert sec_system.atoms.positions[1][1].magnitude == approx(1.65893189e-10,)
    assert sec_system.atoms.lattice_vectors[2][2].magnitude == approx(3.31786378e-10)

    sec_scc = sec_runs[8].calculation[0]
    assert sec_scc.energy.total.value.magnitude == approx(4.513135831891813e-19)


def test_entry2(parser):
    archive = EntryArchive()
    parser.parse('tests/data/TE_531821030293_000_and_MO_122703700223_002_1500785453_tr.json', archive, None)

    assert len(archive.run) == 1


def test_archive(parser):
    archive = EntryArchive()
    parser.parse('tests/data/openkim_archive_data.json', archive, None)

    assert len(archive.run) == 10
