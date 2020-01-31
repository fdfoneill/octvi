from unittest import TestCase
import numpy as np
import octvi

class TestCalcNdvi(TestCase):
	def test_basic_calculation(self):
		red_array = np.array([.1])
		nir_array = np.array([.5])
		ndvi_array = octvi.array.calcNdvi(red_array,nir_array)
		self.assertEqual(ndvi_array,np.array([6666]))
	def test_divideByZero_handling(self):
		red_array = np.array([.1])
		nir_array = np.array([-.1])
		ndvi_array = octvi.array.calcNdvi(red_array,nir_array)
		self.assertEqual(ndvi_array,np.array(-3000))

class TestMask(TestCase):
	pass

class TestToRaster(TestCase):
	pass