
from protocol.messages import digest_of


def compute_task(start, end, target_digest):
    
    for n in range(start, end):
        if digest_of(n) == target_digest:
            return True, n
    return False, 0