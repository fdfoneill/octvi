## set up logging
import logging, os
logging.basicConfig(level=os.environ.get("LOGLEVEL","INFO"))
log = logging.getLogger(__name__)

## import modules
import csv, octvi.exceptions, shutil, ssl, subprocess, sys, urllib
from datetime import datetime
from io import StringIO
from  octvi.exceptions import UnavailableError
from urllib.request import urlopen, Request, URLError, HTTPError

supported_products = ["MOD09Q1","MOD13Q1","MYD09Q1","MYD13Q1","VNP09H1","MOD09Q1N","MOD13Q4N","MOD09CMG","VNP09CMG"]
#app_key = '95A63BCA-39AE-11E8-B469-FEF9569DBFBA'


def pull(url:str,out_dir=None,file_name_override=None,retries=5) -> str:
	"""
	This function attempts to open the data file located at {url}. If
	{out_dir} is provided, the file is saved to that location. Otherwise,
	an opened file object is returned.

	If {out_dir} is set, the function returns the full path to the saved
	file as a string.

	...

	Parameters
	----------

	url: str
		Url of source file to be downloaded/opened
	out_dir: str
		Path to directory where file will be output
	file_name_override: str
		Desired name of output file. If None, an attempt will be made to
		extract the product, date, and tile of the url, in order to form the
		name as follows: "{product}.{date}.{tile}.{extension}"
	retries: int
		How many times to re-try the download if it fails
	"""
	# check whether LP or LADS
	if url.split("/")[2] == 'e4ftl01.cr.usgs.gov':
		lads_or_lp = "LP"
	else:
		lads_or_lp = "LADS"

	## building authorization
	headers = { 'user-agent' : str('tis/download.py_1.0--' + sys.version.replace('\n','').replace('\r','')), 'Authorization' : f'Bearer {octvi.app_key}'}
	#headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
	CTX = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

	## if saving to file, generate file name
	if out_dir is not None:
		url_parts = url.split("/")#[-1].split(".")
		tile = url_parts[-1].split(".")[2]
		if file_name_override is None:
			# extracting information from URL string
			product = url_parts[-4]
			year = url_parts[-3]
			doy = url_parts[-2]
			date = datetime.strptime(f"{year}{doy}","%Y%j").strftime("%Y-%m-%d")
			extension = url_parts[-1].split(".")[-1]
			# creating output file name
			out_base = f"{product}.{date}.{tile}.{extension}"
		else:
			out_base = file_name_override
		out = os.path.join(out_dir,out_base)
	else:
		out=None

	#def tryPull(url,out_path):
		#"""
		#Attempt to pull url
		#"""
		#try:
			#fh = urlopen(Request(url, headers=headers), context=CTX)
			#if out_path is None:
				#return fh.read().decode('utf-8')
			#else:
				#with open(out,'wb') as fd:
					#shutil.copyfileobj(fh, fd)
				#fh = fd = None # use garbage collection to force cache flush
		#except Error as e:
			#if out_path is None:
				#raise e
			#log.warning(f"urllib method failed for {url}, trying wget")
			#try:
				#log.info("wget64")
				#subprocess.call(["wget64",url,'--header',f'"Authorization: Bearer {octvi.app_key}"',"-O",out],shell=True)
				#return out
			#except FileNotFoundError:
				#try:
					#log.info("wget32")
					#subprocess.call(["wget32",url,'--header',f'"Authorization: Bearer {octvi.app_key}"',"-O",out],shell=True)
					#return out
				#except FileNotFoundError:
					#log.info("wget")
					#subprocess.call(["wget",url,'--header',f'"Authorization: Bearer {octvi.app_key}"',"-O",out],shell=True)
					#return out

	## fetching data
	try:
		fh = urlopen(Request(url, headers=headers), context=CTX)
		if out is None:
			return fh.read().decode('utf-8')
		else:
			with open(out,'wb') as fd:
				shutil.copyfileobj(fh, fd)
			fh = fd = None # use garbage collection to force cache flush
	except HTTPError:
		if retries<=0:
			raise UnavailableError(f"Failed to pull data from {url}")
		else:
			log.warning(f"HTTPError at {url}; trying again. Remaining retries: {retries}")
			return pull(url=url,out_dir=out_dir,file_name_override=file_name_override,retries=retries-1)
	#except URLError as e:
		#log.exception('Failed to make request')

	return out

