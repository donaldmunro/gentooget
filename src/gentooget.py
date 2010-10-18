#!/usr/bin/env python

#gentooget - Gentoo portage download script
#    Copyright (C) 2010  Donald Munro
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/gpl-3.0.html>.
#
# Patches
#  AlecM (github.com/AlecM) - Made downman optional
#  AlecM (github.com/AlecM) - Added color output to distinquish aria output from script output

import os
import os.path
import sys
import errno
import traceback
import getopt
import shlex
import subprocess
import re
import time
from urlparse import urlparse
#from urllib.parse import urlparse # Python 3

VERSION = "0.2"
DEBUG = VERBOSE = False
GENTOO_MIRRORS = INTERNATIONAL_MIRRORS = LOCAL_MIRRORS = INTERNAL_MIRRORS = []

def usage():
   global VERSION
   print("gentooget " + VERSION)
   print("""
gentooget is a replacement download script for Gentoo Linux portage which acts as a facade for the
aria2 downloader (http://aria2.sourceforge.net/) to enable simultaneous multi-part downloads from
different Gentoo mirrors thus improving download speed.
It also provides a facility to switch between 2 different (probably ADSL) Internet connections. This
is desirable in dumbassed countries where you pay per Gb for ADSL and the costs for local only
are a order of magnitude cheaper than international access. This allows use of a local connection
where possible but if a download fails where the file is not available on a local mirror then
gentooget switches to the international connection, downloads the file and then switches back to the
local connection.

gentooget [-h --help] [-v --version] [-V --verbose] [-D --debug] [-T --true] [-c --continue]  [-u --url=]
          [-d directory=] [-f --file=] [-a --aria=] [-l --local=] [-i --international=]
     -T --true           : Always return success even if a download fails.
     -h --help           : Display help.
     -c --continue       : Continue download (if not specified then existing file will be overwritten)
                           Specify this in the RESUMECOMMAND variable in make.conf
     -w --downman        : Attempt to use Downman if the package is not found anywhere else.
     -u --url=           : The url of the file to be downloaded. This should be passed as ${URI}
                           in the FETCHCOMMAND and RESUMECOMMAND variables in the make.conf file.
     -d directory=       : The destination directory to download the file to.
     -f --file=          : The name of the destination file (full path is specified by -d and -f).
     -a --aria=          : Path to the aria2 binary if it is not in the PATH.
     -l --local=         : Path to a script or executable that switches to a local Internet
                           connection.
     -i --international= : Path to a script or executable that switches to a international
                           Internet  connection.
     -I --interface=     : The interface being switched by --local/--international (defaults to ppp0)
                           If it is not ppp0 then it must be specified otherwise gentooget cannot
                           check to see if the interface is up before continuing download.

Enviroment Variables
====================
GENTOO_MIRRORS        : Contains a list of urls of mirrors for Gentoo portage dist locations
                        separated by a space. This is a Portage standard variable and is used if
                        local and international is not specified in the command line.
Example: GENTOO_MIRRORS="http://ftp.heanet.ie/pub/gentoo/ ftp://ftp.is.co.za//mirror/ftp.gentoo.org"

LOCAL_MIRRORS         : Contains a list of urls of local mirrors for Gentoo portage dist locations
Example: LOCAL_MIRRORS="ftp://ftp.is.co.za//mirror/ftp.gentoo.org ftp://ftp.up.ac.za/mirrors/gentoo.org/gentoo"

INTERNATIONAL_MIRRORS : Contains a list of urls of international mirrors for Gentoo portage dist locations
Example: INTERNATIONAL_MIRRORS="http://ftp.heanet.ie/pub/gentoo/ ftp://mirrors.rit.edu/gentoo/"

INTERNAL_MIRRORS      : Contains a list of urls of internal network urls to distfiles directories
Example: INTERNAL_MIRRORS="ftp://192.168.0.1/portage"
Internal mirrors are currently assumed to be on a different interface eg eth1 as opposed to ppp0
therefore no connection switching is applied before internal fetches. 

Files
=====
~/GENTOO_MIRRORS
May contain the GENTOO_MIRRORS, LOCAL_MIRRORS and INTERNATIONAL_MIRRORS variables (see Enviroment Variables)
Example
cat ~/GENTOO_MIRRORS
GENTOO_MIRRORS="http://ftp.heanet.ie/pub/gentoo/ ftp://ftp.is.co.za//mirror/ftp.gentoo.org"
LOCAL_MIRRORS="ftp://ftp.is.co.za//mirror/ftp.gentoo.org ftp://ftp.up.ac.za/mirrors/gentoo.org/gentoo"
INTERNATIONAL_MIRRORS="http://ftp.heanet.ie/pub/gentoo/ ftp://mirrors.rit.edu/gentoo/"

/etc/make.conf
This is the Portage make.conf file. It should include the GENTOO_MIRRORS variable and optionally
the LOCAL_MIRRORS and INTERNATIONAL_MIRRORS variables if local/international access is used and these
are not specified as environment variables or in ~/GENTOO_MIRRORS.
Additionally the FETCHCOMMAND and RESUMECOMMAND variables must be changed to use gentooget.

Example make.conf (only showing entries pertinent to gentooget)
FETCHCOMMAND="/usr/bin/gentooget.py -V -D -d '${DISTDIR}' -f '${FILE}' -u '${URI}'"
RESUMECOMMAND="/usr/bin/gentooget.py -V -D -c -d '${DISTDIR}' -f '${FILE}' -u '${URI}'"
GENTOO_MIRRORS="ftp://ftp.is.co.za//mirror/ftp.gentoo.org ftp://ftp.up.ac.za/mirrors/gentoo.org/gentoo http://ftp.heanet.ie/pub/gentoo/"

Example make.conf using local/international switching
FETCHCOMMAND="/usr/bin/gentooget.py -V -D -d '${DISTDIR}' -f '${FILE}' -u '${URI}' -l /etc/ppp/local -i /etc/ppp/shaped"
RESUMECOMMAND="/usr/bin/gentooget.py -V -D -c -d '${DISTDIR}' -f '${FILE}' -u '${URI}' -l /etc/ppp/local -i /etc/ppp/shaped"
GENTOO_MIRRORS="ftp://ftp.is.co.za//mirror/ftp.gentoo.org ftp://ftp.up.ac.za/mirrors/gentoo.org/gentoo http://ftp.heanet.ie/pub/gentoo/"
LOCAL_MIRRORS="ftp://ftp.is.co.za//mirror/ftp.gentoo.org ftp://ftp.up.ac.za/mirrors/gentoo.org/gentoo"
INTERNATIONAL_MIRRORS="http://ftp.heanet.ie/pub/gentoo/ ftp://mirrors.rit.edu/gentoo/"
(assumes the scripts /etc/ppp/local.sh and  /etc/ppp/international.sh switch to local and international
Internet connections)

Notes
Emerge will call gentooget as user portage so if using local/international switching with ADSL the script
that does the switching will probably have to use sudo at least when stopping and starting PPPOE eg
sudo pppoe-start /etc/ppp/pppoe.conf.local. In this case user portage will need to be a real user ie
not have /bin/false for its shell in /etc/passwd and user portage will need to be added to group
wheel (/etc/group). On a single user desktop system you can use group based sudo in /etc/sudoers. For example
/etc/passwd:  portage:x:250:250:portage:/var/tmp/portage:/bin/bash
/etc/group:   wheel:x:10:root,portage
/etc/sudoers: %wheel ALL=(ALL) NOPASSWD: ALL
A more secure solution would be to allow user portage per command access, for example:
/etc/sudoers: portage  localhost = /usr/sbin/pppoe-start /usr/sbin/pppoe-stop (see <http://www.gentoo.org/doc/en/sudo-guide.xml>)
""")

