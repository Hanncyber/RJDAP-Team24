"""Worker registry: who has joined, where they are, and what they are working on."""
import time


class WorkerInfo:
    def __init__(self, worker_id, addr):
        self.worker_id = worker_id
        self.addr = addr                 # (ip, port) the worker sends from
        self.last_seen = time.time()
        self.current_task = None         # task_id in progress, or None
        self.current_attempt = 0


class WorkerRegistry:
    def __init__(self):
        self.workers = {}      # worker_id -> WorkerInfo
        self._by_addr = {}     # addr -> worker_id
        self._next_id = 1

    def register(self, addr):
        """Register a worker. Returns (WorkerInfo, is_new).

        A repeated WORKER_JOIN from the same address (the JOIN_ACK was lost) gets the
        same Worker_ID back instead of a new one.
        """
        if addr in self._by_addr:
            worker = self.workers[self._by_addr[addr]]
            worker.last_seen = time.time()
            return worker, False
        worker = WorkerInfo(self._next_id, addr)
        self._next_id += 1
        self.workers[worker.worker_id] = worker
        self._by_addr[addr] = worker.worker_id
        return worker, True

    def get(self, worker_id, addr):
        #Return the worker only if the ID exists and the packet came from its address.
        worker = self.workers.get(worker_id)
        if worker is None or worker.addr != addr:
            return None
        return worker

    def touch(self, worker):
        worker.last_seen = time.time()