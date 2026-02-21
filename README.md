# Network Congestion Mitigation: Experiential Learning Project

## 1. Project Overview

This project simulates a network router to analyze and mitigate **network congestion** under high load conditions. The goal is to evaluate how different queue management and scheduling algorithms protect high-priority (“Gold”) traffic during overload scenarios.

### Problem Statement
In a standard First-In-First-Out (FIFO) router using Tail Drop, high-priority (“Gold”) packets are dropped at the same rate as low-priority (“Bronze”) packets when congestion occurs. This leads to unacceptable loss for mission-critical traffic.

### Objective
Implement and compare advanced congestion mitigation strategies to prioritize high-value traffic and reduce or eliminate Gold packet loss.

---

## 2. Traffic Classes

Traffic is categorized into three priority levels:

1. **Gold** – Mission-critical data (e.g., VoIP, real-time control systems)  
   **Target:** 0% packet loss  

2. **Silver** – Important but non-critical traffic (e.g., streaming, database synchronization)

3. **Bronze** – Low-priority traffic (e.g., file downloads, background updates)

---

## 3. Simulated Methods

### A. Baseline (Control Group)

**Algorithm:** Tail Drop (FIFO)  
**Buffer Size:** 20 packets  

**Logic:**  
Packets are processed in arrival order. If the buffer is full (packet #21 arrives), the packet is immediately dropped, regardless of priority.

**Expected Outcome:**  
High Gold packet loss (~30%).  
This method does not differentiate traffic classes and fails to protect high-priority data.

---

### B. Choke Packet (Active Queue Management)

**Algorithm:** Active Queue Management (AQM) with Source Throttling  

**Logic:**
- Monitor buffer occupancy.
- If buffer exceeds **40% capacity (8/20 packets)**, enter *Congestion State*.
- In Congestion State:
  - Drop all incoming Silver and Bronze packets.
  - Allow only Gold packets into the buffer.

**Why It Works:**  
This strategy reserves the remaining 60% of buffer capacity exclusively for Gold traffic during congestion bursts, preventing high-priority loss.

---

### C. Token Bucket (Traffic Shaping / Policing)

**Algorithm:** Token Bucket Rate Limiting  

**Logic:**
- Each traffic class has a token bucket.
- Sending a packet consumes one token.
- **Gold Refill Rate:** 5.0 tokens/tick (effectively unrestricted)
- **Bronze Refill Rate:** 0.2 tokens/tick (approximately 1 packet every 5 ticks)

**Why It Works:**  
This method prevents Bronze traffic from flooding the buffer by limiting its transmission rate before congestion occurs.

**Limitation:**  
Gold packets may still experience minimal loss (~2.5%) if physical buffer constraints are exceeded during bursts.

---

### D. Weighted Fair Queuing (WFQ)

**Algorithm:** Weighted Fair Queuing with Preemption  

**Logic:**
Packets are scheduled based on calculated finish time:

\[
Finish\ Time = \frac{Packet\ Size}{Weight}
\]

- Higher-weight traffic (Gold) receives preferential service.
- **Preemption Feature:**  
  If the buffer is full and a Gold packet arrives, a Bronze packet in the queue is removed to make space.

**Why It Works:**  
WFQ guarantees Gold service even when the buffer is full, ensuring zero Gold packet loss.

---

## 4. Running the Simulations

The project includes multiple Python scripts to analyze and visualize performance.

### 1. `simulation.py` — Statistical Analysis

**Purpose:**  
Runs a large-scale simulation (50,000 packets) and outputs statistical results.

**Use Case:**  
Generate quantitative results for reports or documentation.

**Key Metric:**  
Monitor the **Gold Loss (%)** column.

Expected outcomes:
- Baseline: ~30%
- Choke Packet: 0%
- Token Bucket: ~2.5%
- WFQ: 0%

---

### 2. `realtime_simulation.py` — Live Dashboard

**Purpose:**  
Displays a real-time, multi-panel dashboard including:
- Gold packet loss over time
- Buffer occupancy
- Bronze packet drops

**Use Case:**  
Live demonstration or presentation.

---

### 3. `bandwidth_battle.py` — Throughput Comparison

**Purpose:**  
Displays a 2×2 comparison grid of bandwidth usage between Gold and Bronze traffic under each algorithm.

**Key Feature:**  
Every 20 frames, a simulated Gold traffic burst occurs.

**Observation Goals:**
- WFQ should immediately prioritize Gold and suppress Bronze.
- Baseline should struggle during burst conditions.

---

## 5. Results Summary

| Method              | Gold Loss (%) | Evaluation |
|---------------------|--------------|------------|
| Baseline (FIFO)     | ~30%         | Failed to protect high-priority traffic |
| Choke Packet (AQM)  | 0.0%         | Successfully preserved Gold traffic |
| Token Bucket        | ~2.5%        | Strong performance with minor burst loss |
| WFQ (Preemptive)    | 0.0%         | Best overall performance |

---

## 6. Installation & Dependencies

### Requirements

- Python 3.x  
- Required libraries:

```bash
pip install matplotlib numpy