def colorstr(message, color):
   return '\033[' + color + 'm' + message + '\033[0m'

# Python 3 compatibility helper
def printErr(message):
   print  >>sys.stderr, red() + message
#   print(red() + message, file=sys.stderr)

def main(argv=None):
   global  VERSION, VERBOSE, DEBUG, GENTOO_MIRRORS, INTERNATIONAL_MIRRORS, LOCAL_MIRRORS, INTERNAL_MIRRORS
   if argv is None:
      argv = sys.argv
   try:
      opts = []
      args = []
      try:
         opts, args = getopt.getopt(argv[1:],  "hvVDTwcu:d:f:a:l:i:I:",
            ['help', 'version', 'verbose', 'debug', 'true', 'downman', "continue","url=", "directory=", "file=",
            "aria=", 'local=', 'international=', 'interface=' ])
      except getopt.error, e:
#         except getopt.error as e: #Python 3
         printErr("%s"%str(e))
         sys.exit(1)
      options = ["/usr/bin/aria2c", "--check-certificate=false"]      
      # @type url str
      url = None
      # @type name str
      name = None
      local = None
      international = None
      interface = 'ppp0'
      alwaysSucceed = False
      useDownman = False
      mustSwitch = False
      dir = '/usr/portage/distfiles'
      for opt, arg in opts:
         if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
         elif opt in ("-v", "--version"):
            print("gentooget " + VERSION)
            sys.exit(0)
         elif opt in ("-V", "--verbose"):
            VERBOSE = True
         elif opt in ("-D", "--debug"):
            DEBUG = True
         elif opt in ("-T", "--true"):
            alwaysSucceed = True
         elif opt in ("-w", "--downman"):
            useDownman = True
         elif opt in ("-c", "--continue"):
            options.append("-c")
         elif opt in ("-u", "--url"):
            url = arg
         elif opt in ("-d", "--directory"):
            options.append("-d")
            dir = arg
            options.append(dir)
         elif opt in ("-f", "--file"):
            # @type arg str
            p = arg.rfind('?file=')
            if p >= 0:
               arg = arg[p+6:]
            options.append("-o")
            options.append(arg)
            name = arg
         elif opt in ("-a", "--aria"):
            if os.path.isfile(arg):
               options[0] = arg
            else:
               printErr('ERROR: ' + arg + " does not exist or is not a file")
               sys.exit(1)
         elif opt in ("-l", "--local"):
            if os.path.isfile(arg):
               local = arg
            else:
               printErr('ERROR: Local script ' + arg + " does not exist or is not a file")
               sys.exit(1)
         elif opt in ("-i", "--international"):
            if os.path.isfile(arg):
               international = arg
            else:
               printErr('ERROR: International script ' + arg + " does not exist or is not a file")
               sys.exit(1)
         elif opt in ("-I", "--interface"):
               interface = arg
      
      if not '-d' in options:
         options.append("-d")
         options.append(dir)
      if url is None:
         printErr('ERROR: No url specified')
         sys.exit(1)
      if not '-o' in options:
         printErr('ERROR: No output filename specified')
         sys.exit(1)
      if not '-c' in options:
         options.append('--allow-overwrite=true')
      fullPath = os.path.join(dir, name)
      mustSwitch = not local is None and not international is None
      if local is None and not international is None:
         printErr("If a international script (%s) is specified then a local script must also be specified"
         % (international,))
         sys.exit(1)
      if not local is None and international is None:
         printErr("If a local script (%s) is specified then an international script must also be specified"
         % (local,))
         sys.exit(1)
      if DEBUG:
         print(concatOpts(argv))
      # @type mirrors list      
      GENTOO_MIRRORS = readMirrors()
      INTERNAL_MIRRORS = readMirrors('INTERNAL_MIRRORS')
      if mustSwitch:
         LOCAL_MIRRORS = readMirrors('LOCAL_MIRRORS')
         if LOCAL_MIRRORS is None or len(LOCAL_MIRRORS) == 0:
            printErr("ERROR: No local mirrors found (checked env variable LOCAL_MIRRORS, file " \
            + os.path.expanduser('~') + os.path.sep + 'GENTOO_MIRRORS' + ' and file /etc/make.conf)')
            sys.exit(1)
         INTERNATIONAL_MIRRORS = readMirrors('INTERNATIONAL_MIRRORS')
         if INTERNATIONAL_MIRRORS is None or len(INTERNATIONAL_MIRRORS) == 0:
            printErr("ERROR: No international mirrors found (checked env variable INTERNATIONAL_MIRRORS, file " \
            + os.path.expanduser('~') + os.path.sep + 'GENTOO_MIRRORS' + ' and file /etc/make.conf)')
            sys.exit(1)
         mirrors = LOCAL_MIRRORS
         if VERBOSE:
            print('Switch to local script: %s using mirrors: %s' % (local, str(LOCAL_MIRRORS)))
            print('Switch to international script: %s using mirrors: %s' % (international, str(INTERNATIONAL_MIRRORS)))
            print("Monitoring interface: " + interface)
      else:
         mirrors = GENTOO_MIRRORS
         if (mirrors is None or len(mirrors) == 0) and \
            (INTERNAL_MIRRORS is None or len(INTERNAL_MIRRORS) == 0):
            printErr("WARNING: No mirrors found (checked env variable GENTOO_MIRRORS, file " \
            + os.path.expanduser('~') + os.path.sep + 'GENTOO_MIRRORS' + ' and file /etc/make.conf)')

      urlStart = len(options)
      uo = urlparse(url)      
      address = uo.netloc
      status = 1
      # Try internal first if there are any
      if not INTERNAL_MIRRORS is None and len(INTERNAL_MIRRORS) > 0:
         for mirror in INTERNAL_MIRRORS:
            newUrl = mirror + '/distfiles/' + name
            options.append(newUrl)
         if DEBUG:
            print(green() + 'Using internal mirror:')
            print(concatOpts(options))
         status = download(options, fullPath)
      if status != 0: # Next try local or default if not using local/international switching
         if mustSwitch:
         # If using using local/international switching start in local
            ip = switchConnection(local, interface)
            if ip is None:
               printErr('Error: Could not switch to local connection using %s (checking interface %s)' %
               (local, interface))
               sys.exit(1)
            else:
               if VERBOSE:
                  print("Switched to local connection using IP " + ip)
         isMirror = appendMirrors(url, address, name, options, mirrors)
         if DEBUG:
            print(green() + concatOpts(options))
         if mustSwitch:
            if isMirror: #External url is probably not local
               if DEBUG:
                  print(green() + 'Using local mirror')
               status = download(options, fullPath)
         else:
            status = download(options, fullPath)
      if status != 0 and mustSwitch:
         # If using using local/international switching try international next
         if VERBOSE:
            print(yellow() + "Downloading %s/%s failed on local connection. Attempting international" % (address, name))
         options = options[0:urlStart]
         appendMirrors(url, address, name, options, INTERNATIONAL_MIRRORS)
         ip = switchConnection(international, interface) # Switch to international
         if not ip is None:
            try:
               if VERBOSE:
                  print(green() + "Switched to international (%s) " % (ip,))
               if DEBUG:
                  print(green() + 'Using international mirror:')
                  print(green() + concatOpts(options))
               status = download(options, fullPath)
            finally:
               ip = switchConnection(local, interface) # Switch back to local
               if ip is None:
                  print(red() + "Failed to switch back to local")
                  sys.exit(1)
               if VERBOSE:
                  print(green() + "Switched to local (%s) " % (ip,))
      if status != 0 and useDownman:
         if VERBOSE:
            print(yellow() + "Downloading %s/%s failed. Attempting Portage downman" % (address, name))
         options = options[0:urlStart]
