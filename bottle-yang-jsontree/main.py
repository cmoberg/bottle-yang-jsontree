#!/usr/bin/env python

import os, sys, cgi, argparse
import optparse
import logging

from datetime import datetime
from functools import wraps

from bottle import route, run, install, template, request, response, static_file, error, debug
from bottle import *

import pyang
from pyang import plugin


__author__ = 'camoberg@cisco.com'
__copyright__ = "Copyright (c) 2017, Carl Moberg, camoberg@cisco.com"
__license__ = "New-style BSD"
__email__ = "camoberg@cisco.com"
__version__ = "0.1"

debug(True)

logger = logging.getLogger('yang-jsontree')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('yangjsontree.log')
formatter = logging.Formatter('%(msg)s')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_to_logger(fn):
    '''
    Wrap a Bottle request so that a log line is emitted after it's handled.
    (This decorator can be extended to take the desired logger as a param.)
    '''
    @wraps(fn)
    def _log_to_logger(*args, **kwargs):
        request_time = datetime.now()
        actual_response = fn(*args, **kwargs)
        # modify this to log exactly what you need:
        logger.info('%s %s %s %s %s' % (request.remote_addr,
                                        request_time,
                                        request.method,
                                        request.url,
                                        response.status))
        return actual_response
    return _log_to_logger

def get_plugin_by_name(name):
    for p in plugin.plugins:
        if p.name == name:
            return p
    return False

class Writer(object):
	def __repr__(self):
		return self.retval
	def write(self, string):
		self.retval = string

@route('/')
def validator():
	return template('main')

@route('/transform', method="POST")
def transform_module():
	module = request.body.read()

	logging.info("Content-type is:", request.content_type)

	response.content_type = 'application/json'

	repos = pyang.FileRepository()
	ctx = pyang.Context(repos)

	modules = []
	modules.append(ctx.add_module("upload module", module))

	plugin.init()
	p = get_plugin_by_name('jsontree')

	op = optparse.OptionParser()
	p.add_opts(op)
	(o, args) = op.parse_args()
	ctx.opts = o

	wr = Writer()
	try:
		p.emit(ctx, modules, wr)
	except:
		bottle.abort(500, 'Internal Server Error')

	return str(wr)

@route('/static/:path#.+#', name='static')
def static(path):
	return static_file(path, root='static')

@route('/about')
def about():
	return(template('about'))

@error(404)
def error404(error):
	return 'Nothing here, sorry.'

if __name__ == '__main__':
	port = 8080

	parser = argparse.ArgumentParser(description='A YANG to JSON tree transformer.')
	parser.add_argument('-p', '--port', dest='port', type=int, help='Port to listen to (default is 8080)')
	parser.add_argument('-d', '--debug', help='Turn on debugging output', action="store_true")
	args = parser.parse_args()

	if args.port:
		port = args.port

	if args.debug:
		debug = True

	install(log_to_logger)

	run(server='cherrypy', host='0.0.0.0', port=port)
