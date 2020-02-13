## set up logging
import logging, os
logging.basicConfig(level=os.environ.get("LOGLEVEL","INFO"))
log = logging.getLogger(__name__)

import gdal, h5py, octvi.extract
import numpy as np
from gdalnumeric import *

supported_indices = ["NDVI","GCVI"]

def calcNdvi(red_array,nir_array) -> "numpy array":
	"""
	A function to robustly build an NDVI array from two
	arrays (red and NIR) of the same shape.

	Resulting array is scaled by 10000, with values stored
	as integers. Nodata value is -3000.

	...

	Parameters
	----------

	red_array: numpy.array
		Array of red reflectances
	nir_array: numpy.array
		Array of near-infrared reflectances

	"""

	## perform NDVI generation
	ndvi = np.divide((nir_array - red_array),(nir_array + red_array))

	## rescale and replace infinities
	ndvi = ndvi * 10000
	ndvi[ndvi == np.inf] = -3000
	ndvi[ndvi == -np.inf] = -3000
	ndvi = ndvi.astype(int)

	## return array
	return ndvi

def calcGcvi(green_array,nir_array) -> "numpy array":
	"""
	A function to robustly build a GCVI array from two
	arrays (green and NIR) of the same shape.

	Resulting array is scaled by 10000, with values stored
	as integers. Nodata value is -3000.

	...

	Parameters
	----------

	green_array: numpy.array
		Array of green reflectances
	nir_array: numpy.array
		Array of near-infrared reflectances

	"""

	## perform NDVI generation
	gcvi = np.divide(nir_array, green_array) - 1

	## rescale and replace infinities
	gcvi = gcvi * 10000
	gcvi[gcvi == np.inf] = -3000
	gcvi[gcvi == -np.inf] = -3000
	gcvi = gcvi.astype(int)

	## return array
	return gcvi

def mask(in_array, source_stack) -> "numpy array":
	"""
	This function removes non-clear pixels from an input array,
	including clouds, cloud shadow, and water.

	For M*D CMG files, removes only nodata pixels

	Returns a cleaned array.

	...

	Parameters
	----------

	in_array: numpy.array
		The array to be cleaned. This must have the same dimensions
		as source_stack, and preferably have been extracted from the
		stack.
	source_stack: str
		Path to a hierarchical data file containing QA layers with
		which to perform the masking. Currently valid formats include
		MOD09Q1 hdf and VNP09H1 files.
	"""

	## get file extension and product suffix
	ext = os.path.splitext(source_stack)[1]
	suffix = os.path.basename(source_stack).split(".")[0][3:7]

	## product-conditional behavior

	# MODIS pre-generated VI masking
	if suffix == "13Q1" or suffix == "13Q4":
		if suffix[-1] == "1":
			pr_arr = octvi.extract.datasetToArray(source_stack, "250m 16 days pixel reliability")
			#qa_arr = octvi.extract.datasetToArray(source_stack, "250m 16 days VI Quality")
		else:
			pr_arr = octvi.extract.datasetToArray(source_stack, "250m 8 days pixel reliability")
			#qa_arr = octvi.extract.datasetToArray(source_stack, "250m 8 days VI Quality")
	

		in_array[pr_arr != 0] = -3000

	# MODIS and VIIRS surface reflectance masking
	else:
		# modis
		if suffix == "09CM":
			qa_arr = octvi.extract.datasetToArray(source_stack,"Coarse Resolution QA")
			state_arr = octvi.extract.datasetToArray(source_stack,"Coarse Resolution State QA")
		elif ext == ".hdf": 
			qa_arr = octvi.extract.datasetToArray(source_stack, "sur_refl_qc_250m")
			state_arr = octvi.extract.datasetToArray(source_stack,"sur_refl_state_250m")

		# viirs
		elif ext == ".h5":
			qa_arr = octvi.extract.datasetToArray(source_stack, "SurfReflect_QC_500m")
			state_arr = octvi.extract.datasetToArray(source_stack,"SurfReflect_State_500m")

		else:
			raise octvi.exceptions.FileTypeError("File must be of format .hdf or .h5")

		## mask clouds
		in_array[(state_arr & 0b11) != 0 ] = -3000
		in_array[(state_arr & 0b10000000000) != 0] = -3000 # internal cloud mask

		## mask cloud shadow
		in_array[(state_arr & 0b100) != 0] = -3000

		## mask cloud adjacent pixels
		in_array[(state_arr & 0b10000000000000) != 0] = -3000

		## mask aerosols
		in_array[(state_arr & 0b11000000) != 64] = -3000

		## mask snow/ice
		in_array[(state_arr & 0b1000000000000) != 0] = -3000

		## mask water
		in_array[((state_arr & 0b111000) != 8) & ((state_arr & 0b111000) != 16) & ((state_arr & 0b111000) !=32)] = -3000 # checks against three 'allowed' land/water classes and excludes pixels that don't match

		## mask bad solar zenith
		#in_array[(qa_arr & 0b11100000) != 0] = -3000


	## return output
	return in_array

