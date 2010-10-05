#!/usr/bin/env python

import os.path
import sys

import getopt
import subprocess
from urlparse import urlparse

def main(argv=None):
   if argv is None:
      argv = sys.argv
   print "ARGS " + str(argv)
   try:
      opts = []
      args = []
      try:
         opts, args = getopt.getopt(argv[1:],  "cu:d:f:a:",
            ["continue","url=", "directory=", "file=", "aria=" ])
      except getopt.error, e:
         print("%s"%str(e))
         sys.exit(1)
      options = ["/usr/bin/aria2c", "--check-certificate=false"]
      # @type mirrors list
      mirrors = readMirrors()
      if mirrors is None or len(mirrors) == 0:
         print  >>sys.stderr, "ERROR: No mirrors found (checked env variable GENTOO_MIRRORS, file " + os.path.expanduser('~') + os.path.sep + 'GENTOO_MIRRORS' + ' and file /etc/make.conf)'
         sys.exit(1)
      #mirrors.append('http://www.voidspace.org.uk/cgi-bin/voidspace')
      # @type url str
      url = None
      # @type name str
      name = None
      for opt, arg in opts:
         if opt in ("-c", "--continue"):
            options.append("-c")
         elif opt in ("-u", "--url"):
            url = arg
         elif opt in ("-d", "--directory"):
            options.append("-d")
            options.append(arg)
         elif opt in ("-f", "--file"):
            # @type arg str
            p = arg.rfind('?file=')
            if p >= 0:
               arg = arg[p+6:]
            options.append("-o")
            options.append(arg)
            name = arg
         elif opt in ("-a", "--aria"):
            options[0] = arg
      if not '-c' in options:
         options.append('--allow-overwrite=true')
      if not '-d' in options:
         options.append("-d")
         options.append('/usr/portage/distfiles')      
      if url is None:
         print  >>sys.stderr, 'ERROR: No url specified'
         sys.exit(1)
      if not '-o' in options:
         print  >>sys.stderr, 'ERROR: No output filename specified'
         sys.exit(1)
      uo = urlparse(url)
      print str(uo)
      address = uo.netloc      
      isMirror = False
      for mirror in mirrors:
         # @type mirror str
         if mirror.find(address) >= 0:
            isMirror = True
            break
      urlStart = len(options)
      options.append("-s")
      options.append(str(len(mirrors)))
      if not isMirror:
         options.append(url)
         status = subprocess.call(options)
      else:
         for mirror in mirrors:
            newUrl = mirror + '/distfiles/' + name
            options.append(newUrl)
         print options[urlStart]
         print options
         status = subprocess.call(options)
      if status != 0:
         options = options[0:urlStart]
         options.append("-s")
         options.append('1')
         options.append('http://www.voidspace.org.uk/cgi-bin/voidspace/downman.py?file=' + name)
         print options
         sys.exit(subprocess.call(options))
      else:
         sys.exit(0)
   except getopt.error, err:
      print >>sys.stderr, err
      sys.exit(1)

def readMirrors():
   mirrors = None
   s = os.environ.get('GENTOO_MIRRORS')
   if not s is None and len(s.strip()) > 0:
      mirrors = s.split(' ')
   if mirrors is None or len(mirrors) == 0:
      filename = os.path.expanduser('~') + os.path.sep + 'GENTOO_MIRRORS'
      if os.path.isfile(filename):
         mirrors = getFileVar(filename)
         if mirrors is None or len(mirrors) == 0:
            mirrors = getFileVar(filename, '')
      if mirrors is None or len(mirrors) == 0:
         mirrors = getFileVar('/etc/make.conf')
   return mirrors

def getFileVar(filename, key ='GENTOO_MIRRORS'):
   fd = None
   try:
      # @type fd file
      fd = open(filename, "r")
      s = fd.readline()
      while s != '':
         # @type s str
         s = s.strip()
         if s.startswith(key):
            l = s.split('=')
            if len(l) > 1: s = l[1] 
            elif len(l) > 0: s = l[0]
            else: s= ''
            s = s.strip()
            s = s.strip('"')
            s = s.strip()
            return s.split(' ')
         s = fd.readline()
      return []
   except:
      print 'Error reading ' + filename
      return None
   finally:
      if not fd is None:
         try:
            fd.close()
         except:
            pass

if __name__ == "__main__":
   sys.exit(main())

