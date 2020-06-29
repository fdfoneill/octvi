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

	For M*D CMG files, removes pixels ranked below "8" in
	MOD13Q1 compositing method, as well as water.

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
			qa_arr = octvi.extract.datasetToArray(source_stack, "250m 16 days VI Quality")
		else:
			pr_arr = octvi.extract.datasetToArray(source_stack, "250m 8 days pixel reliability")
			qa_arr = octvi.extract.datasetToArray(source_stack, "250m 8 days VI Quality")
	

		in_array[(pr_arr != 0) & (pr_arr != 1)] = -3000

		# mask clouds
		in_array[(qa_arr & 0b11) > 1] = -3000 # bits 0-1 > 01 = Cloudy

		# mask Aerosol
		in_array[(qa_arr & 0b11000000) == 0] = -3000 # climatology
		in_array[(qa_arr & 0b11000000) == 192] = -3000 # high

		# mask water
		in_array[(qa_arr & 0b11100000000000) != 8] & in_array[(qa_arr & 0b11100000000000) != 16] & in_array[(qa_arr & 0b11100000000000) != 32] = -3000
		# 8 = land, 16 = coastline, 32 = ephemeral water

		# mask snow/ice
		in_array[(qa_arr & 0b100000000000000) != 0] = -3000 # bit 14

		# mask cloud shadow
		in_array[(qa_arr & 0b1000000000000000) != 0] = -3000 # bit 15

	# MODIS and VIIRS surface reflectance masking
	# CMG
	elif suffix == "09CM":
		if ext == ".hdf": # MOD09CMG
			qa_arr = octvi.extract.datasetToArray(source_stack,"Coarse Resolution QA")
			state_arr = octvi.extract.datasetToArray(source_stack,"Coarse Resolution State QA")
			vang_arr = octvi.extract.datasetToArray(source_stack,"Coarse Resolution View Zenith Angle")
			vang_arr[vang_arr<=0]=9999
			sang_arr = octvi.extract.datasetToArray(source_stack,"Coarse Resolution Solar Zenith Angle")
			rank_arr = np.full(qa_arr.shape,10) # empty rank array

			## perform the ranking!
			logging.debug("--rank 9: SNOW")
			SNOW = ((state_arr & 0b1000000000000) | (state_arr & 0b1000000000000000)) # state bit 12 OR 15
			rank_arr[SNOW>0]=9 # snow
			del SNOW
			logging.debug("--rank 8: HIGHAEROSOL")
			HIGHAEROSOL=(state_arr & 0b11000000) # state bits 6 AND 7
			rank_arr[HIGHAEROSOL==192]=8
			del HIGHAEROSOL
			logging.debug("--rank 7: CLIMAEROSOL")
			CLIMAEROSOL=(state_arr & 0b11000000) # state bits 6 & 7
			#CLIMAEROSOL=(cloudMask & 0b100000000000000) # cloudMask bit 14
			rank_arr[CLIMAEROSOL==0]=7 # default aerosol level
			del CLIMAEROSOL
			logging.debug("--rank 6: UNCORRECTED")
			UNCORRECTED = (qa_arr & 0b11) # qa bits 0 AND 1
			rank_arr[UNCORRECTED==3]=6 # flagged uncorrected
			del UNCORRECTED
			logging.debug("--rank 5: SHADOW")
			SHADOW = (state_arr & 0b100) # state bit 2
			rank_arr[SHADOW==4]=5 # cloud shadow
			del SHADOW
			logging.debug("--rank 4: CLOUDY")
			# set adj to 11 and internal to 12 to verify in qa output
			CLOUDY = ((state_arr & 0b11)) # state bit 0 OR bit 1 OR bit 10 OR bit 13
			#rank_arr[CLOUDY!=0]=4 # cloud pixel
			del CLOUDY
			CLOUDADJ = (state_arr & 0b10000000000000)
			#rank_arr[CLOUDADJ>0]=4 # adjacent to cloud
			del CLOUDADJ
			CLOUDINT = (state_arr & 0b10000000000)
			rank_arr[CLOUDINT>0]=4
			del CLOUDINT
			logging.debug("--rank 3: HIGHVIEW")
			rank_arr[sang_arr>(85/0.01)]=3 # HIGHVIEW
			logging.debug("--rank 2: LOWSUN")
			rank_arr[vang_arr>(60/0.01)]=2 # LOWSUN
			# BAD pixels
			logging.debug("--rank 1: BAD pixels") # qa bits (2-5 OR 6-9 == 1110)
			BAD = ((qa_arr & 0b111100) | (qa_arr & 0b1110000000))
			rank_arr[BAD==112]=1
			rank_arr[BAD==896]=1
			rank_arr[BAD==952]=1
			del BAD

			logging.debug("-building water mask")
			water = ((state_arr & 0b111000)) # check bits
			water[water==56]=1 # deep ocean
			water[water==48]=1 # continental/moderate ocean
			water[water==24]=1 # shallow inland water
			water[water==40]=1 # deep inland water
			water[water==0]=1 # shallow ocean
			rank_arr[water==1]=0
			vang_arr[water==32]=9999 # ephemeral water???
			water[state_arr==0]=0
			water[water!=1]=0 # set non-water to zero
			in_array[rank_arr <= 7] = -3000
		elif ext == ".h5": # VNP09CMG
			qf2 = octvi.extract.datasetToArray(source_stack,"SurfReflect_QF2")
			qf4 = octvi.extract.datasetToArray(source_stack,"SurfReflect_QF4")
			state_arr = octvi.extract.datasetToArray(source_stack,"State_QA")
			vang_arr = octvi.extract.datasetToArray(source_stack,"SensorZenith")
			vang_arr[vang_arr<=0]=9999
			sang_arr = octvi.extract.datasetToArray(source_stack,"SolarZenith")
			rank_arr = np.full(state_arr.shape,10) # empty rank array

			## perform the ranking!
			logging.debug("--rank 9: SNOW")
			SNOW = (state_arr & 0b1000000000000000) # state bit 15
			rank_arr[SNOW>0]=9 # snow
			del SNOW
			logging.debug("--rank 8: HIGHAEROSOL")
			HIGHAEROSOL=(qf2 & 0b10000) # qf2 bit 4
			rank_arr[HIGHAEROSOL!=0]=8
			del HIGHAEROSOL
			logging.debug("--rank 7: AEROSOL")
			CLIMAEROSOL=(state_arr & 0b1000000) # state bit 6
			#CLIMAEROSOL=(cloudMask & 0b100000000000000) # cloudMask bit 14
			#rank_arr[CLIMAEROSOL==0]=7 # "No"
			del CLIMAEROSOL
			# logging.debug("--rank 6: UNCORRECTED")
			# UNCORRECTED = (qa_arr & 0b11) # qa bits 0 AND 1
			# rank_arr[UNCORRECTED==3]=6 # flagged uncorrected
			# del UNCORRECTED
			logging.debug("--rank 5: SHADOW")
			SHADOW = (state_arr & 0b100) # state bit 2
			rank_arr[SHADOW!=0]=5 # cloud shadow
			del SHADOW
			logging.debug("--rank 4: CLOUDY")
			# set adj to 11 and internal to 12 to verify in qa output
			# CLOUDY = ((state_arr & 0b11)) # state bit 0 OR bit 1 OR bit 10 OR bit 13
			# rank_arr[CLOUDY!=0]=4 # cloud pixel
			# del CLOUDY
			# CLOUDADJ = (state_arr & 0b10000000000) # nonexistent for viirs
			# #rank_arr[CLOUDADJ>0]=4 # adjacent to cloud
			# del CLOUDADJ
			CLOUDINT = (state_arr & 0b10000000000) # state bit 10
			rank_arr[CLOUDINT>0]=4
			del CLOUDINT
			logging.debug("--rank 3: HIGHVIEW")
			rank_arr[sang_arr>(85/0.01)]=3 # HIGHVIEW
			logging.debug("--rank 2: LOWSUN")
			rank_arr[vang_arr>(60/0.01)]=2 # LOWSUN
			# BAD pixels
			logging.debug("--rank 1: BAD pixels") # qa bits (2-5 OR 6-9 == 1110)
			BAD = (qf4 & 0b110)
			rank_arr[BAD!= 0]=1
			del BAD

			logging.debug("-building water mask")
			water = ((state_arr & 0b111000)) # check bits 3-5
			water[water == 40] = 0 # "coastal" = 101
			water[water>8]=1 # sea water = 011; inland water = 010
			# water[water==16]=1 # inland water = 010
			# water[state_arr==0]=0
			water[water!=1]=0 # set non-water to zero
			water[water!=0]=1
			rank_arr[water==1]=0
			in_array[rank_arr <= 7] = -3000
		else:
			raise octvi.exceptions.FileTypeError("File must be of format .hdf or .h5")
	# standard
	else:
		# modis
		if ext == ".hdf": 
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
		#in_array[(state_arr & 0b10000000000000) != 0] = -3000

		## mask aerosols
		in_array[(state_arr & 0b11000000) == 0] = -3000 # climatology
		in_array[(state_arr & 0b11000000) == 192] = -3000 # high

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
			try:
				refDs = h5py.File(model_file.split("\"")[1],mode='r') # open file in read-only mode
			except IndexError:
				refDs = h5py.File(model_file,mode='r') # open file in read-only mode
			fileMetadata = refDs['HDFEOS INFORMATION']['StructMetadata.0'][()].split() # grab metadata
			fileMetadata = [m.decode('utf-8') for m in fileMetadata] # decode UTF
			ulc = [i for i in fileMetadata if 'UpperLeftPointMtrs' in i][0]    # Search file metadata for the upper left corner of the file
			ulcLon = float(ulc.split('=(')[-1].replace(')', '').split(',')[0]) # Parse metadata string for upper left corner lon value
			ulcLat = float(ulc.split('=(')[-1].replace(')', '').split(',')[1]) # Parse metadata string for upper left corner lat value
			# special behavior for VNP09CMG
			if os.path.basename(model_file).split(".")[0][-3:] == "CMG":
				ulcLon = ulcLon / 1000000
				ulcLat = ulcLat / 1000000
				pixelSize = 0.05
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