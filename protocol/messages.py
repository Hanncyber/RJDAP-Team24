import hashlib
import struct

WORKER_JOIN = 0
JOIN_ACK = 1        # we added this to know Worker id
HEARTBEAT = 2
TASK_DISPATCH = 3
TASK_RESULT = 4
ACK_RESULT = 5

MSG_NAMES = {
    WORKER_JOIN: 'WORKER_JOIN',
    JOIN_ACK: 'JOIN_ACK',
    HEARTBEAT: 'HEARTBEAT',
    TASK_DISPATCH: 'TASK_DISPATCH',
    TASK_RESULT: 'TASK_RESULT',
    ACK_RESULT: 'ACK_RESULT',
}

FLAG_NO_MORE_TASKS = 0x01

TASK_FMT = '!QQ32s'    
RESULT_FMT = '!BQ'     


def pack_task(start, end, target_digest):
    return struct.pack(TASK_FMT, start, end, target_digest)


def unpack_task(payload):
    """Return (start, end, target_digest)."""
    return struct.unpack(TASK_FMT, payload)


def pack_result(found, value):
    return struct.pack(RESULT_FMT, 1 if found else 0, value)


def unpack_result(payload):
    """Return (found, value)."""
    found, value = struct.unpack(RESULT_FMT, payload)
    return bool(found), value


def digest_of(n):
    """SHA-256 of the 8-byte big-endian encoding of n. The server uses this to build task targets."""
    return hashlib.sha256(n.to_bytes(8, 'big')).digest()