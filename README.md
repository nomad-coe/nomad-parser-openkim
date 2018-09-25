# OpenKIM Parser
[NOMAD Laboratory CoE](http://nomad-coe.eu) parser for [OpenKIM](https://openkim.org)
## Version 0.0.1

This is the parser for OpenKIM queries at [OpenKIM](https://openkim.org).
The official version lives at:

    git@gitlab.mpcdf.mpg.de:nomad-lab/parser-openkim.git

You can browse it at:

    https://gitlab.rzg.mpg.de/nomad-lab/parser-openkim

It relies on having the nomad-meta-info and the python-common repositories one level higher.
The simplest way to have this is to check out nomad-lab-base recursively:

    git clone --recursive git@gitlab.mpcdf.mpg.de:nomad-lab/nomad-lab-base.git

This parser will be in the directory parsers/openkim of this repository.

## Running and Testing the Parser
### Requirements
The required python packages can be installed with (see [python-common](https://gitlab.rzg.mpg.de/nomad-lab/python-common)):

    pip install -r nomad-lab-base/python-common/requirements.txt

### Usage
The query output of OpenKIM simulation results can be parsed with:

    python parser-openkim.py test_nomad_id openkim_query_data.json

### Test Files
Example log output files of OpenKIM query can be found in the directory test/examples.
More details about the calculations and files are explained in README file of test/examples.

