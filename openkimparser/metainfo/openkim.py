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
