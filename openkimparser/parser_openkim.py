# coding=utf-8
from __future__ import division
from builtins import map
from builtins import range
from builtins import object
import logging, sys, bisect
from datetime import datetime
import re, traceback
from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
import numpy as np
from nomadcore.unit_conversion.unit_conversion import convert_unit_function
from nomadcore.unit_conversion.unit_conversion import convert_unit
import ase.geometry
import ase.data
import ase.build
import json
from ase import Atoms
from ase.data import atomic_numbers, chemical_symbols
from math import pi
from contextlib import contextmanager

@contextmanager
def open_section(parser, backend, name):
    parser.gidSections[name] = backend.openSection(name)
    yield parser.gidSections[name]
    backend.closeSection(name, parser.gidSections[name])

def metaNameConverter(keyName):
    newName = keyName.lower().replace(" ", "").replace("-", "")
    newName = newName.replace("(", "").replace(")", "")
    newName = newName.replace("[", "").replace("]", "")
    newName = newName.replace(",", "").replace(".", "")
    newName = newName.replace("\\", "").replace("/", "")
    newName = newName.replace("'", "").replace(":", "")
    return newName

def metaNameConverter_UnderscoreAll(keyName):
    newName = keyName.lower()
    newName = ' '.join(newName.split())
    newName = newName.replace(" ", "_").replace("-", "_").replace(".", "_")
    newName = metaNameConverter(newName)
    return newName

def metaNameConverter_OpenKIM(keyName):
    newName = metaNameConverter_UnderscoreAll(keyName)
    newName = 'x_openkim_' + newName
    return newName

def secondsFromEpoch(date):
    epoch = datetime(1970,1,1)
    ts=date-epoch
    return ts.seconds + ts.microseconds/1000.0

def KIMQueryReader(jsonfile):
    with open(jsonfile, 'r') as dbfile:
        data = json.load(dbfile)
    return data['QUERY']

