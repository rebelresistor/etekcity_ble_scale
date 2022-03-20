#!/usr/bin/env python3

'''A packet decoders for the Scale'''

import struct
import logging

from typing import Union
from dataclasses import dataclass, InitVar, field

log = logging.getLogger(__name__)


class AbstractPayload:
	'''This is an abstract base class for all decodable payloads.'''
	pass


@dataclass(frozen=True)
class Weight(AbstractPayload):
	payload: InitVar[bytes]

	kg: float = field(init=False)
	lbs: float = field(init=False)
	is_stable: bool = field(init=False)
	footer: bytes = field(init=False)

	def __post_init__(self, payload):
		object.__setattr__(self, 'kg', 1.0e-2 * struct.unpack('>h', payload[0:2])[0] )
		object.__setattr__(self, 'lbs', 1.0e-2 * struct.unpack('>h', payload[2:4])[0] )
		object.__setattr__(self, 'is_stable', payload[4] > 0x00)
		object.__setattr__(self, 'footer', payload[5:])


# each header is 5-bytes long
PAYLOAD_DECODERS = {
	'FEEFC0A3D0': Weight
}

@dataclass(frozen=True)
class Packet:
	raw_bytes: InitVar[bytes]

	header:   bytes = field(init=False)
	length:   int = field(init=False)
	checksum: int = field(init=False)
	payload: Union[bytes, AbstractPayload] = field(init=False)

	def __post_init__(self, raw_bytes):
		object.__setattr__(self, 'header', raw_bytes[0:5])
		object.__setattr__(self, 'length', raw_bytes[5])
		object.__setattr__(self, 'checksum', raw_bytes[-1])
		object.__setattr__(self, 'payload', raw_bytes[ 6:6+self.length ])
		
		# check if there's a custom decoder for this header
		decoder = PAYLOAD_DECODERS.get(self.hex_header)
		if decoder is not None:
			object.__setattr__(self, 'payload', decoder(self.payload))

	@property
	def hex_header(self) -> str:
		return ''.join(f'{b:02X}' for b in self.header)


if __name__ == '__main__':
	print(Packet(b'\xFE\xEF\xC0\xA3\xD0\x08\x25\x26\x51\xE0\x01\x00\x00\x00\x55'))
