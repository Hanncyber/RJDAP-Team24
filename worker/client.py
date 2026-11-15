import argparse
import os
import socket
import struct
import threading
import time

from protocol.header import Packet, ProtocolError, pack_packet, unpack_packet
from protocol.logger import PacketLogger
from protocol.messages import (ACK_RESULT, FLAG_NO_MORE_TASKS, HEARTBEAT, JOIN_ACK,
                               TASK_DISPATCH, TASK_RESULT, WORKER_JOIN,
                               pack_result, unpack_task)
from worker.compute import compute_task


def run(host, port, log_path, timeout, max_retries, heartbeat, idle_timeout):
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    server = (socket.gethostbyname(host), port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    log = PacketLogger(log_path)
    worker_id = 0                 # 0 until the server assigns one

    def send(msg_type, task_id=0, attempt=0, payload=b'', flags=0):
        raw = pack_packet(msg_type, worker_id, task_id, attempt, payload, flags)
        sock.sendto(raw, server)
        log.log('SEND', Packet(msg_type, flags, worker_id, task_id, attempt, payload), server)

    def receive(wait):
        deadline = time.time() + wait
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            sock.settimeout(remaining)
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                return None
            except ConnectionResetError:
                continue                       # Windows: server port not open yet
            if addr != server:
                continue
            try:
                pkt = unpack_packet(data)
            except ProtocolError:
                continue                       # corrupted: drop it like a lost packet
            log.log('RECV', pkt, addr)
            return pkt


    pending = None                             # a TASK_DISPATCH that arrived early
    for _ in range(max_retries * 5):
        send(WORKER_JOIN)
        reply = receive(timeout)
        if reply is not None and reply.msg_type in (JOIN_ACK, TASK_DISPATCH):
            worker_id = reply.worker_id
            if reply.msg_type == TASK_DISPATCH:
                pending = reply
            break
    else:
        print('Worker: no answer from server, giving up.')
        log.close()
        return False

    stop_heartbeat = threading.Event()
    if heartbeat > 0:
        def beat():
            while not stop_heartbeat.wait(heartbeat):
                try:
                    send(HEARTBEAT)
                except OSError:
                    pass
        threading.Thread(target=beat, daemon=True).start()


    tasks_done = 0
    ok = True
    try:
        if reply.msg_type == JOIN_ACK and reply.flags & FLAG_NO_MORE_TASKS:
            return True                        # nothing to do
        while True:
            if pending is not None:
                pkt, pending = pending, None
            else:
                pkt = receive(idle_timeout)
                if pkt is None:
                    print('Worker %d: no task received for %.0f s, stopping.'
                          % (worker_id, idle_timeout))
                    ok = False
                    break
            if pkt.msg_type == ACK_RESULT:
                if pkt.flags & FLAG_NO_MORE_TASKS:
                    break                      # late repeat of the final ACK
                continue
            if pkt.msg_type != TASK_DISPATCH:
                continue                       # e.g. a repeated JOIN_ACK

            try:
                start, end, digest = unpack_task(pkt.payload)
            except struct.error:
                continue
            found, value = compute_task(start, end, digest)
            result = pack_result(found, value)

            # Send the result; resend it if no ACK arrives before the timeout.
            answer = None
            for _ in range(max_retries):
                send(TASK_RESULT, pkt.task_id, pkt.attempt, result)
                deadline = time.time() + timeout
                while answer is None:
                    reply = receive(deadline - time.time())
                    if reply is None:
                        break                  # timeout: send the result again
                    if reply.msg_type == ACK_RESULT and reply.task_id == pkt.task_id:
                        answer = reply
                    elif reply.msg_type == TASK_DISPATCH and reply.task_id != pkt.task_id:
                        answer = reply         # the server only sends the next task after
                                               # it has our result, so this counts as an ACK
                if answer is not None:
                    break
            if answer is None:
                print('Worker %d: no ACK for task %d, giving up.' % (worker_id, pkt.task_id))
                ok = False
                break
            tasks_done += 1
            if answer.msg_type == TASK_DISPATCH:
                pending = answer
            elif answer.flags & FLAG_NO_MORE_TASKS:
                break
    finally:
        stop_heartbeat.set()
        log.close()
    print('Worker %d finished: %d tasks computed' % (worker_id, tasks_done), flush=True)
    return ok


def main():
    ap = argparse.ArgumentParser(description='RJDAP worker')
    ap.add_argument('--server', default='localhost')
    ap.add_argument('--port', type=int, default=12000)
    ap.add_argument('--log', default='logs/worker.csv')
    ap.add_argument('--timeout', type=float, default=0.2, help='seconds to wait for an ACK')
    ap.add_argument('--max-retries', type=int, default=10)
    ap.add_argument('--heartbeat', type=float, default=1.0, help='seconds; 0 turns it off')
    ap.add_argument('--idle-timeout', type=float, default=10.0)
    args = ap.parse_args()
    ok = run(args.server, args.port, args.log, args.timeout, args.max_retries,
             args.heartbeat, args.idle_timeout)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
