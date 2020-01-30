from unittest import TestCase

def test_import_main():
	try:
		import octvi
	except ImportError:
		raise AssertionError
	except ModuleNotFoundError:
		raise AssertionError

class TestSubmoduleImports(TestCase):
	def test_array_automatically_imported(self):
		try:
			import octvi
			octvi.array
		except AttributeError:
			raise AssertionError

	def test_url_automatically_imported(self):
		try:
			import octvi
			octvi.url
		except AttributeError:
			raise AssertionError

	def test_extract_automatically_imported(self):
		try:
			import octvi
			octvi.extract
		except AttributeError:
			raise AssertionError

	def test_exceptions_automatically_imported(self):
		try:
			import octvi
			octvi.exceptions
		except AttributeError:
			raise AssertionError