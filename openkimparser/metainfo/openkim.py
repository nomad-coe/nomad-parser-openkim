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
import numpy as np            # pylint: disable=unused-import
import typing                 # pylint: disable=unused-import
from nomad.metainfo import (  # pylint: disable=unused-import
    MSection, MCategory, Category, Package, Quantity, Section, SubSection, SectionProxy,
    Reference
)
from nomad.datamodel.metainfo import run


class Run(run.run.Run):

    m_def = Section(validate=False, extends_base_section=True)

    openkim_build_date = Quantity(
        type=str,
        shape=[],
        description='''
        build date as string
        ''')

    openkim_src_date = Quantity(
        type=str,
        shape=[],
        description='''
        date of last modification of the source as string
        ''')


class Method(run.method.Method):

    m_def = Section(validate=False, extends_base_section=True)

    x_openkim_atom_kind_refs = Quantity(
        type=run.method.AtomParameters,
        shape=['number_of_atoms'],
        description='''
        reference to the atom kinds of each atom
        ''')
