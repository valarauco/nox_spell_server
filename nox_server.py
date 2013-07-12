#! /usr/bin/python2.4
import os, sys
from signal import SIGKILL
import httplib
import re
from lib.cherrypy import _cpwsgiserver
import time
import socket

import popen2
from threading import Condition

class Logger:

    def __init__(self):
        #Load the data
        self.data = {'used': 0, 'data length': 0,
        'da': 0, 'de': 0, 'en': 0, 'es': 0,
        'fr': 0, 'hi': 0, 'hr': 0, 'it': 0,
        'nl': 0, 'no': 0, 'pl': 0, 'pt': 0,
        'fi': 0, 'sv': 0, 'ru': 0, 'id': 0}
        self._loadData()
        self.in_write_mode = False

    def _loadData(self):
        try:
            fp_lang_data = open("lang_data.log", "r")
            for line in open("lang_data.log", "r").readlines():
                vals = line.split("\t")
                self.data[vals[0]] = int(vals[1])
            fp_lang_data.close()
        except IOError:
            pass

    def _writeData(self):
        self.in_write_mode = True
        fp_lang_data = open("lang_data.log", "w")
        for k, v in self.data.items():
            fp_lang_data.write("%s\t%i\n" % (k, v))
        fp_lang_data.close()
        self.in_write_mode = False

    def writeToLog(self, lang, data_length):
        self.data["used"] += 1
        try:
            self.data[lang] += 1
        except:
            self.data[lang] = 0
        self.data["data length"] += data_length
        self._writeData()

Logger = Logger()

class aspell:
    def __init__(self, lang="en"):
        self._f = popen2.Popen3("aspell -a -d %s --encoding=utf-8 --sug-mode=normal" % lang)
        self._f.fromchild.readline() #skip the credit line

    def checkLine(self, line, add_to_offset=0):
        result = []
        line = line.encode("utf-8")
        #Remove aspell special chars
        line = re.sub("\*|\&|@|#|-|\+|!|%|\^", "$", line)
        self._f.tochild.write(line)
        self._f.tochild.write("\n")
        self._f.tochild.flush()

        tries = 1
        while True:
            s = self._f.fromchild.readline()

            tries += 1
            if tries > 200:
                return ""

            if re.match("\s", s) != None:
                break
            else:
                s = s.strip()

                #* = No error
                if s.find("&") == 0:
                    #Get the length of the word
                    s_len = re.search("& (.*?) ", s)
                    word = s_len.group(1)
                    word = unicode(word, "utf-8")
                    length = len(word)    #3 is the "extra chars"

                    #Get the offset and results
                    s = re.sub("& (.*?) \d+ ", "", s)
                    s = s.split(": ")
                    offset = int(s[0]) + add_to_offset
                    result.append((offset, length, s[1].split(", ")[0:5]))
        return result

    def checkText(self, text):
        """
        Returns a list with (offset, length, [suggestions])
        """
        try:
            text_r = unicode(text, "utf-8")
            text = text_r.encode("utf-8")

            result =    []

            line_ofst = 0
            for line in re.split(u"\n", text, re.U):
                line = unicode(line, "utf-8")

                if line == "":
                    line_ofst += 1
                else:
                    result.append(self.checkLine(line, line_ofst))
                    line_ofst += len(line) + 1
        finally:
            self._f.fromchild.close()
            self._f.tochild.close()
        return result

def googleAspellLike(input, lang):
    """
    Input:
    <?xml version="1.0" encoding="utf-8" ?><spellrequest textalreadyclipped="0" ignoredups="0" ignoredigits="1" ignoreallcaps="1"><text>Ths is a tst</text></spellrequest>

    Output:
    <?xml version="1.0"?>
    <spellresult error="0" clipped="0" charschecked="12"><c o="0" l="3" s="1">This    Th's        Thus        Th            HS</c><c o="9" l="3" s="1">test tat         ST St             st</c></spellresult>
    """
    #Get only the text out of the XML
    try:
        input = re.search("<text>((.|\s)*?)</text>", input).group(1)
    except AttributeError:
        print input
        raise

    #Create an aspell object
    speller = aspell(lang)

    corrections = []

    for line_corr in speller.checkText(input):
        for corr in line_corr:
            corrections.append('<c o="%s" l="%s" s="1">%s</c>' % (corr[0], corr[1], "\t".join(corr[2])))

    errors = 0
    if corrections != []:
        errors = 1

    output = ['<?xml version="1.0"?>\n<spellresult error="%i">' % errors]
    output.append("".join(corrections))
    output.append("</spellresult>")
    return "".join(output)

class TooLarge(Exception): pass

class SpellChecker:

    def getLang(self, environ):
        r_text = ""
        lang = environ['QUERY_STRING'].replace("lang=", "")

        if len(lang) != 2:
            lang = "en"
        return lang

    def getPostData(self, environ):
        data_len = int(environ.get('HTTP_CONTENT_LENGTH', 0))
        if data_len > 30000:
            raise TooLarge
        data = environ.get("wsgi.input").read(data_len)
        return data

    def useGoogle(self, data, lang):
        con = httplib.HTTPSConnection("www.google.com")
        con.request("POST", "/tbproxy/spell?lang=%s" % lang, data)
        response = con.getresponse()
        r_text = response.read()
        con.close()
        return [r_text]

    def useAspell(self, data, lang):
        r_text = googleAspellLike(data, lang)
        return [r_text]

    def error(self):
        start_response('502 BAD GATEWAY', [('Content-Type', 'text/html; charset=%s' % "utf-8")])
        return "Not allowed. Contact amix@amix.dk for more info."

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        lang = self.getLang(environ)
        try:
            data = self.getPostData(environ)
        except socket.timeout:
            print "Sockt timeout error"
            start_response('502 BAD GATEWAY', [('Content-Type', 'text/html; charset=%s' % "utf-8")])
            return "Error"
        except TooLarge:
            start_response('502 BAD GATEWAY', [('Content-Type', 'text/html; charset=%s' % "utf-8")])
            return "Error: Too large"

        start_response('200 OK', [('Content-Type', 'text/html; charset=%s' % "utf-8")])

        if path.find("/") == 0:
            if lang in ['da', 'de', 'en', 'es', 'fr', 'it', 'nl', 'pl', 'pt', 'fi', 'sv']:
                return self.useGoogle(data, lang)
            else:
                return self.useAspell(data, lang)
        return "Not found"

wsgi_app = SpellChecker()
def start(port):
    server = _cpwsgiserver.CherryPyWSGIServer(('', port), wsgi_app)
    try:
        print "Server started on port %s" % port
        server.start()
    except KeyboardInterrupt:
        print "Server stopped"
        server.stop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usge is: python nox_server.py PORT"
    else:
        start(int(sys.argv[1]))
