import argparse
import csv
import glob
import os
from collections import Counter


def read_csv(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def check(logs_dir='logs', num_tasks=1000):
    """Returns (problems, stats). `problems` is empty when the run passed."""
    problems = []
    stats = {}

    results = read_csv(os.path.join(logs_dir, 'results.csv'))
    server_log = read_csv(os.path.join(logs_dir, 'server.csv'))
    worker_logs = sorted(glob.glob(os.path.join(logs_dir, 'worker_*.csv')))

    # 1. every task completed, once, with a correct result
    result_ids = [int(r['task_id']) for r in results]
    missing = sorted(set(range(1, num_tasks + 1)) - set(result_ids))
    repeated = sorted(t for t, n in Counter(result_ids).items() if n > 1)
    wrong = [r['task_id'] for r in results if r['correct'] != '1']
    stats['tasks_completed'] = len(set(result_ids))
    if missing:
        problems.append('%d tasks have no result (first: %s)' % (len(missing), missing[:5]))
    if repeated:
        problems.append('results counted twice for tasks %s' % repeated[:5])
    if wrong:
        problems.append('%d wrong results (first: %s)' % (len(wrong), wrong[:5]))

    # 2. zero duplicate executions
    if not worker_logs:
        problems.append('no worker logs found in %s' % logs_dir)
    executions = Counter()
    for path in worker_logs:
        for row in read_csv(path):
            if row['direction'] == 'RECV' and row['msg_type'] == 'TASK_DISPATCH':
                executions[int(row['task_id'])] += 1
    duplicate_exec = sorted(t for t, n in executions.items() if n > 1)
    never_run = sorted(set(range(1, num_tasks + 1)) - set(executions))
    stats['workers'] = len(worker_logs)
    stats['executions'] = sum(executions.values())
    stats['duplicate_executions'] = len(duplicate_exec)
    if duplicate_exec:
        problems.append('%d tasks executed more than once (first: %s)'
                        % (len(duplicate_exec), duplicate_exec[:5]))
    if never_run:
        problems.append('%d tasks never executed (first: %s)' % (len(never_run), never_run[:5]))

    # 3. every result was acknowledged; report repeated results the server dropped
    result_recv = Counter()
    ack_sent = Counter()
    for row in server_log:
        if row['msg_type'] == 'TASK_RESULT' and row['direction'] == 'RECV':
            result_recv[int(row['task_id'])] += 1
        elif row['msg_type'] == 'ACK_RESULT' and row['direction'] == 'SEND':
            ack_sent[int(row['task_id'])] += 1
    unacked = sorted(set(result_ids) - set(ack_sent))
    stats['duplicate_results_received'] = sum(n - 1 for n in result_recv.values() if n > 1)
    if unacked:
        problems.append('%d results were never acknowledged (first: %s)'
                        % (len(unacked), unacked[:5]))
    return problems, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--logs', default='logs')
    ap.add_argument('--tasks', type=int, default=1000)
    args = ap.parse_args()
    problems, stats = check(args.logs, args.tasks)
    print('--- result check ---')
    for key, value in stats.items():
        print('%-28s %s' % (key, value))
    if problems:
        print('FAIL')
        for p in problems:
            print('  - ' + p)
        raise SystemExit(1)
    print('PASS: all %d tasks completed correctly, zero duplicate executions' % args.tasks)


if __name__ == '__main__':
    main()
