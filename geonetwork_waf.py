# -*- coding: utf8 -*-

## Copyright (c) 2014 Astun Technology

## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:

## The above copyright notice and this permission notice shall be included in
## all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
## THE SOFTWARE.

### geonetwork_waf.py: script for converting geonetwork batch export to WAF
### suitable for use with data.gov.uk

### WOULD BE NICE: to check for wfs and csw urls as well as wms, and add as required
### would need to be done for both service and dataset xml

import sys
import os
import zipfile
from lxml import etree
from optparse import OptionParser
import shutil
import datetime
import glob

class GeonetworkWAF():

    def __init__(self):

        desc = """create a single folder of metadata in xml format from a geonetwork batch export zip
        Usage: geonetwork_waf.py -p zipfile -C client -u URL"""
        parser = OptionParser(description=desc)
        parser.add_option("-p", "--path", dest="path", help="name of zip file (mandatory)")
        parser.add_option("-C", "--client", dest="client", help="name of client (mandatory)")
        parser.add_option("-u", "--url", dest="url", help="URL for WAF (mandatory)")
        (options, args) = parser.parse_args()

        mandatories = ['path', 'client', 'url']
        for m in mandatories:
            if not options.__dict__[m]:
                    print "a mandatory option is missing"
                    parser.print_help()
                    exit(-1)

        self.options = options
        self.client = options.client
        self.path = options.path
        self.url = options.url
        self.clientlcase = self.client.lower().replace(" ", "_") #sanitised client name to use as name of zip

        # set today's date in correct format for updating service and dataset xml files if needed
        now = datetime.datetime.now()
        self.formattednow = now.strftime("%Y-%m-%d")

    def fixTimeStamp(self, outputdir):
        ''' fixes timestamp on modified files so data.gov.uk doesn't reject them'''
        try:
            for filename in glob.glob(os.path.join(outputdir, '*.xml')):
                doc = etree.parse(filename)
                for d in doc.find('.//{http://www.isotc211.org/2005/gmd}dateStamp'):
                    d.text = self.formattednow
                    doc.write(filename)
        except:
            e = sys.exc_info()[1]
            print "Date Error with %s: %s" % (filename, e)
            sys.exit(1)


    def extractzip(self):
        # set up required folders
        tmpdir = os.path.join(os.getcwd(), 'tmp')
        outputdir = os.path.join(os.getcwd(), self.clientlcase)

        # create dictionary to hold UUID and layer names (needed for editService function)
        d = {}

        #define required namespaces
        namespaces = {'gmd': 'http://www.isotc211.org/2005/gmd', 'gco':'http://www.isotc211.org/2005/gco', 'srv':'http://www.isotc211.org/2005/srv'}

        try:
            if not os.path.isdir(tmpdir):
                print "tmpdir does not exist, making it"
                os.makedirs(tmpdir)
            if not os.path.isdir(outputdir):
                print "outputdir does not exist, making it"
                os.makedirs(outputdir) 
        except:             
            e = sys.exc_info()[1]
            print "file creation error: %s" % e
            sys.exit(1)
        
        # unzip downloaded zip and extract only metadata.xml file
        try:
            filezip = zipfile.ZipFile(self.path, 'r')
        except:
            e = sys.exc_info()[1]
            print "Unzip Error: %s" % e
            sys.exit(1)
      
        for name in filezip.namelist():
            if os.path.basename(name) == 'metadata.xml':
                # set up temporary folder for extracting to
                tmpfile = os.path.join(tmpdir, os.path.basename(name))
                file(tmpfile, 'wb').write(filezip.read(name))
                # parse xml to find something sensible and unique to rename xml to
                doc = etree.parse(tmpfile)

                try:                        
                    # if it's the service doc then rename it and move on
                    for b in doc.find('./gmd:hierarchyLevel',namespaces):
                        if b.attrib['codeListValue'] == 'service':
                            for m in doc.findall('./gmd:MD_DigitalTransferOptions', namespaces):
                                 for l in m.findall('./gmd:onLine', namespaces):
                                    for i in l.findall('./gmd:hierarchyLevel/gmd:description',namespaces):
                                        for j in i.findall('./gco:CharacterString'):
                                            etree.SubElement(i, '{http://www.isotc211.org/2005/gco}CharacterString').text = 'INSPIRE Service GetCapabilties URL'
                                            i.remove(j)
                                            doc.write(tmpfile)
                                    shutil.move(tmpfile,os.path.join(tmpdir,'temp_service.xml'))
                        else:
                            # use proper title as filename for URL
                            try:
                                for i in doc.iterfind('./gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title',namespaces):
                                    for n in i.findall('./gco:CharacterString',namespaces):
                                        d[os.path.dirname(os.path.dirname(name))] = n.text
                                        shutil.move(tmpfile,os.path.join(outputdir,n.text + '.xml'))
                            except:
                                e = sys.exc_info()[1]
                                print "XML file naming error with %s: %s" % (name, e)
                                sys.exit(1)  
                except:
                    e = sys.exc_info()[1]
                    print "XML dataset Error with %s: %s" % (name, e)
                    sys.exit(1)

        try:
            #edit service doc so that links to coupled resources reference xml files in outputdir
            servicedoc = etree.parse(os.path.join(tmpdir,'temp_service.xml'))
            serviceID = servicedoc.find('.//srv:SV_ServiceIdentification', namespaces)
            for k in servicedoc.findall('.//srv:SV_ServiceIdentification/srv:operatesOn', namespaces):
                for key,value in k.attrib.iteritems():
                    if key == 'uuidref':
                        # find correct entry in dictionary
                        if value in d:
                            # remove invalid element
                            serviceID.remove(k)
                            # add new valid subelement
                            etree.SubElement(serviceID, '{http://www.isotc211.org/2005/srv}operatesOn',{'{http://www.w3.org/1999/xlink}href':self.url + '/' + d[value] + '.xml'})
                        else:
                            print "Problem with coupled resource %s" % value


            servicedoc.write(os.path.join(outputdir, 'service.xml'), pretty_print=True)
            # delete temp directory (and its contents)
            shutil.rmtree(tmpdir)
            print "File extraction into %s completed successfully" % outputdir
        except:
            e = sys.exc_info()[1]
            print "XML service Error: %s" % e
            sys.exit(1)

            
        self.fixTimeStamp(outputdir)

    def createIndex(self):
        '''Create an index.html file suitable for using on data.gov.uk'''
        # iterate through files in output folder to create a list
        # create a new list to hold the files
        try:
            l = []
            outputdir = os.path.join(os.getcwd(), self.clientlcase)
            filelist = os.listdir(outputdir)
            for i in filelist:
                l.append(i)
            # basic setup of page
            page = etree.Element('html')
            doc = etree.ElementTree(page)
            headElt = etree.SubElement(page,'head')
            bodyElt = etree.SubElement(page,'body')
            titleElt = etree.SubElement(headElt,'title')
            titleElt.text = self.client + ' INSPIRE metadata index page'
            h1Elt = etree.SubElement(bodyElt,'h1')
            h1Elt.text = self.client + ' INSPIRE metadata index page'
            # iterate through files in list to create body of page
            for x in l:
                aElt = etree.SubElement(bodyElt, 'a', href = x)
                aElt.text = x
                brElt = etree.SubElement(bodyElt, 'br')
            outFile = open(os.path.join(outputdir, 'index.html'), 'w')
            doc.write(outFile)
            print "Index.html written successfully"
        except:
            e = sys.exc_info()[1]
            print "Index creation error: %s" % e
            sys.exit(1)

        
def main():

    try:
        gothunderbirdsgo = GeonetworkWAF()
        gothunderbirdsgo.extractzip()
        gothunderbirdsgo.createIndex()
    except (KeyboardInterrupt):
        print "Keyboard interrupt detected. Script aborting"
        raise
    except:
        e = sys.exc_info()[1]
        print "Main Error: %s" % e
        sys.exit(1)

if __name__ == "__main__":
    main()