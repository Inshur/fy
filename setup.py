
# -*- coding: utf-8 -*-

# DO NOT EDIT THIS FILE!
# This file has been autogenerated by dephell <3
# https://github.com/dephell/dephell

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

readme = ''

setup(
    long_description=readme,
    name='fycli',
    version='2.0.13',
    python_requires='==3.*,>=3.9.0',
    author='Rob Wilson',
    author_email='roobert@gmail.com',
    entry_points={"console_scripts": ["fy = fycli.__main__:main"]},
    packages=['fycli', 'fycli.environment', 'fycli.infra', 'fycli.kubernetes', 'fycli.skeleton', 'fycli.terraform', 'fycli.vault'],
    package_dir={"": "."},
    package_data={"fycli": ["*.txt"]},
    install_requires=['pyyaml==5.*,>=5.3.0', 'sh==1.*,>=1.12.14'],
    extras_require={"dev": ["black==20.*,>=20.8.0.b1"]},
)
