import configparser
from octvi import configFile

def getYesNo(message:str) -> bool:
	cont = input(message+"[Y/N]\n")
	if cont.lower() in ("y","yes"):
		return True
	elif cont.lower() in ("n","no"):
		return False
	else:
		print("Error: Input not recognized. Please select one of: [Y/N]")
		return getYesNo(message)


def main():
	config = configparser.ConfigParser()
	try:
		config.read(configFile)
		assert isinstance(config['NASA'],dict)
	except:
		config['NASA'] = {}
	config['NASA']['app_key'] = input('App Key: ')
	if getYesNo('Save new app key?'):
		with open(configFile,'w') as wf:
			config.write(wf)