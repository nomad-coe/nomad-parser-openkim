import sys
import os
import os.path

basedir = os.path.dirname(os.path.abspath(__file__))
commondir = os.path.normpath(os.path.join(basedir,"../../../../python-common/common/python"))
parserdir = os.path.normpath(os.path.join(basedir, ".."))

if commondir not in sys.path:
    sys.path.insert(1, commondir)
if parserdir not in sys.path:
    sys.path.insert(1, parserdir)
