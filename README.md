RJDAP-FD v1 - Reliable Job Dispatch & Aggregation Protocol over UDP
Computer Networks Major Task, Fall 2026 - Project 2 (RJDAP), Phase 1 prototype
Team: Hana Tamer Ismaeil      24P0336
      Raghad Mohamed ElSherif 24P0044
      Salma Mohamed ElSherif  24P0012
      Mohamed Kareem Kamal    24P0047


DEMO VIDEO:



1. WHAT THIS IS
---------------
A Command Hub (server) sends small hash-search tasks to Worker clients over UDP.
Each Worker computes the task and returns the result. The protocol detects lost
and repeated packets so that every result is counted exactly once.

Phase 1 demonstrates the INIT exchange (WORKER_JOIN, JOIN_ACK) and the DATA
exchange (TASK_DISPATCH, TASK_RESULT, ACK_RESULT), with every packet logged.


2. REQUIREMENTS
---------------
- Python 3.8 or newer (developed with Python 3.13).
- Standard library only. No pip install is needed.


3. FOLDER LAYOUT
----------------
  protocol/   header.py (18-byte header, pack/unpack), messages.py (types, payloads),
              checksum.py (CRC32), logger.py (packet log to CSV)
  server/     server.py (Command Hub), task_queue.py, worker_registry.py
  worker/     client.py (Worker), compute.py (hash search)
  tests/      baseline.py (automated baseline scenario),
              test_results.py (checks the logs), test_protocol.py (header self-test)
  logs/       CSV logs written by each run
  captures/   packet captures (.pcap)
  docs/       proposal.pdf, mini_rfc.pdf


4. QUICK START: AUTOMATED BASELINE
----------------------------------
Open a terminal in the project root folder (the folder that contains this file)
and run:

    python -m tests.baseline

(On Linux/macOS use python3 if python is not Python 3.)

This starts the server and 4 workers on localhost, runs 1,000 tasks, then checks
the logs. The last line should be:

    PASS: all 1000 tasks completed correctly, zero duplicate executions

Exit code is 0 on PASS and 1 on FAIL. Options:

    --workers 4      number of workers
    --tasks 1000     number of tasks
    --port 12000     UDP port of the server

Always run commands from the project root, otherwise the imports fail.


5. RUNNING THE PARTS BY HAND
----------------------------
Use one terminal for the server and one terminal per worker.

    python -m server.server --port 12000 --tasks 1000
    python -m worker.client --server localhost --port 12000 --log logs/worker_1.csv
    python -m worker.client --server localhost --port 12000 --log logs/worker_2.csv
    (and so on for workers 3 and 4)

After the server prints its summary, check the logs:

    python -m tests.test_results

Check the header code on its own:

    python -m tests.test_protocol

Server options: --host, --port, --tasks, --range (numbers searched per task,
default 2000), --seed (default 1), --log, --results, --idle-timeout.
Worker options: --server, --port, --log, --timeout (ACK wait in seconds,
default 0.2), --max-retries, --heartbeat (seconds, 0 = off), --idle-timeout.


6. LOG FILES (in logs/)
-----------------------
  server.csv, worker_N.csv   one line per packet sent or received:
      timestamp,direction,msg_type,task_id,worker_id,attempt,payload_len,peer
      (timestamp in Unix seconds, direction is SEND or RECV)
  results.csv                one line per accepted result:
      task_id,worker_id,attempt,found,value,correct

The logs are overwritten at every run.


7. PACKET CAPTURE
-----------------
Start the capture first, then run the baseline, then stop the capture.

  Linux / WSL2:
      sudo tcpdump -i lo -w captures/baseline.pcap udp port 12000
  Windows (Wireshark, Npcap installed):
      capture on "Adapter for loopback traffic capture", filter: udp.port == 12000
      then save as captures/baseline.pcap

The protocol header is not decoded by Wireshark by default: the UDP payload
starts with the bytes 52 4a (Magic "RJ"). The header layout is in docs/mini_rfc.pdf.


8. PHASE 1 LIMITS
-----------------
Not yet implemented (Phase 2): timeout-based task reassignment, Worker-crash
detection from missed heartbeats, adaptive timeout, payload fragmentation and
the netem experiments. In Phase 1 a Worker retransmits its result with a fixed
200 ms timeout, and the server removes duplicate results using the Task_ID.