#         options.append("-s")
#         options.append('1').
         options.append('http://www.voidspace.org.uk/cgi-bin/voidspace/downman.py?file=' + name)
         if DEBUG:
            print(green() + 'Using downman:')
            print(green() + concatOpts(options))
         status = download(options, fullPath)
      if alwaysSucceed:
         sys.exit(0)
      sys.exit(status)
   except getopt.error, err:
#   except getopt.error as err:
      printErr(err)
      sys.exit(1)

def download(options, fullPath):
   if os.path.exists(fullPath + '.aria2'):
      os.remove(fullPath + '.aria2') # If not deleted aria retries using the last failed url regardless of the specified urls
   status = subprocess.call(options)
   if not os.path.exists(fullPath):
      return 1
   if os.path.getsize(fullPath) == 0:
      return 2
   return status

def readMirrors(var = 'GENTOO_MIRRORS'):
   mirrors = []
   s = os.environ.get(var)
   if not s is None and len(s.strip()) > 0:
      mirrors = s.split(' ')
   if mirrors is None or len(mirrors) == 0:
      filename = os.path.expanduser('~') + os.path.sep + 'GENTOO_MIRRORS'
      if os.path.isfile(filename):
         mirrors = getFileVar(filename, var)
      if mirrors is None or len(mirrors) == 0:
         if os.path.isfile('/etc/make.conf'):
            mirrors = getFileVar('/etc/make.conf', var)
         else:
            printErr('/etc/make.conf not found !')
   return mirrors

