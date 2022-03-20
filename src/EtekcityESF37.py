#!/usr/bin/env python3

'''A script to connect to an log any body weight measurements
from the Etekcity ESF37 on a Raspberry Pi'''

import os
import sys
import csv
import pwd
import grp
import time
import bluepy
import logging
import datetime
import argparse
import subprocess
import collections

__version__ = '0.1.2'

import bluepy
from scale_handler import ScaleHandler
from systemd_service_writer import *

from logging.handlers import RotatingFileHandler


SERVICE_NAME = 'Etekcity Scale BLE Sniffer'


# application files folder
LOG_FOLDER='/mnt/data/etekcity_scale/'

# the application log
LOG_FILE = os.path.join(LOG_FOLDER, 'logs/application.log')
LOG_SIZE = 10e6    # 10MB
LOG_COUNT = 10     # keep 10 old logs

# the measurements file
MEASUREMENTS = os.path.join(LOG_FOLDER, 'measurements.csv')
MEASUREMENT_HEADERS = ['timestamp', 'weight_kg']


############# Scale Parameters
# 
# To determine the correct settings for your scale, do the following.
# On your raspberry pi, run this: (assuming python 3.9)
#
#  	$ cd /usr/local/lib/python3.9/dist-packages/bluepy
#
# Turn on the scale and run:
#	$ sudo python blescan.py -t 60
#
# After a 60-second scan is completed, look through the list of discovered
# devices, there should be a device with "Complete Local Name" equal to
# "Etekcity Fitness Scale". If the device name is different, change it here:
SCALE_NAME = 'Etekcity Fitness Scale'

# BLE scans will last this long, and print a summary after each full scan.
SCAN_PERIOD = 60 # seconds

# how long to wait after a successful connection before trying again.
COOL_OFF_PERIOD = 10 # seconds


# when scanning for BLE peripherals, print a debug message for all 
# named BLE devices that are found.
LOG_ALL_NAMED_BLE_DEVICES = False



# make sure the required folders exist for logs and measurements.
for path in [MEASUREMENTS, LOG_FILE]:
	dir_name = os.path.dirname(path)
	if not os.path.isdir(dir_name):
		os.makedirs(dir_name)

# change the owner of the logs directory to pi, so when the service launches
# it can actually write to it. (the service is launched as the pi user.)
subprocess.run(['chown', '-R', 'pi:pi', LOG_FOLDER])


############# Logger Setup
#
handler = RotatingFileHandler(LOG_FILE, maxBytes=int(LOG_SIZE), backupCount=LOG_COUNT)
handler.setFormatter(logging.Formatter(fmt='[%(asctime)s.%(msecs)03d] [%(levelname)-7s] %(message)s', 
									   datefmt='%Y-%m-%d %H:%M:%S'))

logging.basicConfig(level=logging.DEBUG, handlers=[handler])
log = logging.getLogger(__name__)


now = lambda: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def record_measurement(measurement):
	'''Record a weight measurement to the measurement log.'''

	file_exists = os.path.isfile(MEASUREMENTS)

	with open(MEASUREMENTS, 'a') as f:
		c = csv.DictWriter(f, fieldnames=MEASUREMENT_HEADERS)

		if not file_exists:
			c.writeheader()

		c.writerow({
			'timestamp': now(),
			'weight_kg': f'{measurement:.1f}'
		})

def advertisement_dict(device):
	'''For a given BLE device, return the advertised data
	as a dictionary'''

	return {
		key: value for _, key, value in device.getScanData()
	}

def complete_local_name(device):
	'''Return the BLE advertisement "Complete Local Name" of a device
	if it is being advertised by the Peripheral, or None if it isn't.'''

	return advertisement_dict(device).get('Complete Local Name')


def provision_bluepy_helper():
	'''Give the bluepy-helper executable permission to use the 
	bluetooth stack without needing to sudo.'''

	bluepy_folder = os.path.dirname(bluepy.__file__)
	bluepy_helper = os.path.join(bluepy_folder, 'bluepy-helper')
	subprocess.run(['setcap', 'cap_net_raw,cap_net_admin+eip', bluepy_helper])



class AbortScanWithDiscoveredDevice(Exception):
	'''An exception raised to abort the scanning process when the 
	device being searched for is found'''

	def __init__(self, scan_entry_object):
		Exception.__init__(self)
		self.scan_entry_object = scan_entry_object

	@property
	def addr(self):
		return self.scan_entry_object.addr
	


