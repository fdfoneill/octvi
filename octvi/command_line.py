import argparse, octvi, os
from datetime import datetime

def main():
	parser = argparse.ArgumentParser(description="Download a global mosaic of NDVI imagery for a given date")
	parser.add_argument('product',
		type=str,
		help="Product code; e.g. 'MOD09Q1', 'VNP09H1', etc.")
	parser.add_argument('date',
		type=str,
		help="Desired imagery date, in format '%%Y-%%m-%%d'. For composites this is the first day of the compositing period.")
	parser.add_argument('out_directory',
		type=str,
		help="Directory on disk where output file will be written.")
	parser.add_argument("-f",
		'--filename',
		type=str,
		required=False,
		help="Specify file name of output. If this flag is not set, the default of {PRODUCT}.{YEAR}.{DOY}.tif will be used. Must be a .tif file.")
	parser.add_argument("-o",
		"--overwrite",
		action='store_true',
		help="Whether to overwrite an existing file at the output location. Default False.")

	args = parser.parse_args()

	year,doy = datetime.strptime(args.date,"%Y-%m-%d").strftime("%Y.%j").split(".")

	if args.filename:
		newOutName = os.path.join(args.out_directory,args.filename)
	else:
		newOutName = os.path.join(args.out_directory,f"{args.product}.{year}.{doy}.tif")

	try:
		octvi.globalNdvi(args.product,args.date,newOutName,args.overwrite)
	except FileExistsError:
		print(f"WARNING: Image for {args.product} on {args.date} already exists in {args.out_directory}. Use the '--overwrite' flag to overwrite existing files.")