def getFileVar(filename, var ='GENTOO_MIRRORS'):
   fd = None
   try:
      # @type fd file
      fd = open(filename, "r")
      s = fd.readline()
      while s != '':
         # @type s str
         s = s.strip()
         if s.startswith(var):
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
      printErr('Error reading ' + filename)
      return None
   finally:
      if not fd is None:
         try:
            fd.close()
         except:
            pass

def appendMirrors(url, address, name, options, mirrors):
   global GENTOO_MIRRORS, INTERNATIONAL_MIRRORS, LOCAL_MIRRORS, INTERNAL_MIRRORS
   isMirror = False
   allMirrors = []
   if not INTERNAL_MIRRORS is None and len(INTERNAL_MIRRORS) > 0:
      allMirrors.extend(INTERNAL_MIRRORS)
   allMirrors.extend(GENTOO_MIRRORS)
   if not LOCAL_MIRRORS is None and len(LOCAL_MIRRORS) > 0:
      allMirrors.extend(LOCAL_MIRRORS)
   if not INTERNATIONAL_MIRRORS is None and len(INTERNATIONAL_MIRRORS) > 0:
      allMirrors.extend(INTERNATIONAL_MIRRORS)
   for mirror in allMirrors:
      # @type mirror str
      if mirror.find(address) >= 0:
         isMirror = True
         break   
   if not isMirror: #A hardcoded download location eg http://releases.mozilla.org/
      options.append(url)
   else:
