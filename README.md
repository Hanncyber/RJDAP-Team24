# RMSH 
## Reliable Job Dispatch & Aggregation Protocol over UDP

**Computer Networks Major Task — Fall 2026**  
**Project 2 (RJDAP) | Phase 1: Prototype**

### Team Members

| Name | Student ID |
|---|---|
| Hana Tamer Ismaeil | 24P0336 |
| Raghad Mohamed ElSherif | 24P0044 |
| Salma Mohamed ElSherif | 24P0012 |
| Mohamed Kareem Kamal | 24P0047 |

### Demo Video
**Video link:** [Paste the video link here]

---

## 1. Project Overview

RMSH is a custom application-layer protocol built on UDP for reliable job dispatch and result aggregation.

A central **Command Hub (server)** distributes small hash-search tasks to **Worker clients**. Each Worker processes its assigned task and returns the result to the Hub. The protocol uses acknowledgements, retransmissions, and duplicate-result suppression to improve reliability and ensure each result is accepted and counted only once.

The Phase 1 prototype demonstrates:

- **Initialization (INIT):** `WORKER_JOIN` and `JOIN_ACK`
- **Data exchange (DATA):** `TASK_DISPATCH`, `TASK_RESULT`, and `ACK_RESULT`
- **Logging:** Packet events and accepted task results are recorded in CSV files.

## 2. Requirements

- **Python:** 3.8 or newer (developed with Python 3.13).
- **Dependencies:** Python standard library only; no additional packages are required.

## 3. Project Structure

```text
protocol/   Header encoding, message types, payloads, CRC32 checksums, and CSV logging
server/     Command Hub, task queue, and Worker registry
worker/     Worker client and hash-search computation
tests/      Automated baseline and protocol/result tests
logs/       CSV packet-event and task-result logs
captures/   Packet captures (.pcap), when generated
docs/       Project proposal and Mini-RFC
```

## 4. Quick Start: Automated Baseline Test

Run the baseline test from the **project root directory** (the directory containing this README).

```bash
python tests/baseline.py
```

On Linux or macOS, use `python3` if `python` does not point to Python 3.

The automated baseline starts the server and four Workers on localhost, processes 1,000 tasks, and checks the results.

**Expected success message:**

```text
PASS: all 1000 tasks completed correctly, zero duplicate executions
```

The script should exit with code `0` on success and `1` on failure.

### Configurable options

The baseline supports the following options, if implemented by the script:

| Option | Description | Default |
|---|---|---:|
| `--workers` | Number of Workers | `4` |
| `--tasks` | Number of tasks | `1000` |
| `--port` | UDP port used by the server | `12000` |

Run commands from the project root to ensure Python imports resolve correctly.

## 5. Running the Server and Workers Manually

For manual execution, start the server in one terminal and each Worker in a separate terminal. Run every command from the project root.

**Terminal 1 — Command Hub**

```bash
python -m server.server --port 12000 --tasks 1000
```

**Terminal 2 — Worker 1**

```bash
python -m worker.client --server localhost --port 12000 --log logs/worker_1.csv
```

**Terminal 3 — Worker 2**

```bash
python -m worker.client --server localhost --port 12000 --log logs/worker_2.csv
```

Repeat the Worker command for Workers 3 and 4, using a different log filename for each Worker.

After the run, execute the result and protocol tests:

```bash
python -m tests.test_results
python -m tests.test_protocol
```

### Command-line options

The server supports options including `--host`, `--port`, `--tasks`, `--range`, `--seed`, `--log`, `--results`, and `--idle-timeout`.

The Worker supports options including `--server`, `--port`, `--log`, `--timeout`, `--max-retries`, `--heartbeat`, and `--idle-timeout`.

Refer to the corresponding script's argument definitions for exact defaults and supported options.

## 6. Logs and Results

The `logs/` directory contains CSV files generated during execution. The logs are overwritten on each run.

### Packet-event logs

Files such as `server.csv` and `worker_N.csv` record packet events using this schema:

```text
timestamp,direction,msg_type,task_id,worker_id,attempt,payload_len,peer
```

| Field | Meaning |
|---|---|
| `timestamp` | Unix timestamp of the event |
| `direction` | `SEND` or `RECV` |
| `msg_type` | Protocol message type |
| `task_id` | Associated task identifier |
| `worker_id` | Associated Worker identifier |
| `attempt` | Task attempt number |
| `payload_len` | Payload length in bytes |
| `peer` | Remote IP address and port |

### Task-result log

`results.csv` records accepted task results:

```text
task_id,worker_id,attempt,found,value,correct
```

These records allow the baseline test to verify task completion and result correctness.

## 7. Packet Capture (Wireshark / tcpdump)

Packet captures can be used to inspect UDP exchanges independently of the application's CSV logs. This section is included to prepare for the network experiments required in later project phases.

### Linux / WSL2

Start the capture before running the baseline:

```bash
sudo tcpdump -i lo -w captures/baseline.pcap udp port 12000
```

Stop the capture after the test finishes.

### Windows

1. Open Wireshark with Npcap installed.
2. Select the loopback capture adapter.
3. Apply the capture filter `udp port 12000`.
4. Start capturing, run the baseline, then stop the capture.
5. Save the capture as `captures/baseline.pcap`.

Wireshark does not automatically decode the custom RJDAP-FD header. The UDP payload begins with the magic bytes `52 4a` (ASCII `RJ`). Refer to the Mini-RFC in `docs/` for the header layout.

## 8. Phase 1 Scope and Limitations

The Phase 1 prototype focuses on initialization, task dispatch, result delivery, acknowledgements, duplicate-result suppression, and logging.

The following features are deferred to Phase 2:

- Timeout-based task reassignment
- Worker-crash detection based on missed heartbeats
- Adaptive timeout mechanisms
- Payload fragmentation
- Network impairment experiments using `netem`

In Phase 1, a Worker retransmits its result after a fixed 200 ms acknowledgement timeout, and the server suppresses duplicate results using the task identifier.

---

**End of README — RMSH, Phase 1 Prototype**
