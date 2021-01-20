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
from nomad.metainfo.legacy import LegacyDefinition

from nomad.datamodel.metainfo import public

m_package = Package(
    name='openkim_nomadmetainfo_json',
    description='None',
    a_legacy=LegacyDefinition(name='openkim.nomadmetainfo.json'))


class section_run(public.section_run):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_run'))

    openkim_build_date = Quantity(
        type=str,
        shape=[],
        description='''
        build date as string
        ''',
        categories=[public.accessory_info, public.program_info],
        a_legacy=LegacyDefinition(name='openkim_build_date'))

    openkim_src_date = Quantity(
        type=str,
        shape=[],
        description='''
        date of last modification of the source as string
        ''',
        categories=[public.accessory_info, public.program_info],
        a_legacy=LegacyDefinition(name='openkim_src_date'))


class section_method(public.section_method):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_method'))

    x_openkim_atom_kind_refs = Quantity(
        type=public.section_method_atom_kind,
        shape=['number_of_atoms'],
        description='''
        reference to the atom kinds of each atom
        ''',
        a_legacy=LegacyDefinition(name='x_openkim_atom_kind_refs'))


m_package.__init_metainfo__()