class OpenkimContext(object):
    def __init__(self):
        self.parser = None
        self.weights = None
        self.lastSystemDescription = None
        self.labels = None
        self.singleConfCalcs = []
        self.KIM_TE = 0
        self.KIM_TD = None
        self.KIM_MO = None
        self.KIM_MD = None
        self.cell = None
        self.temperature = []
        self.cohesivepot = []
        self.cohesiveeng = []

    def reset(self):
        self.lastSystemDescription = None
        self.labels = None
        self.singleConfCalcs = []
        self.KIM_TE = 0
        self.KIM_TD = None
        self.KIM_MO = None
        self.KIM_MD = None
        self.cell = None
        self.temperature = []
        self.cohesivepot = []
        self.cohesiveeng = []

    def startedParsing(self, parser):
        self.parser = parser

    def onEnd_program(self, parser, querydict):
        backend = parser.backend
        backend.addValue("program_name", "OpenKIM")
        backend.addValue("program_version", g(querydict, "meta.runner.short-id", ""))
        date = g(querydict, "meta.created_on")
        pdate = None
        if date:
            pdate = datetime.strptime(date.strip(), "%Y-%m-%d %H:%M:%S.%f")
        if pdate:
            backend.addValue("program_compilation_datetime", secondsFromEpoch(pdate))

    def onEnd_openkim_data(self, parser, kimquery):
        for k,v in kimquery.items():
            nomad_k = metaNameConverter_OpenKIM(k)
            if isinstance(v, (list,tuple)):
                dictInList = False
                if len(v)>0:
                    if isinstance(v[0], dict):
                        dictInList = True
                if dictInList:
                    for it, item in enumerate(v):
                        if isinstance(item, dict):
                            #keyFooter = '_' + str(it+1)
                            for key, val in item.items():
                                #key = nomad_k + '_' + key + keyFooter
                                key = nomad_k + '_' + key
                                if isinstance(val, list):
                                    backend.addArrayValues(key,np.asarray(val))
                                else:
                                    backend.addValue(key,val)
                else:
                    backend.addArrayValues(nomad_k,np.asarray(v))
            elif isinstance(v, dict):
                for key, val in item.items():
                    key = nomad_k + '_' + key
                    if isinstance(val, list):
                        backend.addArrayValues(key,np.asarray(val))
                    else:
                        backend.addValue(key,val)
            else:
                backend.addValue(nomad_k,v)

    def onEnd_structure(self, parser, querydict, step=0):
        backend = parser.backend
        self.lastSystemDescription = parser.gidSections["section_system"]
        self.cell = None
        self.labels = None
        celltype = None
        if('basis-atom-coordinates.source-value' in querydict and
           ('a.si-value' in querydict) or
           ('b.si-value' in querydict) or
           ('c.si-value' in querydict) or
           ('a-host.si-value' in querydict) or
           ('b-host.si-value' in querydict) or
           ('c-host.si-value' in querydict)):
            basis = querydict['basis-atom-coordinates.source-value']
            #celltype = ase.geometry.crystal_structure_from_cell(basis)
            if not celltype:
                kimprefix = g(querydict, 'meta.runner.kimid-prefix', None).split('_')
                celltype = kimprefix[1] if len(kimprefix)>1 else None
            if not celltype:
                kimprefix = g(querydict, 'meta.runner.extended-id', None).split('_')
                celltype = kimprefix[1] if len(kimprefix)>1 else None
            if celltype:
                backend.addValue("x_openkim_cubic_crystal_type", celltype)
            if 'species.source-value' in querydict:
                self.labels = querydict['species.source-value']
                species_nums = [atomic_numbers[Z] for Z in self.labels]
                a_si_val = querydict['a.si-value']
                if isinstance(a_si_val, list):
                    lat_a = float(a_si_val[int(step)])
                else:
                    lat_a = float(a_si_val)
                si_conv = convert_unit_function("m", "angstrom")
                cellAtoms = Atoms(
                        positions=basis,
                        cell=[si_conv(lat_a),
                              si_conv(lat_a),
                              si_conv(lat_a)],
                        pbc=True)
                cellAtoms.positions = ase.geometry.wrap_positions(cellAtoms.positions, cellAtoms.cell, pbc=True)
                if len(cellAtoms.numbers) == len(species_nums):
                    cellAtoms.numbers = species_nums
                else:
                    if len(species_nums)<2 and len(cellAtoms.numbers)>1:
                        cellAtoms.numbers = [species_nums[0] for i in cellAtoms.numbers]
                if len(self.labels)<2:
                    self.labels = [self.labels[0] for s in cellAtoms.positions]
                ang_conv = convert_unit_function("angstrom", "m")
                si_cell = np.array([[ang_conv(x) for x in i] for i in cellAtoms.cell])
                si_pos = np.array([[ang_conv(x) for x in i] for i in cellAtoms.positions])
                backend.addArrayValues("simulation_cell", si_cell)
                backend.addArrayValues("configuration_periodic_dimensions", np.ones(3, dtype=bool))
                backend.addArrayValues("atom_positions", si_pos)
        if self.labels is not None:
            backend.addArrayValues("atom_labels", np.asarray(self.labels))

    def onEnd_model(self, parser, kimquery):
        backend = parser.backend
        with open_section(parser, backend, "section_sampling_method"):
            if self.KIM_TE == 0:
                sampling_method = "geometry_optimization"
            else:
                sampling_method = "molecular_dynamics"
            backend.addValue("sampling_method", sampling_method)
        with open_section(parser, backend, "section_frame_sequence"):
            if self.temperature:
                backend.addArrayValues('frame_sequence_temperature_frames', np.array([
                    i for i in self.singleConfCalcs]))
                if isinstance(self.temperature, list):
                    if len(self.temperature)<2:
                        backend.addArrayValues('frame_sequence_temperature', np.array([
                            self.temperature[0] for i in self.singleConfCalcs]))
                    else:
                        backend.addArrayValues('frame_sequence_temperature', np.asarray(self.temperature))
                else:
                    backend.addArrayValues('frame_sequence_temperature', np.asarray([self.temperature]))
            if self.cohesivepot:
                backend.addArrayValues('frame_sequence_potential_energy_frames', np.array([
                    i for i in self.singleConfCalcs]))
                if isinstance(self.cohesivepot, list):
                    if len(self.cohesivepot)<2:
                        backend.addArrayValues('frame_sequence_potential_energy', np.array([
                            self.cohesivepot[0] for i in self.singleConfCalcs]))
                    else:
                        backend.addArrayValues(
                                'frame_sequence_potential_energy', np.asarray(self.cohesivepot))
                else:
                    backend.addArrayValues(
                            'frame_sequence_potential_energy', np.asarray([self.cohesivepot]))
            if self.cohesiveeng:
                backend.addArrayValues('x_openkim_frame_sequence_cohesive_energy_frames', np.array([
                    i for i in self.singleConfCalcs]))
                if isinstance(self.cohesiveeng, list):
                    if len(self.cohesiveeng)<2:
                        backend.addArrayValues('x_openkim_frame_sequence_cohesive_energy', np.array([
                            self.cohesiveeng for i in self.singleConfCalcs]))
                    else:
                        backend.addArrayValues(
                                'x_openkim_frame_sequence_cohesive_energy', np.asarray(self.cohesiveeng))
                else:
                    backend.addArrayValues(
                            'x_openkim_frame_sequence_cohesive_energy', np.asarray([self.cohesiveeng]))
            backend.addArrayValues('frame_sequence_time', np.array([0. for i in self.singleConfCalcs]))
            backend.addValue("frame_sequence_to_sampling_ref", parser.gidSections["section_sampling_method"])
            backend.addArrayValues("frame_sequence_local_frames_ref", np.asarray(self.singleConfCalcs))

    def onEnd_calculation(self, parser, kimquery, step=0):
        backend = parser.backend
        backend.addValue("single_configuration_calculation_to_system_ref", self.lastSystemDescription)
        zeroTemp = None
        if 'temperature.si-value' in kimquery:
            self.temperature = kimquery['temperature.si-value']
        if 'cohesive-potential-energy.si-value' in kimquery:
            self.cohesivepot = kimquery['cohesive-potential-energy.si-value']
            if self.temperature:
                if not isinstance(self.temperature, list):
                    if float(self.temperature) > 0:
                        zeroTemp = False
                    else:
                        zeroTemp = True
            if isinstance(self.cohesivepot, list):
                backend.addValue("energy_total", float(self.cohesivepot[int(step)]))
                backend.addValue("energy_potential", float(self.cohesivepot[int(step)]))
                if zeroTemp:
                    backend.addValue("energy_total_T0", float(self.cohesivepot[int(step)]))
            else:
                backend.addValue("energy_total", float(self.cohesivepot))
                backend.addValue("energy_potential", float(self.cohesivepot))
                if zeroTemp:
                    backend.addValue("energy_total_T0", float(self.cohesivepot))
        if 'cauchy-stress.si-value' in kimquery:
            cstress = kimquery['cauchy-stress.si-value']
            f = np.zeros((3,3))
            f[0][0] = float(cstress[0])
            f[1][1] = float(cstress[1])
            f[2][2] = float(cstress[2])
            f[1][2] = float(cstress[3])
            f[0][2] = float(cstress[4])
            f[0][1] = float(cstress[5])
            backend.addArrayValues("stress_tensor", np.asarray(f))

