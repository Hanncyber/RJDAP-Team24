from protocol.header import (HEADER_SIZE, ProtocolError, pack_packet, unpack_packet)
from protocol.messages import (TASK_DISPATCH, TASK_RESULT, digest_of, pack_result,
                               pack_task, unpack_result, unpack_task)
from worker.compute import compute_task


def main():
    target = digest_of(4242)
    raw = pack_packet(TASK_DISPATCH, worker_id=2, task_id=17, attempt=1,
                      payload=pack_task(4000, 5000, target))
    assert len(raw) == HEADER_SIZE + 48

    pkt = unpack_packet(raw)
    assert (pkt.msg_type, pkt.worker_id, pkt.task_id, pkt.attempt) == (TASK_DISPATCH, 2, 17, 1)

    start, end, digest = unpack_task(pkt.payload)
    assert compute_task(start, end, digest) == (True, 4242)
    assert compute_task(0, 100, digest) == (False, 0)

    res = unpack_packet(pack_packet(TASK_RESULT, 2, 17, 1, pack_result(True, 4242)))
    assert unpack_result(res.payload) == (True, 4242)

    corrupted = bytearray(raw)
    corrupted[-1] ^= 0xFF
    try:
        unpack_packet(bytes(corrupted))
    except ProtocolError:
        pass
    else:
        raise SystemExit('FAIL: corruption not detected')

    print('header size: %d bytes - all protocol tests passed' % HEADER_SIZE)


if __name__ == '__main__':
    main()
