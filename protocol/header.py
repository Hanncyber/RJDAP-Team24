import struct
from collections import namedtuple

from protocol.checksum import crc32
from protocol.messages import MSG_NAMES

MAGIC = 0x524A
VERSION = 1
MAX_PAYLOAD = 512

HEADER_FMT = '!HBBBHIBHI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 18 bytes 

Packet = namedtuple('Packet', 'msg_type flags worker_id task_id attempt payload')


class ProtocolError(Exception):
    """3ashan n2fsh el corrupted packets w n drop the packet."""


def pack_packet(msg_type, worker_id=0, task_id=0, attempt=0, payload=b'', flags=0):
    if len(payload) > MAX_PAYLOAD:
        raise ValueError('payload too large')
    head = struct.pack(HEADER_FMT, MAGIC, VERSION, msg_type, flags,
                       worker_id, task_id, attempt, len(payload), 0)
    checksum = crc32(head + payload)
    return head[:-4] + struct.pack('!I', checksum) + payload


def unpack_packet(data):
    if len(data) < HEADER_SIZE:
        raise ProtocolError('packet shorter than header')
    magic, ver, mtype, flags, wid, tid, att, plen, checksum = struct.unpack(
        HEADER_FMT, data[:HEADER_SIZE])
    if magic != MAGIC:
        raise ProtocolError('bad magic')
    if ver != VERSION:
        raise ProtocolError('unsupported version %d' % ver)
    if mtype not in MSG_NAMES:
        raise ProtocolError('unknown message type %d' % mtype)
    payload = data[HEADER_SIZE:]
    if len(payload) != plen or plen > MAX_PAYLOAD:
        raise ProtocolError('bad payload length')
    zeroed = data[:HEADER_SIZE - 4] + b'\x00\x00\x00\x00'
    if crc32(zeroed + payload) != checksum:
        raise ProtocolError('checksum mismatch')
    return Packet(mtype, flags, wid, tid, att, payload)