class ScanDelegate(bluepy.btle.DefaultDelegate):	
	def log_device(self, device):
		'''Log all discovered information about a device'''
		log.debug(f'Advertisement {device.addr} [{device.rssi} dB]: {advertisement_dict(device)}')

	def handleDiscovery(self, device, is_new_device, is_new_data):
		'''Call back that's executed for every discovered BLE Peripheral'''
		
		name = complete_local_name(device)
		
		if LOG_ALL_NAMED_BLE_DEVICES and name is not None:
			self.log_device(device)

		if name == SCALE_NAME and device.connectable:
			raise AbortScanWithDiscoveredDevice(device)


class EtekcityESF37_Scanner(bluepy.btle.Scanner):
	'''Runs a scan process indefinitely'''

	def __init__(self):
		bluepy.btle.Scanner.__init__(self)
		self.withDelegate(ScanDelegate())

		self._closing = False
		self._stop_time = None

	def close(self):
		'''Stop the scanning after the next cycle'''
		log.info('Scale Sniffer recieved a shutdown request...')
		self._closing = True

	def terminate_scan(self):
		'''Stop the BLE scan process, catering for exceptions'''

		try:
			self.stop()
		except bluepy.btle.BTLEDisconnectError:
			# this is caused by a strange bug in the `bluepy` library.
			# haven't figured out the cause, but this is a valid workaround
			pass

	def do_one_scan(self):
		'''Complete a full scan for BLE devices'''

		self.clear()
		self.start()
		try:
			self.process(SCAN_PERIOD)
		except AbortScanWithDiscoveredDevice as e:
			log.info(f'Aborting BLE device scan, peripheral found @ {e.addr}')
			raise
		finally:
			self.terminate_scan()

		self.print_summary()

	def print_summary(self):
		'''Print a summary of all devices found during a scan period.'''

		devices = self.getDevices()

		device_count = len(devices)
		addr_type_counts = collections.Counter(
			[dev.addrType for dev in devices]).most_common()
		addr_type_str = ", ".join([f"{c} {t}" for t, c in addr_type_counts])

		log.info(f'BLE Devices seen: {device_count} ({addr_type_str})')

	def stable_measure_callback(self, packet):
		'''A callback to be executed when there's a stable 
		measurement callback recieved from the scale.'''

		record_measurement(packet.payload.kg)

	def peripheral_connect(self, scan_entry_object):
		'''Connect to the peripheral and handle the session'''

		sh = ScaleHandler(scan_entry_object, parent=self)
		sh.handle_session()

		log.info(f'Cooling down for {COOL_OFF_PERIOD} seconds after session...')
		time.sleep(COOL_OFF_PERIOD)
		log.info(f'Cool down complete...')

	def run(self):
		while not self._closing:
			try:
				self.do_one_scan()
			except AbortScanWithDiscoveredDevice as e:
				self.peripheral_connect(e.scan_entry_object)
			except KeyboardInterrupt:
				self.close()


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__)
	group = parser.add_mutually_exclusive_group(required=True)

	# run the actual bluetooth daemon, should only be run by the systemd service.
	group.add_argument('--daemon', default=False, action='store_true', help=argparse.SUPPRESS) 

	# install/remove the system service
	group.add_argument('--install', default=False, action='store_true', help='Delete something')
	group.add_argument('--remove', default=False, action='store_true', help='Delete something')

	args = parser.parse_args()


	if args.daemon:
		log.info('')
		log.info('********************************')
		log.info('**        Scale Sniffer       **')
		log.info('********************************')
		log.info('')
		log.info(f'Scale Sniffer v{__version__} starting up...')
		
		scanner = EtekcityESF37_Scanner()
		scanner.run()

		log.info('Scale Sniffer exiting!')

	elif args.install:
		provision_bluepy_helper()
		write_service(name=SERVICE_NAME, 
					  python_path=f'{__file__} --daemon',
					  log_dir=LOG_FOLDER)
		enable_service(name=SERVICE_NAME)
		daemon_reload()
		load_service(name=SERVICE_NAME)
	elif args.remove:
		unload_service(name=SERVICE_NAME)
		remove_service(name=SERVICE_NAME)
		daemon_reload()

	