
import random
from collections import deque, namedtuple

from protocol.messages import digest_of

Task = namedtuple('Task', 'task_id start end digest secret')


class TaskQueue:
    def __init__(self, num_tasks=1000, range_size=2000, seed=1):
        
        rng = random.Random(seed)
        self.tasks = {}
        for tid in range(1, num_tasks + 1):
            start = (tid - 1) * range_size
            end = start + range_size
            secret = rng.randrange(start, end)
            self.tasks[tid] = Task(tid, start, end, digest_of(secret), secret)
        self.pending = deque(range(1, num_tasks + 1))   # waiting to be dispatched
        self.attempts = {tid: 0 for tid in self.tasks}  # how many times each was dispatched
        self.done = set()                               # task_ids with an accepted result

    def next_task(self):
        #Take the next waiting task. Returns (task, attempt_num) or None if nothing waits.
        if not self.pending:
            return None
        tid = self.pending.popleft()
        self.attempts[tid] += 1
        return self.tasks[tid], self.attempts[tid]

    def requeue(self, task_id):
        #Put a task back at the front (used later for timeouts and worker crashes).
        if task_id not in self.done:
            self.pending.appendleft(task_id)

    def is_known(self, task_id):
        return task_id in self.tasks

    def mark_done(self, task_id):
       #Record an accepted result. Returns True the first time, False for a duplicate.
        if task_id in self.done:
            return False
        self.done.add(task_id)
        return True

    @property
    def has_pending(self):
        return len(self.pending) > 0

    @property
    def all_done(self):
        return len(self.done) == len(self.tasks)