import random
import heapq
import copy
from collections import deque
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ==========================================
# 1. CONFIGURATION
# ==========================================
BUFFER_SIZE = 20
ROUTER_SPEED = 0.7  # 70% service rate
CHOKE_THRESHOLD = 8
WEIGHTS = {'Gold': 4.0, 'Silver': 2.0, 'Bronze': 1.0}
PACKETS_PER_FRAME = 50  # Speed of animation

# ==========================================
# 2. PACKET CLASS
# ==========================================
class Packet:
    def __init__(self, id, type, arrival_time):
        self.id = id
        self.type = type
        self.arrival_time = arrival_time
        self.size = random.randint(1, 3) 
        self.finish_time = 0      
    def __lt__(self, other):
        return self.id < other.id

# ==========================================
# 3. STATEFUL SIMULATION CLASSES
# ==========================================
# We need classes now so they can "remember" their state between animation frames

class SimulationEngine:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.buffer = deque()
        # Stats
        self.served = {'Gold': 0, 'Silver': 0, 'Bronze': 0}
        self.dropped = {'Gold': 0, 'Silver': 0, 'Bronze': 0}
        # History for plotting
        self.hist_gold_loss = []
        self.hist_buffer = []
        self.hist_bronze_drop = []
    
    def process_step(self, packet):
        raise NotImplementedError("Subclasses must implement logic")

    def service(self):
        # Common service logic: Router processes 1 packet (if random allows)
        if self.buffer and random.random() < ROUTER_SPEED:
            p = self.buffer.popleft()
            self.served[p.type] += 1
            return True
        return False

    def record_stats(self):
        # Calculate Gold Loss %
        g_total = self.served['Gold'] + self.dropped['Gold']
        g_loss = (self.dropped['Gold'] / g_total * 100) if g_total > 0 else 0
        
        self.hist_gold_loss.append(g_loss)
        self.hist_buffer.append(len(self.buffer))
        self.hist_bronze_drop.append(self.dropped['Bronze'])

# --- 1. BASELINE ---
class BaselineSim(SimulationEngine):
    def process_step(self, p):
        self.service()
        if len(self.buffer) < BUFFER_SIZE:
            self.buffer.append(p)
        else:
            self.dropped[p.type] += 1
        self.record_stats()

# --- 2. CHOKE PACKET ---
class ChokeSim(SimulationEngine):
    def process_step(self, p):
        self.service()
        
        # Trigger Logic
        is_congested = len(self.buffer) > CHOKE_THRESHOLD
        
        if is_congested:
            if p.type == 'Gold':
                if len(self.buffer) < BUFFER_SIZE:
                    self.buffer.append(p)
                else:
                    self.dropped['Gold'] += 1
            else:
                self.dropped[p.type] += 1 # Drop Silver/Bronze
        else:
            if len(self.buffer) < BUFFER_SIZE:
                self.buffer.append(p)
            else:
                self.dropped[p.type] += 1
        self.record_stats()

# --- 3. TOKEN BUCKET ---
class TokenSim(SimulationEngine):
    def __init__(self, name, color):
        super().__init__(name, color)
        # Aggressive Token Rates
        self.buckets = {'Gold': [10, 10, 5.0], 'Silver': [5, 5, 0.5], 'Bronze': [2, 2, 0.2]}

    def process_step(self, p):
        self.service()
        
        # Refill
        for t in self.buckets:
            cur, cap, rate = self.buckets[t]
            self.buckets[t][0] = min(cap, cur + rate)
            
        needed = 1
        if self.buckets[p.type][0] >= needed:
            if len(self.buffer) < BUFFER_SIZE:
                self.buckets[p.type][0] -= needed
                self.buffer.append(p)
            else:
                self.dropped[p.type] += 1
        else:
            self.dropped[p.type] += 1
        self.record_stats()

