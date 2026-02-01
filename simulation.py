import random
import heapq
from collections import deque
import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. CONFIGURATION & SIMULATION LOGIC
# ==========================================
BUFFER_SIZE = 20          
TOTAL_PACKETS = 50000     
ROUTER_SPEED = 0.7        
CHOKE_THRESHOLD = 8      
WEIGHTS = {'Gold': 4.0, 'Silver': 2.0, 'Bronze': 1.0}

class Packet:
    def __init__(self, id, type, arrival_time):
        self.id = id
        self.type = type
        self.arrival_time = arrival_time
        self.size = random.randint(1, 3) 
        self.finish_time = 0      
    def __lt__(self, other):
        return self.id < other.id

def generate_traffic(n):
    packets = []
    types = ['Gold', 'Silver', 'Bronze']
    # Weights: 20% Gold, 30% Silver, 50% Bronze
    for i in range(n):
        p_type = random.choices(types, weights=[20, 30, 50], k=1)[0]
        packets.append(Packet(i, p_type, i))
    return packets

def init_stats():
    return {
        'Gold':   {'served': 0, 'dropped': 0},
        'Silver': {'served': 0, 'dropped': 0},
        'Bronze': {'served': 0, 'dropped': 0}
    }

# --- SIMULATION ENGINES (OPTIMIZED) ---
def run_baseline(packets):
    buffer = deque()
    stats = init_stats()
    for p in packets:
        if buffer and random.random() < ROUTER_SPEED:
            proc_p = buffer.popleft()
            stats[proc_p.type]['served'] += 1
        if len(buffer) < BUFFER_SIZE:
            buffer.append(p)
        else:
            stats[p.type]['dropped'] += 1
    while buffer:
        proc_p = buffer.popleft()
        stats[proc_p.type]['served'] += 1
    return stats

def run_choke(packets):
    buffer = deque()
    stats = init_stats()
    choke_active = False
    for p in packets:
        if buffer and random.random() < ROUTER_SPEED:
            proc_p = buffer.popleft()
            stats[proc_p.type]['served'] += 1
        if len(buffer) > CHOKE_THRESHOLD:
            choke_active = True
        elif len(buffer) < CHOKE_THRESHOLD / 2:
            choke_active = False
        dropped = False
        if choke_active:
            if p.type == 'Gold':
                if len(buffer) < BUFFER_SIZE: buffer.append(p)
                else: dropped = True
            else: dropped = True 
        else:
            if len(buffer) < BUFFER_SIZE: buffer.append(p)
            else: dropped = True
        if dropped: stats[p.type]['dropped'] += 1
    while buffer:
        proc_p = buffer.popleft()
        stats[proc_p.type]['served'] += 1
    return stats

def run_token_bucket(packets):
    buckets = {'Gold': [10, 10, 5.0], 'Silver': [5, 5, 0.5], 'Bronze': [2, 2, 0.2]}
    buffer = deque()
    stats = init_stats()
    for p in packets:
        for t in buckets:
            cur, cap, rate = buckets[t]
            buckets[t][0] = min(cap, cur + rate)
        if buffer and random.random() < ROUTER_SPEED:
            proc_p = buffer.popleft()
            stats[proc_p.type]['served'] += 1
        needed = 1
        if buckets[p.type][0] >= needed:
            if len(buffer) < BUFFER_SIZE:
                buckets[p.type][0] -= needed
                buffer.append(p)
            else: stats[p.type]['dropped'] += 1 
        else: stats[p.type]['dropped'] += 1 
    while buffer:
        proc_p = buffer.popleft()
        stats[proc_p.type]['served'] += 1
    return stats

def run_wfq(packets):
    priority_queue = [] 
    stats = init_stats()
    last_finish = {'Gold': 0, 'Silver': 0, 'Bronze': 0}
    for p in packets:
        if priority_queue and random.random() < ROUTER_SPEED:
            _, proc_p = heapq.heappop(priority_queue)
            stats[proc_p.type]['served'] += 1
        prev_f = last_finish[p.type]
        virtual_finish = max(p.arrival_time, prev_f) + (p.size / WEIGHTS[p.type])
        p.finish_time = virtual_finish
        last_finish[p.type] = virtual_finish
        if len(priority_queue) < BUFFER_SIZE:
            heapq.heappush(priority_queue, (p.finish_time, p))
        else:
            if p.type == 'Gold':
                victim_index = -1
                for i, item in enumerate(priority_queue):
                    if item[1].type == 'Bronze':
                        victim_index = i
                        break
                if victim_index != -1:
                    victim = priority_queue.pop(victim_index)
                    heapq.heapify(priority_queue)
                    stats['Bronze']['dropped'] += 1
                    stats['Bronze']['served'] -= 0 
                    heapq.heappush(priority_queue, (p.finish_time, p))
                else: stats['Gold']['dropped'] += 1
            else: stats[p.type]['dropped'] += 1
    while priority_queue:
        _, proc_p = heapq.heappop(priority_queue)
        stats[proc_p.type]['served'] += 1
    return stats

# ==========================================
# 2. RUN SIMULATION & PLOT
# ==========================================
print("Running simulations... please wait.")
traffic = generate_traffic(TOTAL_PACKETS)
stats_list = [
    run_baseline(traffic.copy()),
    run_choke(traffic.copy()),
    run_token_bucket(traffic.copy()),
    run_wfq(traffic.copy())
]
methods = ['Baseline', 'Choke', 'Token', 'WFQ']

# --- DATA PREP ---
gold_loss_pct = []
gold_drops = []
silver_drops = []
bronze_drops = []

for s in stats_list:
    g_total = s['Gold']['served'] + s['Gold']['dropped']
    g_loss = (s['Gold']['dropped'] / g_total * 100) if g_total > 0 else 0
    gold_loss_pct.append(g_loss)
    
    gold_drops.append(s['Gold']['dropped'])
    silver_drops.append(s['Silver']['dropped'])
    bronze_drops.append(s['Bronze']['dropped'])

# --- PLOTTING ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Plot 1: Gold Packet Loss (The Metric that Matters)
bars = ax1.bar(methods, gold_loss_pct, color=['#ff4d4d', '#2ecc71', '#2ecc71', '#27ae60'])
ax1.set_title('Gold Packet Loss % (Lower is Better)', fontsize=14, fontweight='bold')
ax1.set_ylabel('Loss Percentage (%)')
ax1.set_ylim(0, 40)
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Add text labels on bars
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
             f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

# Plot 2: Drop Distribution (The Sacrifice)
x = np.arange(len(methods))
width = 0.25

r1 = ax2.bar(x - width, gold_drops, width, label='Gold', color='#FFD700')
r2 = ax2.bar(x, silver_drops, width, label='Silver', color='#C0C0C0')
r3 = ax2.bar(x + width, bronze_drops, width, label='Bronze', color='#CD7F32')

ax2.set_title('Packet Drops by Priority Class', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(methods)
ax2.legend()
ax2.set_ylabel('Number of Dropped Packets')
ax2.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()