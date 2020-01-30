# octvi
Python package for downloading, mosaicking, or compositing MODIS-scale NDVI imagery

# Motivation
I work on development of the Global Agriculture Monitoring (GLAM) system. A core feature of the system is the ability to display large amounts of Vegetation Index (VI) imagery, pulled from sources like the MODIS and VIIRS satellite sensors. Obviously, displaying that imagery through our system requires the ability to download it from its source. This is harder than it sounds, especially when we also want to extract specific subdatasets, convert to a different file format, and mosaic dozens of individual "tiles" into a single global image.

This package started out as a local tool for that very purpose. The name "octvi" comes from the fact that, at first, I planned to restrict functionality to 8-day (oct) vegetation indices (vi). Over time, though, I realized it was fairly simple to support more imagery products, including 16-day vegetation indices and even DIY multi-day composites. When other researchers in my department started asking to use the package, I realized it needed to be more accessible.

# Features
The primary functionality of the `octvi` module is the creation of global mosaics of Normalized Difference Vegetation Index (NDVI) imagery. Supported imagery products include:

* MODIS 8-day NDVI
..* Terra (MOD09Q1)
..* Aqua (MYD09Q1)
* MODIS 16-day NDVI
..* Terra (MOD13Q1)
..* Aqua (MYD13Q1)
* VIIRS 8-day NDVI (VNP09H1)
* LANCE Near Real-Time
..* MODIS 8-day Terra (MOD09Q1N)
..* MODIS 16-day Terra (MOD13Q4N)
* MODIS 8-day Climate Modeling Grid (CMG)-scale NDVI (MOD09CMG; custom compositing)

# Code Example

```python
import octvi # import module

# create a list of all days in January 2019 for which there exists valid VNP09H1 imagery
viirsJanuaryDates = octvi.url.getDates("VNP09H1","2019-01") 

# generate global NDVI mosaic of MOD09Q1 data for an 8-day period starting on January 1st, 2019
octvi.globalNdvi("MOD09Q1","2019-01-01","C:/temp/example_standard.tif") 

# generate custome composite of CMG-scale NDVI for an 8-day period starting on January 1st, 2019
octvi.globalNdvi("MOD09CMG","2019-01-01","C:/temp/example_cmg.tif") 
```

# How to Use
The `octvi` package contains four submodules: `url`, `extract`, `array`, and `exceptions`. Most of the features you will want, though, are in the top-level module.

The core functionality is shown in the code example above. Once the package is installed, you can import it in a script or REPL, and then use all the submodules freely. When `octvi` is imported, all submodules are also automatically imported and their namespaces can be accessed as shown with `octvi.url.getDates()` above.

# License
MIT License

Copyright (c) 2020 F. Dan O'Neill

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
