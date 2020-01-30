from unittest import TestCase
import numpy as np
import os
import octvi

class TestExtract(TestCase):
	def setUp(self):
		self.stack = octvi.url.pull(octvi.url.getUrls("MOD09CMG","2019-01-01")[0][0],os.path.dirname(__file__),True)
	def tearDown(self):
		os.remove(self.stack)

class TestGetDatasetNames(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

	def test_datasetNames(self):
		dsn = octvi.extract.getDatasetNames(self.stack)
		self.assertIsInstance(dsn,list)
		for name in dsn:
			self.assertIsInstance(name,str)

class TestDatasetToPath(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

	def test_datasetToPath(self):
		dsn = octvi.extract.getDatasetNames(self.stack)
		pathName = octvi.extract.datasetToPath(self.stack,dsn)
		self.assertIsInstance(pathName,str)

class TestDatasetToArray(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

class TestDatasetToRaster(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

class TestNdviToArray(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

class TestNdviToRaster(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

class TestCmgToViewAngArray(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

class TestCmgListToWaterArray(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

class TestCmgToRankArray(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)

class TestCmgBestNdviPixels(TestCase):
	def setUp(self):
		self.stack = downloadExampleFile()
	def tearDown(self):
		os.remove(self.stack)