def getUrls(product:str,date:str,tiles=None,lads_or_lp="LADS") -> list:
	"""
	This function fetches the LADS DAAC urls for the image
	files specified by the passed product name, date string,
	and tiles. If 'tiles' is omitted, all files for listed date
	will be returned. For CMG-scale products, that parameter
	should be omitted.

	Returns a list of tuples, structured as follows:
	[(url1,tileName1,fileSize1),(url2,tileName2,fileSize2),...]

	...

	Parameters
	----------

	product: str
		Product code of desired product; e.g. "MOD13Q1"
	date: str
		String date of desired data, formatted as "%Y-%m-%d"
	tile: str/list (optional)
		Desired MODIS grid tile; e.g. "h09v13" or ["h09v13", "h10v05"]
	lads_or_lp:str
		Whether to return urls for the LP DAAC or the LADS DAAC
	"""

	if product not in supported_products:
		raise octvi.exceptions.UnsupportedError(f"Product '{product}' is not currently supported. See octvi.supported_products for list of supported products.")

	## coerce 'tiles' argument to list and clean it up
	if tiles is not None:
		try:
			tiles.extend([])
		except AttributeError:
			tiles = [tiles]
		tiles = [x.lower() for x in tiles]

	outList = []

	prefix = product[:3]
	if product[-1] == "N":
		nrt = True
	else:
		nrt = False
	
	## assign correct collection number
	if prefix == "VNP":
		collection = "5000"
	else:
		collection = "6"

	## extract year and doy from date
	dateObj = datetime.strptime(date,"%Y-%m-%d")
	year = dateObj.strftime("%Y")
	doy = dateObj.strftime("%j").zfill(3)

	## form directory url and get file listing
	try:
		if nrt:
			dirUrl = f"https://nrt3.modaps.eosdis.nasa.gov/archive/allData/{collection}/{product}/{year}/{doy}/"
			csvUrl = f"https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/{collection}/{product}/{year}/{doy}/?fields=all&format=csv"
			dirFiles = [ f for f in csv.DictReader(StringIO(pull(csvUrl)), skipinitialspace=True) ]
		else:
			ladsUrl = f"https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/{collection}/{product}/{year}/{doy}/"
			lpUrl = f"https://e4ftl01.cr.usgs.gov/MOLT/{product}.{collection.zfill(3)}/{dateObj.strftime('%Y.%m.%d')}/"
			dirFiles = [ f for f in csv.DictReader(StringIO(pull('%s.csv' % ladsUrl)), skipinitialspace=True) ]
			if lads_or_lp == "LADS":
				dirUrl = ladsUrl
			elif lads_or_lp == "LP":
				dirUrl = lpUrl
	except UnavailableError:
		raise UnavailableError(f"No listed data for requested product {product} on date {date}")


	## append matching files / all files
	for f in dirFiles:
		if nrt:
			fPath = f['downloadsLink']
			fTile = fPath.split("/")[-1].split(".")[2]
			if fPath.split(".")[-1] == "met": # skip metadata files for NRT
				continue
			fullUrl = "https://nrt3.modaps.eosdis.nasa.gov" + fPath
			fSize = f['size']
		else:
			fName = f["name"]
			fTile  = fName.split(".")[2]
			fullUrl = dirUrl + fName
			fSize = f["size"]

		# append to list
		if (tiles is None):
			outList.append((fullUrl,fTile,fSize))
		elif (fTile in tiles):
			outList.append((fullUrl,fTile,fSize))

	## throw error if no matching tiles
	if len(outList) == 0:
		raise UnavailableError(f"Requested tiles not found for product {product} on {date}")

	return outList

