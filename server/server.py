import argparse
import os
import socket
import time

from protocol.header import Packet, ProtocolError, pack_packet, unpack_packet
from protocol.logger import PacketLogger
from protocol.messages import (ACK_RESULT, FLAG_NO_MORE_TASKS, HEARTBEAT, JOIN_ACK,
                               TASK_DISPATCH, TASK_RESULT, WORKER_JOIN,
                               pack_task, unpack_result)
from server.task_queue import TaskQueue
from server.worker_registry import WorkerRegistry

LINGER_SECONDS = 0.5   


class Server:
    def __init__(self, host, port, num_tasks, range_size, seed, log_path, results_path):
        for path in (log_path, results_path):
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.log = PacketLogger(log_path)
        self.queue = TaskQueue(num_tasks, range_size, seed)
        self.registry = WorkerRegistry()
        self.results = {}                      # task_id includes worker_id, attempt, found, value
        self.results_file = open(results_path, 'w', buffering=1)
        self.results_file.write('task_id,worker_id,attempt,found,value,correct\n')
        self.duplicates_dropped = 0
        self.malformed = 0
        self.wrong_results = 0
        self.first_dispatch_time = None
        self.completion_time = None

    def send(self, msg_type, worker, task_id=0, attempt=0, payload=b'', flags=0):
        raw = pack_packet(msg_type, worker.worker_id, task_id, attempt, payload, flags)
        self.sock.sendto(raw, worker.addr)
        self.log.log('SEND', Packet(msg_type, flags, worker.worker_id, task_id, attempt, payload),
                     worker.addr)

    def dispatch(self, worker):
        """Give the worker the next waiting task. Returns False if no task is left."""
        item = self.queue.next_task()
        if item is None:
            return False
        task, attempt = item
        self.send(TASK_DISPATCH, worker, task.task_id, attempt,
                  pack_task(task.start, task.end, task.digest))
        worker.current_task = task.task_id
        worker.current_attempt = attempt
        if self.first_dispatch_time is None:
            self.first_dispatch_time = time.time()
        return True

    def resend_dispatch(self, worker):
        """Send the worker's current task again, unchanged (same Attempt_Num)."""
        task = self.queue.tasks[worker.current_task]
        self.send(TASK_DISPATCH, worker, task.task_id, worker.current_attempt,
                  pack_task(task.start, task.end, task.digest))

    def handle_join(self, addr):
        worker, is_new = self.registry.register(addr)
        flags = 0 if self.queue.has_pending or worker.current_task is not None \
            else FLAG_NO_MORE_TASKS
        self.send(JOIN_ACK, worker, flags=flags)
        if worker.current_task is None:
            self.dispatch(worker)
        elif not is_new:
            # The worker joined again, so it probably never saw its task: send it again.
            self.resend_dispatch(worker)

    def handle_heartbeat(self, pkt, addr):
        worker = self.registry.get(pkt.worker_id, addr)
        if worker is not None:
            self.registry.touch(worker)

    def handle_result(self, pkt, addr):
        worker = self.registry.get(pkt.worker_id, addr)
        if worker is None or not self.queue.is_known(pkt.task_id):
            return                                   # unknown sender or task so we ignore it
        self.registry.touch(worker)
        try:
            found, value = unpack_result(pkt.payload)
        except Exception:
            self.malformed += 1
            return

        first_time = self.queue.mark_done(pkt.task_id)
        if first_time:
            correct = found and value == self.queue.tasks[pkt.task_id].secret
            if not correct:
                self.wrong_results += 1
            self.results[pkt.task_id] = (pkt.worker_id, pkt.attempt, found, value)
            self.results_file.write('%d,%d,%d,%d,%d,%d\n' % (
                pkt.task_id, pkt.worker_id, pkt.attempt, found, value, correct))
            if worker.current_task == pkt.task_id:
                worker.current_task = None
            if self.queue.all_done:
                self.completion_time = time.time()
        else:
            self.duplicates_dropped += 1             # count the result only once

        # Always acknowledge, even a repeat, so the worker stops retransmitting.
        has_next = self.queue.has_pending
        self.send(ACK_RESULT, worker, pkt.task_id, pkt.attempt,
                  flags=0 if has_next else FLAG_NO_MORE_TASKS)
        if first_time and has_next and worker.current_task is None:
            self.dispatch(worker)

    def handle(self, data, addr):
        try:
            pkt = unpack_packet(data)
        except ProtocolError:
            self.malformed += 1                      # if the packet is malformed, we drop it like a lost packet
            return
        self.log.log('RECV', pkt, addr)
        if pkt.msg_type == WORKER_JOIN:
            self.handle_join(addr)
        elif pkt.msg_type == HEARTBEAT:
            self.handle_heartbeat(pkt, addr)
        elif pkt.msg_type == TASK_RESULT:
            self.handle_result(pkt, addr)

    def run(self, idle_timeout):
        print('Server ready on port %d, %d tasks' % (self.sock.getsockname()[1],
                                                     len(self.queue.tasks)), flush=True)
        self.sock.settimeout(0.2)
        last_activity = time.time()
        done_at = None
        ok = True
        while True:
            try:
                data, addr = self.sock.recvfrom(2048)
                last_activity = time.time()
                self.handle(data, addr)
            except socket.timeout:
                pass
            except ConnectionResetError:
                pass                                 
            if self.queue.all_done:
                if done_at is None:
                    done_at = time.time()
                elif time.time() - done_at > LINGER_SECONDS:
                    break
            elif time.time() - last_activity > idle_timeout:
                print('Idle for %.0f s with tasks unfinished, stopping.' % idle_timeout)
                ok = False
                break
        self.summary()
        self.close()
        return ok

    def summary(self):
        total = None
        if self.first_dispatch_time and self.completion_time:
            total = self.completion_time - self.first_dispatch_time
        print('--- server summary ---')
        print('tasks completed:           %d / %d' % (len(self.queue.done), len(self.queue.tasks)))
        print('wrong results:             %d' % self.wrong_results)
        print('duplicate results dropped: %d' % self.duplicates_dropped)
        print('malformed packets:         %d' % self.malformed)
        print('workers joined:            %d' % len(self.registry.workers))
        if total is not None:
            print('total completion time:     %.3f s' % total)

    def close(self):
        self.log.close()
        self.results_file.close()
        self.sock.close()


def main():
    ap = argparse.ArgumentParser(description='RJDAP server (Command Hub)')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=12000)
    ap.add_argument('--tasks', type=int, default=1000)
    ap.add_argument('--range', type=int, default=2000, help='numbers searched per task')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--log', default='logs/server.csv')
    ap.add_argument('--results', default='logs/results.csv')
    ap.add_argument('--idle-timeout', type=float, default=30.0)
    args = ap.parse_args()
    server = Server(args.host, args.port, args.tasks, args.range, args.seed,
                    args.log, args.results)
    raise SystemExit(0 if server.run(args.idle_timeout) else 1)


if __name__ == '__main__':
    main()