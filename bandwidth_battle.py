import random
import heapq
from collections import deque
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import copy

# ==========================================
# 1. CONFIGURATION
# ==========================================
BUFFER_SIZE = 20
ROUTER_SPEED = 0.7 
CHOKE_THRESHOLD = 8
WEIGHTS = {'Gold': 4.0, 'Silver': 2.0, 'Bronze': 1.0}
PACKETS_PER_FRAME = 30  # Slightly slower to see the "waves"

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
# 3. SIMULATION ENGINES (Throughput Focus)
# ==========================================
class SimulationEngine:
    def __init__(self, name):
        self.name = name
        self.buffer = deque()
        # Instantaneous Throughput (Reset every frame)
        self.frame_served = {'Gold': 0, 'Silver': 0, 'Bronze': 0}
        # History for plotting
        self.hist_gold = []
        self.hist_silver = []
        self.hist_bronze = []
    
    def reset_frame_stats(self):
        self.frame_served = {'Gold': 0, 'Silver': 0, 'Bronze': 0}

    def record_history(self):
        self.hist_gold.append(self.frame_served['Gold'])
        self.hist_silver.append(self.frame_served['Silver'])
        self.hist_bronze.append(self.frame_served['Bronze'])

    def service(self):
        if self.buffer and random.random() < ROUTER_SPEED:
            p = self.buffer.popleft()
            self.frame_served[p.type] += 1
            return True
        return False

    def process_step(self, p):
        raise NotImplementedError

# --- 1. BASELINE ---
class BaselineSim(SimulationEngine):
    def process_step(self, p):
        self.service()
        if len(self.buffer) < BUFFER_SIZE:
            self.buffer.append(p)
    
# --- 2. CHOKE ---
class ChokeSim(SimulationEngine):
    def process_step(self, p):
        self.service()
        is_congested = len(self.buffer) > CHOKE_THRESHOLD
        
        if is_congested:
            if p.type == 'Gold':
                if len(self.buffer) < BUFFER_SIZE: self.buffer.append(p)
            else: pass # Drop
        else:
            if len(self.buffer) < BUFFER_SIZE: self.buffer.append(p)

# --- 3. TOKEN ---
class TokenSim(SimulationEngine):
    def __init__(self, name):
        super().__init__(name)
        self.buckets = {'Gold': [10, 10, 5.0], 'Silver': [5, 5, 0.5], 'Bronze': [2, 2, 0.2]}

    def process_step(self, p):
        self.service()
        for t in self.buckets:
            cur, cap, rate = self.buckets[t]
            self.buckets[t][0] = min(cap, cur + rate)
            
        needed = 1
        if self.buckets[p.type][0] >= needed:
            if len(self.buffer) < BUFFER_SIZE:
                self.buckets[p.type][0] -= needed
                self.buffer.append(p)

# --- 4. WFQ ---
class WFQSim(SimulationEngine):
    def __init__(self, name):
        super().__init__(name)
        self.buffer = [] # Heap
        self.last_finish = {'Gold': 0, 'Silver': 0, 'Bronze': 0}

    def service(self):
        if self.buffer and random.random() < ROUTER_SPEED:
            _, p = heapq.heappop(self.buffer)
            self.frame_served[p.type] += 1
            return True
        return False

    def process_step(self, p):
        self.service()
        prev_f = self.last_finish[p.type]
        v_finish = max(p.arrival_time, prev_f) + (p.size / WEIGHTS[p.type])
        p.finish_time = v_finish
        self.last_finish[p.type] = v_finish
        
        if len(self.buffer) < BUFFER_SIZE:
            heapq.heappush(self.buffer, (p.finish_time, p))
        else:
            if p.type == 'Gold':
                # Preemption Logic
                victim_idx = -1
                for i, item in enumerate(self.buffer):
                    if item[1].type == 'Bronze':
                        victim_idx = i
                        break
                if victim_idx != -1:
                    self.buffer.pop(victim_idx)
                    heapq.heapify(self.buffer)
                    heapq.heappush(self.buffer, (p.finish_time, p))

# ==========================================
# 4. REAL-TIME PLOTTING LOGIC
# ==========================================
sims = [
    BaselineSim("Baseline (Shared Misery)"),
    ChokeSim("Choke (Gold Protected)"),
    TokenSim("Token Bucket (Shaping)"),
    WFQSim("WFQ (Prioritization)")
]

# Setup 2x2 Grid
fig, axs = plt.subplots(2, 2, figsize=(14, 10))
axs = axs.flatten() # Make it easy to loop 0-3

# Line storage
lines = [] 
# Colors: Gold, Silver(Grey), Bronze(Orange)
colors = {'Gold': '#FFD700', 'Silver': '#A9A9A9', 'Bronze': '#D2691E'}

for i, ax in enumerate(axs):
    ax.set_title(sims[i].name, fontweight='bold')
    ax.set_ylim(0, 15) # Throughput scale
    ax.set_ylabel("Packets Served / Frame")
    ax.grid(True, linestyle=':', alpha=0.6)
    
    # Create 3 lines per graph
    l_g, = ax.plot([], [], label='Gold', color=colors['Gold'], linewidth=2.5)
    l_s, = ax.plot([], [], label='Silver', color=colors['Silver'], linewidth=1.5, linestyle='--')
    l_b, = ax.plot([], [], label='Bronze', color=colors['Bronze'], linewidth=1.5, linestyle=':')
    
    lines.append([l_g, l_s, l_b])
    
    if i == 0: ax.legend(loc='upper left') # Legend only on first graph

global_packet_id = 0

def update(frame):
    global global_packet_id
    
    # 1. Generate Traffic (Bursty)
    chunk = []
    # Every 10th frame, simulate a MASSIVE Gold burst to test robustness
    if frame % 20 == 0:
        weights = [90, 5, 5] # 90% Gold burst
    else:
        weights = [20, 30, 50] # Normal noise
        
    for _ in range(PACKETS_PER_FRAME):
        p_type = random.choices(['Gold', 'Silver', 'Bronze'], weights=weights, k=1)[0]
        chunk.append(Packet(global_packet_id, p_type, global_packet_id))
        global_packet_id += 1
    
    # 2. Process Traffic
    for i, sim in enumerate(sims):
        sim.reset_frame_stats()
        sim_packets = copy.deepcopy(chunk)
        for p in sim_packets:
            sim.process_step(p)
        sim.record_history()
        
        # 3. Update Lines
        x_data = range(len(sim.hist_gold))
        # Keep window sliding (show last 50 frames)
        if len(x_data) > 50:
            x_view = x_data[-50:]
            y_g = sim.hist_gold[-50:]
            y_s = sim.hist_silver[-50:]
            y_b = sim.hist_bronze[-50:]
        else:
            x_view = x_data
            y_g = sim.hist_gold
            y_s = sim.hist_silver
            y_b = sim.hist_bronze
            
        lines[i][0].set_data(x_view, y_g)
        lines[i][1].set_data(x_view, y_s)
        lines[i][2].set_data(x_view, y_b)
        
        axs[i].set_xlim(min(x_view), max(x_view) + 1)

    return sum(lines, [])

print("Starting Bandwidth Battle Dashboard...")
ani = animation.FuncAnimation(fig, update, interval=100, blit=False)
plt.show()