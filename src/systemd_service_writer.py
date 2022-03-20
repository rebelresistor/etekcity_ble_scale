#!/usr/bin/env python3

'''A module to write systemd services'''

import os
import subprocess

__all__ = [
	'write_service',
	'remove_service',
	'load_service',
	'enable_service',
	'unload_service',
	'daemon_reload'
]



TEMPLATE = '''
[Unit]
Description={name}
After=bluetooth.target

[Service]
ExecStart=/usr/bin/python {py_path}
WorkingDirectory={log_dir}
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
'''

SYSTEMD_SERVICE_NAME = '/lib/systemd/system/{name}.service'

def build_systemd_service_path(name):
	'''Build a suitable systemd service name'''
	n = name.lower().replace(' ', '-')
	return SYSTEMD_SERVICE_NAME.format(name=n)


def write_service(name, python_path, log_dir):
	'''Create the service file for this script'''

	try:
		with open(build_systemd_service_path(name), 'w') as f:
			f.write(TEMPLATE.format(name=name,
									py_path=python_path,
									log_dir=log_dir))
	except OSError:
		log.error('OS error while writing the service file, did you sudo?\n', exc_info=True)
		raise

def remove_service(name):
	'''Create the service file for this script'''
	
	service_path = build_systemd_service_path(name)
	try:
		if os.path.isfile(service_path):
			os.remove(service_path)
	except OSError:
		log.error('OS error while deleting the service file, did you sudo?\n', exc_info=True)
		raise


def enable_service(name):
	'''Load the given service name'''
	service_name = os.path.basename(build_systemd_service_path(name))
	try:
		subprocess.run(['systemctl', 'enable', service_name])
	except subprocess.CalledProcessError:
		log.error('Error while loading the service into systemd:\n', exc_info=True)

def load_service(name):
	'''Load the given service name'''
	service_name = os.path.basename(build_systemd_service_path(name))
	try:
		subprocess.run(['systemctl', 'enable', service_name])
		subprocess.run(['systemctl', 'start', service_name])
	except subprocess.CalledProcessError:
		log.error('Error while loading the service into systemd:\n', exc_info=True)


def unload_service(name):
	'''Load the given service name'''
	service_name = os.path.basename(build_systemd_service_path(name))
	try:
		subprocess.run(['systemctl', 'stop', service_name])
		subprocess.run(['systemctl', 'disable', service_name])
	except subprocess.CalledProcessError:
		log.error('Error while disabling the service in systemd:\n', exc_info=True)


def daemon_reload():
	'''Load the given service name'''
	try:
		subprocess.run(['systemctl', 'daemon-reload'])
	except subprocess.CalledProcessError:
		log.error('Error while reloading daemons on disk in systemd:\n', exc_info=True)
		