# input-encoding: latin-1
from __future__ import print_function

# windows ?
import sys
iswin = sys.platform == "win32"

# import config
from env import (QT_QMAKE_VERSION_INFO, QT_LIBRARY_DIR, OPEN_MS_BUILD_TYPE, OPEN_MS_SRC,
                 OPEN_MS_CONTRIB_BUILD_DIRS, OPEN_MS_LIB, OPEN_SWATH_ALGO_LIB, SUPERHIRN_LIB,
                 OPEN_MS_BUILD_DIR, MSVS_RTLIBS, OPEN_MS_VERSION, Boost_MAJOR_VERSION, Boost_MINOR_VERSION)

IS_DEBUG = OPEN_MS_BUILD_TYPE.upper() == "DEBUG"

if iswin and IS_DEBUG:
    raise Exception("building pyopenms on windows in debug mode not tested yet.")

# use autowrap to generate Cython and .cpp file for wrapping OpenMS:
import autowrap.Main
import glob
import pickle
import os.path
import os
import shutil
import time

j = os.path.join

if iswin:
  # copy stuff
  try:
    shutil.copy(j(OPEN_MS_BUILD_DIR, "src", "openswathalgo", "OpenSwathAlgo.lib"), j(OPEN_MS_BUILD_DIR, "bin"))
    shutil.copy(j(OPEN_MS_BUILD_DIR, "src", "openms", "OpenMS.lib"), j(OPEN_MS_BUILD_DIR, "bin"))
    shutil.copy(j(OPEN_MS_BUILD_DIR, "src", "superhirn", "SuperHirn.lib"), j(OPEN_MS_BUILD_DIR, "bin"))
  except IOError:
    pass
	
src_pyopenms = j(OPEN_MS_SRC, "src/pyOpenMS")
pxd_files = glob.glob(src_pyopenms + "/pxds/*.pxd")
addons = glob.glob(src_pyopenms + "/addons/*.pyx")
converters = [j(src_pyopenms, "converters")]


persisted_data_path = "include_dir.bin"

extra_cimports = [  # "from libc.stdint cimport *",
    #"from libc.stddef cimport *",
    #"from UniqueIdInterface cimport setUniqueId as _setUniqueId",
    #"from Map cimport Map as _Map",
    #"cimport numpy as np"
]

decls, instance_map = autowrap.parse(pxd_files, ".")
# add __str__ if toString() method is declared:
for d in decls:
    # enums, free functions, .. do not have a methods attribute
    methods = getattr(d, "methods", dict())
    to_strings = []
    for name, mdecls in methods.items():
        for mdecl in mdecls:
            name = mdecl.cpp_decl.annotations.get("wrap-cast", name)
            name = mdecl.cpp_decl.annotations.get("wrap-as", name)
            if name == "toString":
                to_strings.append(mdecl)

    for to_string in to_strings:
        if len(to_string.arguments) == 0:
            d.methods.setdefault("__str__", []).append(to_string)
            print("ADDED __str__ method to", d.name)
            break

autowrap_include_dirs = autowrap.Main.create_wrapper_code(decls, instance_map, addons,
                                                          converters, out="pyopenms/pyopenms.pyx",
                                                          extra_inc_dirs=extra_cimports,
                                                          extra_opts=None, include_boost=False)

pickle.dump(autowrap_include_dirs, open(persisted_data_path, "wb"))

#
# Fix two bugs in the cpp code generated by Cython to allow error-free
# compilation (see OpenMS issues on github #527 and #745).
#
import re
f = open("pyopenms/pyopenms.cpp")
fout = open("pyopenms/pyopenms_out.cpp", "w")
expr_fix = re.compile(r"(.*).std::vector<(.*)>::iterator::~iterator\(\)")
for line in f:
    # Fix for Issue #527
    res = expr_fix.sub('typedef std::vector<\\2>::iterator _it;\n\\1.~_it()', line)
    # Fix for Issue #745
    res = res.replace("__Pyx_PyUnicode_FromString(char", "__Pyx_PyUnicode_FromString(const char")
    fout.write(res)

fout.close()
f.close()
shutil.copy("pyopenms/pyopenms_out.cpp", "pyopenms/pyopenms.cpp")
os.remove("pyopenms/pyopenms_out.cpp")

print("created pyopenms.cpp")

# create version information
version = OPEN_MS_VERSION

print("version=%r\n" % version, file=open("pyopenms/version.py", "w"))
print("info=%r\n" % QT_QMAKE_VERSION_INFO, file=open("pyopenms/qt_version_info.py", "w"))

# parse config