def getDates(product:str,date:str) -> list:
	"""
	This function returns all available imagery dates for the
	given product x date-range combination. If passed a single date,
	returns that date if it is available or an empty list if not.

	...

	Parameters
	---------

	product:str
		String name of desired imagery product
	date:str
		Range in which to search for valid imagery.
		Can be one of: "%Y", "%Y-%m", "%Y-%m-%d". In the former two
		cases, loops over all dates within year or month, and returns
		those dates for which there is imagery available. If a full
		Y-m-d is passed, returns a list containing that date if there
		is imagery available, or an empty list if not.
	"""

	def doysFromYear(product, year,collection,nrt=False) -> list:
		"""Given product and year, returns valid days of year"""
		outList = []

		## get and parse CSV
		try:
			if nrt:
				csvUrl = f"https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/{collection}/{product}/{year}/?fields=all&format=csv"
				dirFiles = [ f for f in csv.DictReader(StringIO(pull(csvUrl)), skipinitialspace=True) ]
			else:
				dirUrl = f"https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/{collection}/{product}/{year}/"
				dirFiles = [ f for f in csv.DictReader(StringIO(pull('%s.csv' % dirUrl)), skipinitialspace=True) ]
		except UnavailableError:
			return []

		## extract valid days of year fro CSV
		for d in dirFiles:
			doy = d['name']
			if nrt:
				doyCsvUrl = f"https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/{collection}/{product}/{year}/{doy}/?fields=all&format=csv"
				doyFiles = [ f for f in csv.DictReader(StringIO(pull(doyCsvUrl)), skipinitialspace=True) ]
				if len(doyFiles) == 0:
					continue
			outList.append(doy)

		## return list
		return outList

	def checkDoy(product,year,doy,collection,nrt=False) -> bool:
		"""Returns whether there is any data for a given product on a given date"""

		doyList = doysFromYear(product,year,collection,nrt)

		if doy in doyList:
			return True
		else:
			return False

	## confirm that product is valid
	if product not in supported_products:
		raise octvi.exceptions.UnsupportedError(f"Product '{product}' is not currently supported. See octvi.supported_products for list of supported products.")

	## determine whether Near-Real-Time product
	prefix = product[:3]
	if product[-1] == "N":
		nrt = True
		dirUrl = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/"
	else:
		nrt = False
		dirUrl = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/"
	
	## assign correct collection number
	if prefix == "VNP":
		collection = "5000"
	else:
		collection = "6"

	outList = []
	doyList = []
	try: # is it "%Y-%m-%d"?
		dateObj = datetime.strptime(date,"%Y-%m-%d")
		year = dateObj.strftime("%Y")
		doy = dateObj.strftime("%j")
		if checkDoy(product,year,doy,collection,nrt):
			doyList = [doy]
		else:
			doyList = []
	except ValueError:
		try:
			dateObj = datetime.strptime(date,"%Y-%m")
			year = dateObj.strftime("%Y")
			month = dateObj.strftime("%m")
			validDoys = doysFromYear(product,year,collection,nrt)
			for doy in validDoys:
				if datetime.strptime(f"{year}-{doy}","%Y-%j").strftime("%m") == month:
					doyList.append(doy)
		except ValueError:
			try:
				dateObj = datetime.strptime(date,"%Y")
				year = dateObj.strftime("%Y")
				doyList= doysFromYear(product,year,collection,nrt)
			except ValueError:
				log.error(r"Date must be one of %Y-%m-%d, %Y-%m, %Y")
				return []
	for doy in doyList:
		outList.append(datetime.strptime(f"{year}-{doy}","%Y-%j").strftime("%Y-%m-%d"))
	return outList

def ladsToLp(lads_url:str) -> str:
	pass