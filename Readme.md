# Python utilities for working with Geonetwork (2.10)

**geonetwork_waf.py**

_Only works with Geonetwork 2.10.x, see 3.2.x branch for later version_

Utility script to prep the metadata for use in the web-accessible folder method of harvesting on data.gov.uk. Takes a zip file of metadata as downloaded from geonetwork and extracts the relevant xml files into a single folder suitable for use as a web-accessible folder for use on data.gov.uk. Identifies the service record and names it service.xml, fixes the coupled record references within service.xml, and creates an index.html listing all the files, as required for harvesting. Only tested with metadata in Gemini 2.2 format, mileage with other schema may vary

Requires:

  - Python 2.6+ (Python 3 not tested)
  - lxml (install from [here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml) if setuptools don't work)

  Usage:

		python geonetwork_waf.py -p path -C client -u URL

  Where:

  -p is the path to the zip file as downloaded from geonetwork

  -C is the name of the client (will be sanitised and used for the name of the output folder)

  -u is the URL of the web-accessible folder on the external server (required for correct parsing of index.html by data.gov.uk)

  