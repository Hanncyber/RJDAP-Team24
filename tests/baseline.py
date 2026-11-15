

#Starts the server and the workers, waits until all tasks are done, then runs the
#result check (tests/test_results.py). Exit code 0 = pass, 1 = fail.

import argparse
import glob
import os
import subprocess
import sys
import time

from test_results import check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--tasks', type=int, default=1000)
    ap.add_argument('--port', type=int, default=12000)
    ap.add_argument('--time-limit', type=float, default=120.0)
    args = ap.parse_args()

    os.makedirs(os.path.join(ROOT, 'logs'), exist_ok=True)
    for old in glob.glob(os.path.join(ROOT, 'logs', '*.csv')):
        os.remove(old)                         # start from clean logs

    procs = []
    passed = False
    try:
        server = subprocess.Popen(
            [sys.executable, '-m', 'server.server', '--port', str(args.port),
             '--tasks', str(args.tasks), '--log', 'logs/server.csv',
             '--results', 'logs/results.csv'], cwd=ROOT)
        procs.append(server)
        time.sleep(0.5)                        # let the server bind its port

        started = time.time()
        workers = []
        for i in range(1, args.workers + 1):
            workers.append(subprocess.Popen(
                [sys.executable, '-m', 'worker.client', '--server', 'localhost',
                 '--port', str(args.port), '--log', 'logs/worker_%d.csv' % i], cwd=ROOT))
        procs.extend(workers)

        server.wait(timeout=args.time_limit)
        for w in workers:
            w.wait(timeout=15)
        elapsed = time.time() - started
        print('\nBaseline run finished in %.2f s' % elapsed)

        problems, stats = check(os.path.join(ROOT, 'logs'), args.tasks)
        print('--- result check ---')
        for key, value in stats.items():
            print('%-28s %s' % (key, value))
        if problems:
            print('FAIL')
            for p in problems:
                print('  - ' + p)
        else:
            print('PASS: all %d tasks completed correctly, zero duplicate executions'
                  % args.tasks)
            passed = True
    except subprocess.TimeoutExpired:
        print('FAIL: the run did not finish within the time limit')
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()