if OPEN_MS_CONTRIB_BUILD_DIRS.endswith(";"):
    OPEN_MS_CONTRIB_BUILD_DIRS = OPEN_MS_CONTRIB_BUILD_DIRS[:-1]

for OPEN_MS_CONTRIB_BUILD_DIR in OPEN_MS_CONTRIB_BUILD_DIRS.split(";"):
    if os.path.exists(os.path.join(OPEN_MS_CONTRIB_BUILD_DIR, "lib")):
        break


if iswin:
    for libname in ["math", "regex"]:
        # fix for broken library names on Windows
        for p in glob.glob(os.path.join(OPEN_MS_CONTRIB_BUILD_DIR,
                                        "lib",
                                        "libboost_%s_*mt.lib" % libname)):

            # Copy for MSVS 2008 (vc90), MSVS 2010 (vc100) and MSVS 2015 (vc140)
            if "vc90" in p:
                continue
            if "vc100" in p:
                continue
            if "vc140" in p:
                continue
            new_p = p.replace("-mt.lib", "-vc90-mt-%s_%s.lib" % (Boost_MAJOR_VERSION, Boost_MINOR_VERSION))
            shutil.copy(p, new_p)
            new_p = p.replace("-mt.lib", "-vc100-mt-%s_%s.lib"% (Boost_MAJOR_VERSION, Boost_MINOR_VERSION))
            shutil.copy(p, new_p)			
            new_p = p.replace("-mt.lib", "-vc140-mt-%s_%s.lib"% (Boost_MAJOR_VERSION, Boost_MINOR_VERSION))
            shutil.copy(p, new_p)	


# Package data expected to be installed. On Linux the debian package
# contains share/ data and must be installed to get access to the OpenMS shared
# library.
#
if iswin:
    shutil.copy(OPEN_MS_LIB, "pyopenms")
    shutil.copy(OPEN_SWATH_ALGO_LIB, "pyopenms")
    shutil.copy(SUPERHIRN_LIB, "pyopenms")

    shutil.copy(MSVCR90DLL, "pyopenms")
    shutil.copy(MSVCP90DLL, "pyopenms")

    if OPEN_MS_BUILD_TYPE.upper() == "DEBUG":
        shutil.copy(j(QT_LIBRARY_DIR, "QtCored4.dll"), "pyopenms")
        shutil.copy(j(QT_LIBRARY_DIR, "QtGuid4.dll"), "pyopenms")
        shutil.copy(j(QT_LIBRARY_DIR, "QtSqld4.dll"), "pyopenms")
        shutil.copy(j(QT_LIBRARY_DIR, "QtNetworkd4.dll"), "pyopenms")
        shutil.copy(j(OPEN_MS_CONTRIB_BUILD_DIR, "lib", "xerces-c_3_1D.dll"),
                    "pyopenms")
    else:
        shutil.copy(j(QT_LIBRARY_DIR, "QtCore4.dll"), "pyopenms")
        shutil.copy(j(QT_LIBRARY_DIR, "QtGui4.dll"), "pyopenms")
        shutil.copy(j(QT_LIBRARY_DIR, "QtSql4.dll"), "pyopenms")
        shutil.copy(j(QT_LIBRARY_DIR, "QtNetwork4.dll"), "pyopenms")
        shutil.copy(j(OPEN_MS_CONTRIB_BUILD_DIR, "lib", "xerces-c_3_1.dll"),
                    "pyopenms")

elif sys.platform.startswith("linux"):

    shutil.copy(j(OPEN_MS_BUILD_DIR, "lib", "libOpenMS.so"), "pyopenms")
    shutil.copy(j(OPEN_MS_BUILD_DIR, "lib", "libSuperHirn.so"), "pyopenms")
    shutil.copy(j(OPEN_MS_BUILD_DIR, "lib", "libOpenSwathAlgo.so"), "pyopenms")

elif sys.platform == "darwin":

    shutil.copy(j(OPEN_MS_BUILD_DIR, "lib", "libOpenMS.dylib"), "pyopenms")
    shutil.copy(j(OPEN_MS_BUILD_DIR, "lib", "libSuperHirn.dylib"), "pyopenms")
    shutil.copy(j(OPEN_MS_BUILD_DIR, "lib", "libOpenSwathAlgo.dylib"), "pyopenms")
    shutil.copy(j(QT_LIBRARY_DIR, "QtCore.framework", "QtCore"), "pyopenms")
    shutil.copy(j(QT_LIBRARY_DIR, "QtNetwork.framework", "QtNetwork"), "pyopenms")

else:
    print("\n")
    print("platform", sys.platform, "not supported yet")
    print("\n")
    exit()

print("copied files needed for distribution to pyopenms/")
print("\n")

