#!/usr/bin/env python3

'''A handler class for the scale'''

import os
import sys
import time
import logging

import bluepy
from packet_decoder import Packet, Weight


log = logging.getLogger(__name__)


#######################################################################
####                           WARNING                             ####
#######################################################################
#
# This script may not work with your scale. The scale sends NOTIFY
# data by itself without being configured to do so after a client 
# connects. Your scale may be programmed differently.
#

# dump all notification data seen over the air to the debug log
LOG_ALL_NOTIFICATION_DATA = False

# how long after the scale stops sending notifications should 
# the script wait before disconnecting. This is based on the scale
# turning itself off after 30 secs of idle time.
NOTIFICATION_TIMEOUT = 27.5    # seconds


def uuid_to_name(uuid):
	'''Convert a characteristic UUID to recognised name'''
	return bluepy.btle.AssignedNumbers.getCommonName(uuid)


class NotificationDelegate(bluepy.btle.DefaultDelegate):
	def __init__(self, parent):
		bluepy.btle.DefaultDelegate.__init__(self)

		self._parent = parent
		self._awaiting_notifications = False

	def begin_listening(self):
		'''Start the notification handler listening for packets.'''
		self._awaiting_notifications = True

	def stop_listening(self):
		'''Stop the notification handler listening for packets.'''
		self._awaiting_notifications = False

	def handleNotification(self, handle_id, data):
		'''Manage all notification data that comes in'''

		if LOG_ALL_NOTIFICATION_DATA:
			log.debug(f'NOTIFY: handle=0x{handle_id:04X} data=' + \
					   ' '.join([f'{b:02X}' for b in data]) )

		if not self._awaiting_notifications:
			return

		p = Packet(data)
		log.debug(repr(p))

		# execute a callback on the parent to record this value if it's stable
		if isinstance(p.payload, Weight):
			if p.payload.is_stable:
				self._parent.stable_measure_callback(p)


class ScaleHandler(bluepy.btle.Peripheral):
	'''A class to handle the session with the BTLE Scale'''

	def __init__(self, scan_entry_object, parent):
		bluepy.btle.Peripheral.__init__(self, None)

		self._parent = parent
		self._scan_entry_object = scan_entry_object

		self._notification_delegate = NotificationDelegate(parent=self._parent)
		self.setDelegate(self._notification_delegate)


	@property
	def se(self):
		return self._scan_entry_object
	
	def check_connectable(self):
		'''Make sure the peripheral is connectable.'''

		if not self.se.connectable:
			log.error(f'Target: {self.se.addr} ' + \
					   'is not connectable')
			raise RuntimeError('target not connectable')

	def enumerate_services(self):
		'''Attempt to download all services and characteristics 
		from the device.'''

		log.debug('')
		log.debug('Enumerating services:')
		for service in self.services:
			log.debug(f'    {service}:')

			for chara in service.getCharacteristics():
				log.debug(f'        {chara}, handle={hex(chara.handle)}, supports {chara.propertiesToString()}')
				if chara.supportsRead():
					try:
						log.debug(f'          -> {repr(chara.read())}')
					except BTLEException as e:
						log.debug(f'          -> {e}')
		log.debug('')

	def consume_notifications(self):
		'''Attempt to download all services and characteristics 
		from the device.'''

		# log.debug('Enabling notifications...')
		# service = self.getServiceByUUID( 0x1910 )
		# chara = service.getCharacteristics( 0x2C12 ).pop()
		# chara.write( b'\1\0' )

		log.debug('Waiting for notifications...')

		self._notification_delegate.begin_listening()

		while self.waitForNotifications(NOTIFICATION_TIMEOUT):
			continue

		self._notification_delegate.stop_listening()

		log.debug('Timeout while waiting for new notifications...')

	def handle_session(self):
		'''Complete the entire session speaking to the device.'''

		try:
			self.check_connectable()

			log.info(f'Connecting to {self.se.addr} ({self.se.addrType} address)')
			self.connect(self.se)

			# dump all services to the log -- can be commented out if not needed
			self.enumerate_services()

			self.consume_notifications()

		except bluepy.btle.BTLEException as e:
			log.error(f'Aborting (BTLE exception): {e.__class__.__name__}("{str(e)}")')

		except Exception as e:
			log.error(f'Aborting (General exception):\n', exc_info=True)

		finally:
			try:
				log.info(f'Disconnecting from {self.se.addr}')
				self.disconnect()
			except:
				pass

