
import threading
import time

from protocol.messages import MSG_NAMES


class PacketLogger:
    def __init__(self, path):
        self._f = open(path, 'w', buffering=1)
        self._lock = threading.Lock()
        self._f.write('timestamp,direction,msg_type,task_id,worker_id,attempt,payload_len,peer\n')

    def log(self, direction, pkt, peer):
        
        line = '%.6f,%s,%s,%d,%d,%d,%d,%s:%s\n' % (
            time.time(), direction, MSG_NAMES[pkt.msg_type], pkt.task_id,
            pkt.worker_id, pkt.attempt, len(pkt.payload), peer[0], peer[1])
        with self._lock:
            self._f.write(line)

    def close(self):
        self._f.close()