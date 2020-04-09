# MIT License
# 
# Copyright (c) [year] [fullname]
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

###################################################################################

# Author: F. Dan O'Neill
# Date: 12/06/2019
# Description: Module for the downloading and processing of 8-day NDVI data from MODIS and VIIRS

###################################################################################

from ._version import __version__

## set up logging
import logging, os
logging.basicConfig(level=os.environ.get("LOGLEVEL","INFO"))
log = logging.getLogger(__name__)


import octvi.exceptions, octvi.array, octvi.extract, octvi.url
from octvi.url import supported_products
from octvi.array import supported_indices
import configparser, gdal, shutil, subprocess
from datetime import datetime, timedelta
from urllib.request import HTTPError


__all__ = [
			'exceptions',
			'array',
			'extract',
			'url'
			]

configFile = os.path.join(os.path.dirname(os.path.dirname(__file__)),"etc/config.ini")
try:
	config = configparser.ConfigParser()
	config.read(configFile)
	app_key = config['NASA']['app_key']
except:
	log.warning("No app key found in config file; downloading will be unavailable. Run `octviconfig` from the command line.\nInformation on app keys can be found at https://ladsweb.modaps.eosdis.nasa.gov/tools-and-services/data-download-scripts/#appkeys")

def mosaic(in_files:list,out_path:str) -> str:
	"""
	This function takes a list of input raster files, and uses
	a gdal VRT to create a mosaic of all the inputs. This mosaic
	is then saved to the output location specified by out_path,
	as a single raster file.

	Note that global 250/500-m scale mosaics are large files, and
	a single image may be more than 2 GB in size. Make sure that 
	there is sufficient disk space before calling this function.

	Return value is the string passed to 'out_path'

	...

	Parameters
	----------

	in_files: list
		A list of string paths to the raster files to be mosaicked
	out_path: str
		The full path to a mosaic raster file to be created
	"""

	## define intermediate raster name
	ext = os.path.splitext(out_path)[1]
	intermediate_path = out_path.replace(ext,".vrt")
	interim_path = out_path.replace(ext,f".TEMP{ext}")

	## build the vrt command line call
	# subsetting to dimensions of mhumber's MOD13Q1 files
	north= 8895604.157#9962342# 9972315.0495 * 0.999
	west= -20015109.354#-22735470# -22758229.000 * 0.999
	south = -6671703.118#-9143189# -9152341.5816 * 0.999
	east= 20015109.354#20958445# 20979424.893 * 0.999
	command = ["gdalbuildvrt","-te",str(west),str(south),str(east),str(north),'-q',intermediate_path] # gdal script and output file
	#command = ["gdalbuildvrt",intermediate_path] # gdal script and output file
	command += in_files # append the list of input files


	## build the vrt
	subprocess.call(command)

	## save vrt to output file location, clipped to sinusoidal bounds
	subprocess.call(["gdal_translate","-co", "TILED=YES",'-co',"COPY_SRC_OVERVIEWS=YES",'-co', "COMPRESS=DEFLATE",'-q', intermediate_path,out_path])

	## remove intermediate file
	os.remove(intermediate_path)
	try: # try removing vrt.ovr
		os.remove(intermediate_path+".ovr")
	except: # if it doesn't exist, oh well
		pass

	# copy to interim path
	with open(out_path,'rb') as rf:
		with open(interim_path,'wb') as wf:
			shutil.copyfileobj(rf,wf)

	# delete nodata from file
	ds = gdal.Open(interim_path,1)
	for i in range(ds.RasterCount):
		ds.GetRasterBand(i + 1).DeleteNoDataValue()
	ds = None

	## add overviews to file
	subprocess.call(["gdaladdo",interim_path, "2", "4", "8", "16", "32", "64", "128", "256", "512", "1024"])

	# put nodata back on file
	ds =  gdal.Open(interim_path,1)
	for i in range(ds.RasterCount):
		ds.GetRasterBand(i + 1).SetNoDataValue(-3000)
	ds = None

	# copy back to out_path
	subprocess.call(["gdal_translate","-co", "TILED=YES",'-co',"COPY_SRC_OVERVIEWS=YES",'-co', "COMPRESS=DEFLATE",'-q', interim_path,out_path])

	# delete interim_path
	os.remove(interim_path)

	return out_path


