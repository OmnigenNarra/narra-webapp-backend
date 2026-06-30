#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Setup script
'''

from os import path

from setuptools import setup, find_packages


BASE_PATH = path.abspath(path.dirname(__file__))


setup(
    name='narra_backend',

    version='0.0.3',

    description='Narra backend app',
    long_description='Narra backend app (API, accounts etc.)',

    author='Narra',
    author_email='projekt@narra.pl',

    url='https://bitbucket.org/to_reforge/narra-webapp-backend',

    license='MIT License',

    keywords=['narra', 'gaming', 'unreal', 'unity'],

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

    packages=find_packages(),

    include_package_data=True,

    zip_safe=True,

    install_requires=open(path.join(BASE_PATH, 'requirements.txt')).readlines(),
)
