#!/usr/bin/env python

import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

def readme():
	with open('README.md') as f:
		return f.read()

setup(name='octvi',
		version='1.0.0',
		description='MODIS 8-day NDVI Downloader',
		long_description=readme(),
		author="F. Dan O'Neill",
		author_email='fdfoneill@gmail.com',
		license='MIT',
		packages=['octvi'],
		include_package_data=True,
		# third-party dependencies
		install_requires=[
			'numpy',
			'h5py',
			'gdal'
			],
		zip_safe=False
		)