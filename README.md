# Network Congestion Mitigation: Experiential Learning Project

## 1. Project Overview
This project simulates a network router to analyze and mitigate **Network Congestion**. We compare different algorithms to see how they protect high-priority ("Gold") traffic when the network is overloaded.

* **The Problem:** In a standard First-In-First-Out (FIFO) router, "Gold" (VIP) packets get dropped just as often as "Bronze" (Junk) packets during congestion.
* **The Solution:** We implemented and simulated three advanced mitigation strategies to prioritize Gold traffic.

---

## 2. Traffic Classes
We classify network traffic into three priority levels:
1.  **🥇 Gold:** Mission-critical data (VoIP, Real-time control). **Goal: 0% Drop Rate.**
2.  **🥈 Silver:** Important but not critical (Streaming, Database sync).
3.  **🥉 Bronze:** Low priority (File downloads, Background updates).

---

## 3. The Four Methods Simulated

### A. Baseline (The Control Group)
* **Algorithm:** Tail Drop (FIFO).
* **Logic:** The router has a buffer of size 20. If packet #21 arrives, it is dropped instantly, regardless of whether it is Gold or Bronze.
* **Expected Result:** High drop rates for Gold packets (~30%). **Failure.**

### B. Choke Packet (The "Emergency Brake")
* **Algorithm:** Active Queue Management (AQM) with Source Throttling.
* **Logic:**
    * Monitor the buffer. If it gets **>40% full (Threshold 8/20)**, trigger "Congestion State".
    * In Congestion State, **drop all incoming Silver/Bronze packets** immediately.
    * Only **Gold** packets are allowed into the buffer.
* **Why it works:** It reserves the remaining 60% of the buffer exclusively for Gold bursts.

### C. Token Bucket (The "Strict Budget")
* **Algorithm:** Traffic Shaping / Policing.
* **Logic:**
    * Each class has a "Bucket" of tokens. Sending a packet costs 1 token.
    * **Gold Refill Rate:** Infinite (5.0 tokens/tick). Always allowed.
    * **Bronze Refill Rate:** Starvation (0.2 tokens/tick). Can only send 1 packet every 5 ticks.
* **Why it works:** It prevents Bronze traffic from ever flooding the buffer in the first place.

### D. Weighted Fair Queuing (The "Bouncer")
* **Algorithm:** Scheduling with Preemption.
* **Logic:**
    * Packets are not served FIFO. They are sorted by a calculated **Finish Time** (Size / Weight). Gold has high weight, so it gets a "fast pass" to the front of the line.
    * **Preemption (Crucial Feature):** If the buffer is full and a Gold packet arrives, the router **deletes a Bronze packet** currently in the queue to make space for the Gold packet.
* **Why it works:** It guarantees Gold service even if the buffer is physically full.

---

## 4. How to Run the Simulations

We have 5 Python scripts, each visualizing a different aspect of the project.

### 1. `simulation.py` (The Statistical Proof)
* **What it does:** Runs a massive simulation (50,000 packets) and prints a text table of results.
* **Use this for:** Generating the hard numbers for your report.
* **Key Output:** Look for the **"G LOSS"** column. Baseline will be ~30%, while Choke/WFQ will be 0%.

### 2. `realtime_simulation.py` (Live Dashboard)
* **What it does:** Opens a 3-panel live dashboard.
    * **Top:** Live Gold Loss % (Watch Red line rise, Green line stay flat).
    * **Middle:** Buffer Occupancy (Watch Orange line hover at threshold 8).
    * **Bottom:** Bronze Drops (Watch Green/Orange lines skyrocket as they sacrifice Bronze).
* **Use this for:** Live demo to the professor/class.

### 3. `bandwidth_battle.py` (Throughput Wars)
* **What it does:** Opens a 2x2 grid showing the bandwidth usage of Gold vs. Bronze live.
* **Key Feature:** Every 20 frames, a **"Gold Burst"** occurs.
    * Watch **WFQ (Bottom-Right)** immediately spike Gold and kill Bronze.
    * Watch **Baseline (Top-Left)** fail to accommodate the spike.

## 5. Results Summary

| Method | Gold Loss % | Verdict |
| :--- | :--- | :--- |
| **Baseline** | **~30%** | ❌ **Failed.** Treated VIPs like trash. |
| **Choke Packet** | **0.0%** | ✅ **Success.** Saved Gold by aggressively dropping Silver/Bronze early. |
| **Token Bucket** | **~2.5%** | ⚠️ **Good.** Mostly worked, but bursts occasionally filled the physical buffer. |
| **WFQ** | **0.0%** | 🏆 **Best.** Zero loss due to preemption logic (kicking out Bronze). |

---

## 6. Dependencies
You need Python installed with these libraries:
```bash
pip install matplotlib numpy
