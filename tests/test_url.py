from unittest import TestCase
import numpy as np
import octvi

class TestPull(TestCase):
	pass

class TestGetUrls(TestCase):
	pass

class GetDates(TestCase):

	def test_returnType(self):
		self.assertIsInstance(octvi.url.getDates("MOD09Q1","2019-01"),list)

	def test_noDates(self):
		self.assertTrue(len(octvi.url.getDates("MOD09Q1","1993"))==0)