# --- 4. WFQ (With Preemption) ---
class WFQSim(SimulationEngine):
    def __init__(self, name, color):
        super().__init__(name, color)
        self.buffer = [] # Heap list
        self.last_finish = {'Gold': 0, 'Silver': 0, 'Bronze': 0}

    def service(self):
        if self.buffer and random.random() < ROUTER_SPEED:
            _, p = heapq.heappop(self.buffer)
            self.served[p.type] += 1
            return True
        return False

    def process_step(self, p):
        self.service()
        
        # Calc Finish Time
        prev_f = self.last_finish[p.type]
        v_finish = max(p.arrival_time, prev_f) + (p.size / WEIGHTS[p.type])
        p.finish_time = v_finish
        self.last_finish[p.type] = v_finish
        
        if len(self.buffer) < BUFFER_SIZE:
            heapq.heappush(self.buffer, (p.finish_time, p))
        else:
            # Preemption Logic (Kick Bronze for Gold)
            if p.type == 'Gold':
                victim_idx = -1
                for i, item in enumerate(self.buffer):
                    if item[1].type == 'Bronze':
                        victim_idx = i
                        break
                
                if victim_idx != -1:
                    # Kill Bronze
                    self.buffer.pop(victim_idx)
                    heapq.heapify(self.buffer)
                    self.dropped['Bronze'] += 1
                    # Insert Gold
                    heapq.heappush(self.buffer, (p.finish_time, p))
                else:
                    self.dropped['Gold'] += 1
            else:
                self.dropped[p.type] += 1
        self.record_stats()


# ==========================================
# 4. REAL-TIME PLOTTING LOGIC
# ==========================================

# Initialize Sims
sims = [
    BaselineSim("Baseline", "red"),
    ChokeSim("Choke", "orange"),
    TokenSim("Token", "blue"),
    WFQSim("WFQ", "green")
]

# Setup Plots
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
plt.subplots_adjust(hspace=0.3)

# Lines setup
lines = {'gold': [], 'buffer': [], 'bronze': []}

for sim in sims:
    l1, = ax1.plot([], [], label=sim.name, color=sim.color, linewidth=2)
    l2, = ax2.plot([], [], label=sim.name, color=sim.color, linewidth=1.5, alpha=0.7)
    l3, = ax3.plot([], [], label=sim.name, color=sim.color, linewidth=2)
    lines['gold'].append(l1)
    lines['buffer'].append(l2)
    lines['bronze'].append(l3)

# Graph Formatting
ax1.set_title("Live Metric 1: Gold Packet Loss % (Goal: 0%)", fontweight='bold')
ax1.set_ylabel("Loss %")
ax1.set_ylim(0, 40)
ax1.legend(loc="upper right")
ax1.grid(True, linestyle='--', alpha=0.5)

ax2.set_title("Live Metric 2: Buffer Occupancy (Queue Depth)", fontweight='bold')
ax2.set_ylabel("Packets in Router")
ax2.set_ylim(0, 22)
ax2.axhline(y=BUFFER_SIZE, color='black', linestyle=':', label='Max Capacity')
ax2.grid(True, linestyle='--', alpha=0.5)

ax3.set_title("Live Metric 3: Bronze Sacrifices (Total Drops)", fontweight='bold')
ax3.set_ylabel("Dropped Count")
ax3.set_xlabel("Time (Simulation Steps)")
ax3.grid(True, linestyle='--', alpha=0.5)

# Traffic Generator for the Animation Loop
global_packet_id = 0
def get_packet_chunk():
    global global_packet_id
    chunk = []
    types = ['Gold', 'Silver', 'Bronze']
    # 20% Gold, 30% Silver, 50% Bronze
    for _ in range(PACKETS_PER_FRAME):
        p_type = random.choices(types, weights=[20, 30, 50], k=1)[0]
        chunk.append(Packet(global_packet_id, p_type, global_packet_id))
        global_packet_id += 1
    return chunk

# Animation Function
def update(frame):
    # 1. Generate new traffic chunk
    new_packets = get_packet_chunk()
    
    # 2. Feed SAME traffic to ALL simulations
    for i, sim in enumerate(sims):
        # We must copy packets because WFQ modifies them (finish_time)
        # and lists are mutable
        sim_packets = copy.deepcopy(new_packets)
        
        for p in sim_packets:
            sim.process_step(p)
            
        # 3. Update Line Data
        x_data = range(len(sim.hist_gold_loss))
        
        lines['gold'][i].set_data(x_data, sim.hist_gold_loss)
        lines['buffer'][i].set_data(x_data, sim.hist_buffer)
        lines['bronze'][i].set_data(x_data, sim.hist_bronze_drop)

    # 4. Adjust X-Axis dynamically
    current_len = len(sims[0].hist_gold_loss)
    ax1.set_xlim(0, current_len)
    ax3.set_ylim(0, max(sims[0].dropped['Bronze'], sims[1].dropped['Bronze'], 100) * 1.1)
    
    return lines['gold'] + lines['buffer'] + lines['bronze']

print("Starting Real-Time Simulation Dashboard...")
ani = animation.FuncAnimation(fig, update, interval=50, blit=False)
plt.show()