class KIMParser(object):
    @staticmethod
    def maybeGet(el, meta, default = None):
        if meta in el:
            return el[meta]
        else:
            return default

    def __init__(self, parserInfo, superContext):
        self.fIn = None
        self.parserInfo = parserInfo
        self.superContext = superContext
        self.gidSections = {}

    def parse(self, mainFileUri, fIn, backend):
        self.mainFileUri = mainFileUri
        self.fIn = fIn
        self.backend = backend
        backend.startedParsingSession(
            mainFileUri = mainFileUri,
            parserInfo = self.parserInfo)
        superContext = self.superContext
        superContext.startedParsing(self)
        QueryList = KIMQueryReader(self.fIn)
        try:
            for qi, qdict in enumerate(QueryList):
                superContext.reset()
                with open_section(self, backend, 'section_run'):
                    superContext.onEnd_program(self, qdict)
                    with open_section(self, backend, 'x_openkim_section_metadata'):
                        superContext.onEnd_openkim_data(self, qdict)
                    if 'a.si-value' in qdict or 'a-host.si-value' in qdict:
                        if isinstance(qdict['a.si-value'], list):
                            for step in qdict['a.si-value']:
                                with open_section(self, backend, 'section_single_configuration_calculation'):
                                    superContext.singleConfCalcs.append(self.gidSections[
                                        "section_single_configuration_calculation"])
                                    with open_section(self, backend, 'section_system'):
                                        superContext.onEnd_structure(self, qdict, step)
                                    superContext.onEnd_calculation(self, qdict, step)
                        else:
                            with open_section(self, backend, 'section_single_configuration_calculation'):
                                superContext.singleConfCalcs.append(self.gidSections[
                                    "section_single_configuration_calculation"])
                                with open_section(self, backend, 'section_system'):
                                    superContext.onEnd_structure(self, qdict)
                                superContext.onEnd_calculation(self, qdict)
                    superContext.onEnd_model(self, qdict)
        except:
            logging.exception("failure when parsing %s", self.mainFileUri)
            backend.finishedParsingSession(
                parserStatus = "ParseFailure",
                parserErrors = ["exception: %s" % sys.exc_info()[1]]
            )
        else:
            backend.finishedParsingSession(
                parserStatus = "ParseSuccess",
                parserErrors = None
            )

g = KIMParser.maybeGet

parserInfo = {
  "name": "parser_openkim",
  "version": "1.0"
}


class OpenKIMParser():
   """ A proper class envolop for running this parser from within python. """
   def __init__(self, backend, **kwargs):
       self.backend_factory = backend

   def parse(self, mainfile):
       logging.info('turbomole parser started')
       logging.getLogger('nomadcore').setLevel(logging.WARNING)
       backend = self.backend_factory("openkim.nomadmetainfo.json")
       parserInfo = {'name': 'parser_openkim', 'version': '1.0'}
       context = OpenkimContext()
       parser = KIMParser(parserInfo, context)
       parser.parse('nmd://uri', mainfile, backend)

       return backend
