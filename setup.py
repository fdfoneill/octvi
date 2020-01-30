#!/usr/bin/env python

import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent


setup(name='octvi',
		version='1.0.0',
		description='MODIS 8-day NDVI Downloader',
		author="F. Dan O'Neill",
		author_email='fdfoneill@gmail.com',
		license='MIT',
		packages=find_packages(),
		include_package_data=True,
		# third-party dependencies
		install_requires=[
						'csv',
						'datetime',
						'gdal',
						'h5py',
						'io',
						'logging',
						'numpy',
						'shutil',
						'ssl',
						'subprocess',
						'urllib'
						],
		entry_points={}
	  )