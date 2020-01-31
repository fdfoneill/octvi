from unittest import TestCase

import octvi
import os

class TestMosaic(TestCase):

	def test_mosaicking(self):
		tempDir = os.path.dirname(__file__)
		urls = [u[0] for u in octvi.url.getUrls("MOD09Q1","2019-01-01",tiles=['h00v08','h00v09'])]
		try:
			idealMosaicName = "mosaicTest.tif"
			hdfs = [octvi.url.pull(u,tempDir) for u in urls]
			ndvis = [octvi.extract.ndviToRaster(h,h.replace(".hdf",".ndvi.tif")) for h in hdfs]
			mosaicPath = octvi.mosaic(ndvis,os.path.join(tempDir,idealMosaicName))
			self.assertEqual(os.path.basename(mosaicPath),idealMosaicName)
		finally:
			for f in hdfs:
				os.remove(f)
			for f in ndvis:
				os.remove(f)
			os.remove(mosaicPath)
"""
class TestCmgNdvi(TestCase):
	
	def test_compositing(self):
		idealOutName = 'compositeTest.tif'
		res = octvi.cmgNdvi("2019-01-01",os.path.join(os.path.dirname(__file__),idealOutName),overwrite=True)
		self.assertIsInstance(res,str)
		self.assertIsEqual(os.path.basename(res),idealOutName)
		os.remove(res)
"""

class TestGlobalNdvi(TestCase):
	
	def test_unsupportedProduct(self):
		customError = False
		try:
			octvi.globalNdvi("MOD66F8","2019-01-01",os.path.join(os.path.dirname(__file__),"unsupported.tif"),overwrite=True)
			os.remove(os.path.join(os.path.dirname(__file__),"unsupported.tif"))
		except octvi.exceptions.UnsupportedError:
			customError = True
		self.assertTrue(customError)