def modCmgVi(date,out_path:str,overwrite=False,vi="NDVI",snow_mask=True) -> str:
	"""
	This function produces an 8-day composite VI image
	at cmg scale (MOD09CMG), beginning on the provided date
	
	***

	Parameters
	----------
	date:str
		Start date in format "%Y-%m-%d"
	out_path:str
		Full path to output file location on disk
	overwrite:bool
		Whether to allow overwriting of existing file on disk.
		Default: False
	vi:str
		What Vegetation Index type should be calculated. Default
		"NDVI", valid options ["NDVI","GCVI"]
	snow_mask:bool
		If True (default), masks out snow- and ice-flagged pixels.
	"""

	if vi not in supported_indices:
		raise octvi.exceptions.UnsupportedError(f"Vegetation index '{vi}' not recognized or not supported.")

	if os.path.exists(out_path) and overwrite == False:
		raise FileExistsError(f"{out_path} already exists. To overwrite file, set 'overwrite=True'.")

	working_directory = os.path.dirname(out_path)

	log.info("Fetching dates")
	## build list of eight days in compositing period
	# each date is a datetime object
	dates = [datetime.strptime(date,"%Y-%m-%d")]
	while len(dates) < 8:
		dates.append(dates[-1] + timedelta(days=1))

	## download all hdfs and record their paths
	log.info(f"Downloading daily {vi} files")
	hdfs = []
	try:
		for dobj in dates:
			d = dobj.strftime("%Y-%m-%d")
			log.debug(d)
			try:
				url = octvi.url.getUrls("MOD09CMG",d)[0][0]
				hdfs.append(octvi.url.pull(url,working_directory))
			except octvi.exceptions.UnavailableError:
				log.error("HTTPError from LADS DAAC; retrying from LP DAAC")
				url = octvi.url.getUrls("MOD09CMG",d,lads_or_lp="LP")[0][0]
				hdfs.append(octvi.url.pull(url,working_directory))
		
		## create ideal ndvi array
		log.info("Creating composite")
		ndviArray = octvi.extract.cmgBestViPixels(hdfs,snow_mask=snow_mask)

		## write to disk
		octvi.array.toRaster(ndviArray,out_path,hdfs[0])

		## project to WGS84
		ds = gdal.Open(out_path,1)
		if ds:
			res = ds.SetProjection('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
			if res != 0:
				logging.error("--projection failed: {}".format(str(res)))
			ds = None
		else:
			logging.error("--could not open with GDAL")
	finally:
		## delete hdfs
		for hdf in hdfs:
			os.remove(hdf)
	return out_path


def vnpCmgVi(date,out_path:str,overwrite=False,vi="NDVI",snow_mask=True) ->str:
	"""
	This function produces an 8-day composite VI image
	at cmg scale (VNP09CMG), beginning on the provided date
	
	***

	Parameters
	----------
	date:str
		Start date in format "%Y-%m-%d"
	out_path:str
		Full path to output file location on disk
	overwrite:bool
		Whether to allow overwriting of existing file on disk.
		Default: False
	vi:str
		What Vegetation Index type should be calculated. Default
		"NDVI", valid options ["NDVI","GCVI"]
	snow_mask:bool
		If True (default), masks out snow- and ice-flagged pixels.
	"""
	if vi not in supported_indices:
		raise octvi.exceptions.UnsupportedError(f"Vegetation index '{vi}' not recognized or not supported.")

	if os.path.exists(out_path) and overwrite == False:
		raise FileExistsError(f"{out_path} already exists. To overwrite file, set 'overwrite=True'.")

	working_directory = os.path.dirname(out_path)

	log.info("Fetching dates")
	## build list of eight days in compositing period
	# each date is a datetime object
	dates = [datetime.strptime(date,"%Y-%m-%d")]
	while len(dates) < 8:
		dates.append(dates[-1] + timedelta(days=1))

	## download all hdf5s and record their paths
	log.info(f"Downloading daily {vi} files")
	h5s = []
	try:
		for dobj in dates:
			d = dobj.strftime("%Y-%m-%d")
			log.debug(d)
			try:
				url = octvi.url.getUrls("VNP09CMG",d)[0][0]
				h5s.append(octvi.url.pull(url,working_directory))
			except octvi.exceptions.UnavailableError:
				log.error("HTTPError from LADS DAAC; retrying from LP DAAC")
				url = octvi.url.getUrls("VNP09CMG",d,lads_or_lp="LP")[0][0]
				h5s.append(octvi.url.pull(url,working_directory))

		## create ideal ndvi array
		log.info("Creating composite")
		ndviArray = octvi.extract.cmgBestViPixels(h5s,product="VNP09CMG",snow_mask=snow_mask)
		## write to disk
		octvi.array.toRaster(ndviArray,out_path,h5s[0])

		## project to WGS84
		ds = gdal.Open(out_path,1)
		if ds:
			res = ds.SetProjection('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]')
			if res != 0:
				logging.error("--projection failed: {}".format(str(res)))
			ds = None
		else:
			logging.error("--could not open with GDAL")
	finally:
		## delete hdfs
		for h5 in h5s:
			os.remove(h5)
	return out_path


def globalVi(product,date,out_path:str,overwrite=False,vi="NDVI",cmg_snow_mask=True) -> str:
	"""
	This function takes the name of an imagery product, observation date,
	and a vegetation index, and creates a global mosaic of the given
	product's VI on that date.

	Returns the path to the output file.

	...

	Parameters
	----------

	product: str
		Name of imagery product; e.g. "MOD09Q1"
	date: str
		Date in format "%Y-%m-%d"
	out_path: str
		Full path to location where output file will be saved; e.g. "C:/temp/output.tif"
	overwrite: bool
		Default False, whether to overwrite existing file at out_path
	vi: str
		Default "NDVI", valid ["NDVI", "GCVI"]
	cmg_snow_mask:bool
		Implemented only for CMG-scale imagery. If set to True, masks out snow- and 
		ice-flagged pixels.
	"""

	startTime = datetime.now()

	if product not in supported_products:
		raise octvi.exceptions.UnsupportedError(f"Product '{product}' is not currently supported. See octvi.supported_products for list of supported products.")

	if vi not in supported_indices:
		raise octvi.exceptions.UnsupportedError(f"Vegetation index '{vi}' not recognized or not supported.")

	if os.path.exists(out_path) and overwrite == False:
		raise FileExistsError(f"{out_path} already exists. To overwrite file, set 'overwrite=True'.")

	working_directory = os.path.dirname(out_path)

	if product[5:8] == "CMG":
		if product[0] == "M":
			modCmgVi(date,out_path,overwrite=overwrite,vi=vi,snow_mask=cmg_snow_mask)
		elif product[0] == "V":
			vnpCmgVi(date,out_path,overwrite=overwrite,vi=vi,snow_mask=cmg_snow_mask)
	elif vi == "GCVI":
		raise octvi.exceptions.UnsupportedError("Only CMG-scale imagery is supported for GCVI generation")
	else:
		log.info("Fetching urls")
		tiles = octvi.url.getUrls(product,date)
		log.info(f"Building {vi} tiles")
		ndvi_files = []
		try:
			for tile in tiles:
				#if tile[1][-2:] in ["00","01","16","17"]:
					#log.info(f"skipping {tile[1]}")
					#continue
				log.debug(tile[1])
				url = tile[0]
				try:
					hdf_file = octvi.url.pull(url,working_directory,retries=8)
				except octvi.exceptions.UnavailableError:
					log.error("Unavailable from LADS DAAC; trying from LP DAAC")
					url = octvi.url.getUrls(product,date,tiles=tile[1],lads_or_lp="LP")[0][0]
					hdf_file = octvi.url.pull(url,working_directory)
				ext = os.path.splitext(hdf_file)[1]
				ndvi_files.append(octvi.extract.ndviToRaster(hdf_file,hdf_file.replace(ext,".ndvi.tif")))
				os.remove(hdf_file)
			log.info("Creating mosaic")
			mosaic(ndvi_files,out_path)

		## remove indiviual HDFs
		finally:
			for f in ndvi_files:
				os.remove(f)

	endTime = datetime.now()
	log.info(f"Done. Elapsed time {endTime-startTime}")
	return out_path


def cmgNdvi(date,out_path:str,overwrite=False,snow_mask=False) -> str:
	"""
	This function produces an 8-day composite NDVI image
	at cmg scale (MOD09CMG), beginning on the provided date
	
	***

	Parameters
	----------
	date:str
		Start date in format "%Y-%m-%d"
	out_path:str
		Full path to output file location on disk
	overwrite:bool
		Whether to allow overwriting of existing file on disk.
		Default: False
	"""
	log.warning("cmgNdvi() is deprecated as of octvi 1.1.0. Use cmgVi() instead")
	return modCmgVi(date,out_path,overwrite=overwrite,vi="NDVI",snow_mask=snow_mask)


def globalNdvi(product,date,out_path:str,overwrite=False) -> str:
	"""
	This function takes the name of an imagery product and an
	observation date, and creates a global mosaic of the given
	product's NDVI on that date.

	Returns the path to the output file.

	...

	Parameters
	----------

	product: str
		Name of imagery product; e.g. "MOD09Q1"
	date: str
		Date in format "%Y-%m-%d"
	out_path: str
		Full path to location where output file will be saved; e.g. "C:/temp/output.tif"
	overwrite: bool
		Default False, whether to overwrite existing file at out_path
	"""
	log.warning("globalNdvi() is deprecated as of octvi 1.1.0. Use globalVi() instead.")
	return globalVi(product,date,out_path,overwrite,"NDVI")