class UnavailableError(Exception):
	"""
	Error class indicating that a requested
	file does not exist on the LADS DAAC.
	"""
	def __init__(self,data):
		self.data=data
	def __str__(self):
		return repr(self.data)

class FileTypeError(TypeError):
	"""
	Error class indicating that there is
	a problem with a raster file. The file format
	may be incorrect, a requested subdataset may
	not exist, or there may be another problem.
	"""

	def __init__(self,data):
		self.data=data
	def __str__(self):
		return repr(self.data)

class DatasetNotFoundError(UnavailableError):
	"""
	Error class indicating that a requested
	subdataset does not exist in the given
	hierarchical file.
	"""
	def __init__(self,data):
		self.data=data
	def __str__(self):
		return repr(self.data)

class UnsupportedError(Exception):
	"""
	Error class indicating that a dataset
	is not currently supported by the octvi
	module. Supported datasets are stored
	in the octvi.supported_datasets attribute.
	"""
	def __init__(self,data):
		self.data=data
	def __str__(self):
		return repr(self.data)