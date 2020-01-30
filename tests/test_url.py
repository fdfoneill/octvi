from unittest import TestCase
import numpy as np
import octvi, os

class TestPull(TestCase):
	
	def test_openUrl(self):
		csv = octvi.url.pull('https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MOD09CMG/2019/001/.csv')
		self.assertIsInstance(csv,str)

	def test_pullToDisk(self):
		try:
			idealDir = os.path.dirname(__file__)
			idealName = os.path.join(idealDir,"MOD09CMG.2019-01-01.006.hdf")
			name = octvi.url.pull('https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MOD09CMG/2019/001/MOD09CMG.A2019001.006.2019003023418.hdf',idealDir)
			self.assertTrue(name == idealName)
		except:
			raise AssertionError(f"Error downloading {idealName} to disk")
		finally:
			try:
				os.remove(name)
			except:
				pass

class TestGetUrls(TestCase):
	
	def test_allMod09Tiles(self):
		u = octvi.url.getUrls("MOD09Q1","2019-01-01")
		self.assertIsInstance(u,list)
		self.assertTrue(len(u) == 274)
		self.assertIsInstance(u[0],tuple)

	def test_oneMod09TileString(self):
		u = octvi.url.getUrls("MOD09Q1","2019-01-01",tiles='h00v08')
		self.assertIsInstance(u,list)
		self.assertTrue(len(u) == 1)
		self.assertIsInstance(u[0],tuple)

	def test_twoMod09TilesList(self):
		u = octvi.url.getUrls("MOD09Q1","2019-01-01",tiles=['h00v08','h00v09'])
		self.assertIsInstance(u,list)
		self.assertTrue(len(u) == 2)
		self.assertIsInstance(u[0],tuple)

	def test_mod09Cmg(self):
		u = octvi.url.getUrls("MOD09CMG","2019-01-01")
		self.assertIsInstance(u,list)
		self.assertTrue(len(u) == 1)
		self.assertIsInstance(u[0],tuple)

class TestGetDates(TestCase):

	def test_yearOnly(self):
		self.assertIsInstance(octvi.url.getDates("MOD09Q1","2019"),list)

	def test_yearMonth(self):
		d = octvi.url.getDates("MOD09Q1","2019-01")
		self.assertIsInstance(d,list)
		self.assertFalse(len(d) == 0)

	def test_yearMonthDay(self):
		d = octvi.url.getDates("MOD09Q1","2019-01")
		self.assertIsInstance(d,list)
		self.assertFalse(len(d) == 0)

	def test_noDates(self):
		d = octvi.url.getDates("MOD09Q1","1993")
		self.assertIsInstance(d,list)
		self.assertTrue(len(d)==0)

	def test_invalidDateFormat(self):
		d = octvi.url.getDates("MOD09Q1","invalid_date_format")
		self.assertIsInstance(d,list)
		self.assertTrue(len(d)==0)

	def test_unsupportedProduct(self):
		customError = False
		try:
			octvi.url.getDates("MOD66F8","2019")
		except octvi.exceptions.UnsupportedError:
			customError = True
		except:
			pass
		self.assertTrue(customError)