def toRaster(in_array,out_path,model_file,dtype = None) -> None:
	"""
	This function saves a numpy array into a raster file, with
	the same project and extents as the provided model file.

	As implemented, this function works ONLY for arrays that can
	be coerced to Int16 type.

	...

	Parameters
	----------

	in_array: numpy.array
		The array to be written to disk
	out_path: str
		Full path to raster file where the output will be written
	model_file: str
		Existing raster file with matching spatial reference and geotransform

	"""

	## extract extent, geotransform, and projection
	refDs = gdal.Open(model_file,0)
	sr = refDs.GetProjection() # as WKT
	# viirs won't tell you its projection
	if sr == '':
		sr = 'PROJCS["unnamed",GEOGCS["Unknown datum based upon the custom spheroid",DATUM["Not specified (based on custom spheroid)",SPHEROID["Custom spheroid",6371007.181,0]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Sinusoidal"],PARAMETER["longitude_of_center",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["Meter",1]]'
	geoTransform = refDs.GetGeoTransform()
	# viirs won't tell you its geotransform
	if geoTransform[1] == 1.0:
		if os.path.splitext(model_file)[1] == ".h5":
			pixelSize = 463.3127165
			# use h5py
			refDs = h5py.File(model_file.split("\"")[1],mode='r') # open file in read-only mode
			fileMetadata = refDs['HDFEOS INFORMATION']['StructMetadata.0'][()].split() # grab metadata
			fileMetadata = [m.decode('utf-8') for m in fileMetadata] # decode UTF
			ulc = [i for i in fileMetadata if 'UpperLeftPointMtrs' in i][0]    # Search file metadata for the upper left corner of the file
			ulcLon = float(ulc.split('=(')[-1].replace(')', '').split(',')[0]) # Parse metadata string for upper left corner lon value
			ulcLat = float(ulc.split('=(')[-1].replace(')', '').split(',')[1]) # Parse metadata string for upper left corner lat value
			geoTransform = (ulcLon, pixelSize, 0.0, ulcLat, 0.0, -pixelSize)
		elif os.path.splitext(model_file)[1] == ".hdf":
			ds_sub = gdal.Open(refDs.GetSubDatasets()[0][0])
			geoTransform = ds_sub.GetGeoTransform()
			sr = ds_sub.GetProjection()
	rasterYSize, rasterXSize = in_array.shape
	refDs = None

	## parse datatype
	typeTable = {"Byte":gdal.GDT_Byte,"Int16":gdal.GDT_Int16,"Int32":gdal.GDT_Int32,"Float32":gdal.GDT_Float32,"Float64":gdal.GDT_Float64}
	outType = typeTable.get(dtype,gdal.GDT_Int16)

	## write to disk
	driver = gdal.GetDriverByName('GTiff')
	dataset = driver.Create(out_path,rasterXSize,rasterYSize,1,outType,['COMPRESS=DEFLATE'])
	dataset.GetRasterBand(1).WriteArray(in_array)
	dataset.GetRasterBand(1).SetNoDataValue(-3000)
	dataset.SetGeoTransform(geoTransform)
	dataset.FlushCache() # Write to disk
	del dataset

	## project
	ds = gdal.Open(out_path,1)
	if ds:
		res = ds.SetProjection(sr)
		if res != 0:
			log.error("--projection failed: {}".format(str(res)))
		ds = None
	else:
		log.error("--could not open with GDAL")

	return None