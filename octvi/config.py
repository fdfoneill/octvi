import argparse, configparser, os, sys
configFile = os.path.join(os.path.dirname(os.path.dirname(__file__)),"etc/config.ini")

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
	parser = argparse.ArgumentParser(description="Set credentials for downloading with the octvi python module.")
	parser.add_argument('-l',
		'--list',
		action='store_true',
		help="List current credentials instead of prompting for new")
	args = parser.parse_args()
	config = configparser.ConfigParser()
	if not os.path.exists(os.path.dirname(configFile)):
		os.mkdir(os.path.dirname(configFile))
	try:
		config.read(configFile)
		## if asked to list existing credentials, print them nicely
		if args.list:
			for section in config:
				header = "\n["+str(section)+"]\n"
				for letter in str(section):
					header += "-"
				print(header)
				for key in config[section].keys():
					print(f"{key}: {config[section][key]}")
			print("\n")
		else:
			assert isinstance(config['NASA'],dict)
	## behavior if no file exists, or if it lacks the 'NASA' section
	except:
		if args.list:
			print("WARNING: Config file not found. Use octviconfig to create it.")
			if not getYesNo("Input app key now?"):
				sys.exit()
		config['NASA'] = {}
	if args.list:
		sys.exit()
	config['NASA']['app_key'] = input('Token: ')
	if getYesNo('Save new app key?'):
		with open(configFile,'w') as wf:
			config.write(wf)