#      options.append("-s")
#      options.append(str(len(mirrors)))
      for mirror in mirrors:
         newUrl = mirror + '/distfiles/' + name
         options.append(newUrl)
   return isMirror

INTERFACE_RE = re.compile(r".*inet addr:(\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b) .*")

def interfaceIp(interface):
   global INTERFACE_RE
   process = None
   try:
      process = subprocess.Popen(['/sbin/ifconfig', interface], stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, bufsize=4096)
   except:
      printErr("Exception executing ifconfig " + interface)
      if not process is None:
         try:
            process.kill()
         except:
            pass
      traceback.print_exc()
   if process is None:
      return None
   status = process.wait()
   if status != 0:
      return None
   output = process.communicate()[0]
   # @type output str
   lines = output.splitlines()
   ip = None
   for line in lines:
      m = INTERFACE_RE.match(line)
      if not m is None:
         ip = m.group(1)
         break
   return ip

def switchConnection(script, interface):
   status = 1
   while True:
      try:
         status = subprocess.call(shlex.split(script))
         break
      except OSError, e:
         if e.errno == errno.ENOEXEC: # Try as shell script
            script = '/bin/bash ' + script
            continue
         else:
            printErr("Exception executing %s (%s)" % (script, str(shlex.split(script))))
            traceback.print_exc()
            return None
      except:
         printErr("Exception executing %s (%s)" % (script, str(shlex.split(script))))
         traceback.print_exc()
         return None
   ip = interfaceIp(interface)
   if ip is None:
      print(yellow() + "Waiting for interface " + interface)
   while ip is None:
      time.sleep(3)
      ip = interfaceIp(interface)      
   print(green() + "script %s interface %s ip %s connected" % (script, interface, ip))
   return ip

def concatOpts(opts):
   ret = ''
   for opt in opts:
      ret += opt + ' '
   return ret

def red(message = ' * '):
   return colorstr(message, '91')

def green(message = ' * '):
   return colorstr(message, '92')

def yellow(message = ' * '):
   return colorstr(message, '93')

if __name__ == "__main__":
   sys.exit(main())

