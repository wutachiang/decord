#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, platform, sysconfig
import shutil
import glob

from setuptools import find_packages
from setuptools.dist import Distribution

# need to use distutils.core for correct placement of cython dll
if '--inplace' in sys.argv:
    from distutils.core import setup
    from distutils.extension import Extension
else:
    from setuptools import setup
    from setuptools.extension import Extension

class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return platform.system() == 'Darwin'

CURRENT_DIR = os.path.dirname(__file__)

def get_lib_path():
    """Get library path, name and version"""
     # We can not import `libinfo.py` in setup.py directly since __init__.py
    # Will be invoked which introduces dependences
    libinfo_py = os.path.join(CURRENT_DIR, './decord/_ffi/libinfo.py')
    libinfo = {'__file__': libinfo_py}
    exec(compile(open(libinfo_py, "rb").read(), libinfo_py, 'exec'), libinfo, libinfo)
    version = libinfo['__version__']

    lib_path = libinfo['find_lib_path']()
    libs = [lib_path[0]]

    return libs, version

LIBS, VERSION = get_lib_path()

def config_cython():
    """Try to configure cython and return cython configuration"""
    if os.name == 'nt':
        print("WARNING: Cython is not supported on Windows, will compile without cython module")
        return []
    sys_cflags = sysconfig.get_config_var("CFLAGS")

    if "i386" in sys_cflags and "x86_64" in sys_cflags:
        print("WARNING: Cython library may not be compiled correctly with both i386 and x64")
        return []
    try:
        from Cython.Build import cythonize
        # from setuptools.extension import Extension
        if sys.version_info >= (3, 0):
            subdir = "_cy3"
        else:
            subdir = "_cy2"
        ret = []
        path = "decord/_ffi/_cython"
        if os.name == 'nt':
            library_dirs = ['decord', '../build/Release', '../build']
            libraries = ['libtvm']
        else:
            library_dirs = None
            libraries = None
        for fn in os.listdir(path):
            if not fn.endswith(".pyx"):
                continue
            ret.append(Extension(
                "decord._ffi.%s.%s" % (subdir, fn[:-4]),
                ["decord/_ffi/_cython/%s" % fn],
                include_dirs=["../include/",
                              "../third_party/dmlc-core/include",
                              "../third_party/dlpack/include",
                ],
                library_dirs=library_dirs,
                libraries=libraries,
                language="c++"))
        return cythonize(ret)
    except ImportError:
        print("WARNING: Cython is not installed, will compile without cython module")
        return []

include_libs = False
wheel_include_libs = False
if "bdist_wheel" in sys.argv or os.getenv('CONDA_BUILD'):
    wheel_include_libs = True
else:
    include_libs = True

setup_kwargs = {}

# For bdist_wheel only
if wheel_include_libs:
    with open("MANIFEST.in", "w") as fo:
        for path in LIBS:
            shutil.copy(path, os.path.join(CURRENT_DIR, 'decord'))
            _, libname = os.path.split(path)
            fo.write("include decord/%s\n" % libname)
    setup_kwargs = {
        "include_package_data": True
    }

# For source tree setup
# Conda build also includes the binary library
if include_libs:
    rpath = [os.path.relpath(path, CURRENT_DIR) for path in LIBS]
    setup_kwargs = {
        "include_package_data": True,
        "data_files": [('decord', rpath)]
    }

setup(
    name='decord',
    version=VERSION,
    description='Decord Video Loader',
    zip_safe=False,
    maintainer='Decord commiters',
    maintainer_email='cheungchih@gmail.com',
    packages=find_packages(),
    install_requires=[
        'numpy>=1.14.0',
    ],
    url='https://github.com/zhreshold/decord',
    distclass=BinaryDistribution,
    ext_modules=config_cython(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
    ],
    license='APACHE',
    **setup_kwargs
)

if wheel_include_libs:
    # Wheel cleanup
    os.remove("MANIFEST.in")
    for path in LIBS:
        _, libname = os.path.split(path)
        os.remove("decord/%s" % libname)
