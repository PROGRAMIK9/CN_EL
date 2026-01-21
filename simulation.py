import time
import random
import heapq  # Needed for WFQ to sort by finish time
from collections import deque

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
BUFFER_SIZE = 5          # Max packets the router can hold
TOTAL_PACKETS = 50000        # Total packets to simulate per method
CHOKE_THRESHOLD = 10      # If buffer has >10 packets, trigger CHOKE
ROUTER_SPEED = 0.7  # The router is slower than the traffic (70% capacity)

# Weights for WFQ (Higher isn't always better in formula, see explanation below)
# In WFQ, we divide packet length by weight. Larger weight = Smaller Finish Time = Served Faster.
WEIGHTS = {'Gold': 4.0, 'Silver': 2.0, 'Bronze': 1.0}

# ==========================================
# 2. THE PACKET CLASS
# ==========================================
class Packet:
    def __init__(self, id, type, arrival_time):
        self.id = id
        self.type = type          # Gold, Silver, Bronze
        self.arrival_time = arrival_time
        self.size = random.randint(1, 3) # Random packet size (for WFQ calculation)
        self.finish_time = 0      # Calculated later for WFQ
        
    def __repr__(self):
        return f"[{self.type}#{self.id}]"

    # --- THE FIX IS HERE ---
    def __lt__(self, other):
        # If finish times are equal, the packet with the smaller ID goes first.
        return self.id < other.id

# ==========================================
# 3. HELPER: TRAFFIC GENERATOR
# ==========================================
def generate_traffic(n):
    """Generates a mixed list of Gold, Silver, and Bronze packets."""
    packets = []
    types = ['Gold', 'Silver', 'Bronze']
    for i in range(n):
        p_type = random.choice(types)
        packets.append(Packet(i, p_type, i)) # Arrival time implies order 'i'
    return packets

def init_stats():
    return {
        'Gold':   {'served': 0, 'dropped': 0},
        'Silver': {'served': 0, 'dropped': 0},
        'Bronze': {'served': 0, 'dropped': 0}
    }
# ==========================================
# 4. SIMULATION ENGINES
# ==========================================

# --- METHOD A: BASELINE (Tail Drop / FIFO) ---
def run_baseline(packets):
    print("Running Baseline...")
    buffer = deque()
    stats = init_stats()
    
    for p in packets:
        # 1. Simulate Slow Router (Service)
        if buffer and random.random() < ROUTER_SPEED:
            proc_p = buffer.popleft()
            stats[proc_p.type]['served'] += 1
            
        # 2. Enqueue
        if len(buffer) < BUFFER_SIZE:
            buffer.append(p)
        else:
            stats[p.type]['dropped'] += 1 # Drop everyone equally
            
    # Flush remaining
    while buffer:
        proc_p = buffer.popleft()
        stats[proc_p.type]['served'] += 1
            
    return stats

# --- METHOD B: CHOKE PACKET (Gold Protected) ---
def run_choke(packets):
    print(f"\n--- RUNNING CHOKE PACKET METHOD ---")
    buffer = deque()
    choke_active = False # Flag indicates if network is congested
    
    stats = {
        'Gold':   {'served': 0, 'dropped': 0},
        'Silver': {'served': 0, 'dropped': 0},
        'Bronze': {'served': 0, 'dropped': 0}
    }

    for p in packets:
        # 1. Service a packet
        if buffer and random.random() < ROUTER_SPEED: 
            processed_p = buffer.popleft()
            stats[processed_p.type]['served'] += 1
        
        # 2. Check Congestion Status
        if len(buffer) > CHOKE_THRESHOLD:
            choke_active = True
        elif len(buffer) < CHOKE_THRESHOLD / 2: # Hysteresis: turn off when calm
            choke_active = False
            
        # 3. Admission Control
        dropped = False
        if choke_active:
            if p.type == 'Gold':
                if len(buffer) < BUFFER_SIZE:
                    buffer.append(p)
                else:
                    dropped = True
            else:
                dropped = True # Intentionally throttle Silver/Bronze
        else:
            if len(buffer) < BUFFER_SIZE:
                buffer.append(p)
            else:
                dropped = True
        if dropped:
            stats[p.type]['dropped'] += 1 # Track dropped type

    # Flush buffer
    while buffer:
        processed_p = buffer.popleft()
        stats[processed_p.type]['served'] += 1

    return stats

# --- METHOD C: TOKEN BUCKET (QoS Shaping) ---
def run_token_bucket(packets):
    print("Running Token Bucket...")
    # [Current Tokens, Max Capacity, Refill Rate]
    buckets = {
        'Gold':   [10, 10, 2.0], 
        'Silver': [5,  5,  1.0], 
        'Bronze': [2,  2,  0.5] 
    }
    
    buffer = deque()
    stats = init_stats()
    
    for p in packets:
        # 1. Refill Tokens
        for t in buckets:
            cur, cap, rate = buckets[t]
            buckets[t][0] = min(cap, cur + rate)
            
        # 2. Service
        if buffer and random.random() < ROUTER_SPEED:
            proc_p = buffer.popleft()
            stats[proc_p.type]['served'] += 1
            
        # 3. Admission (Needs Token AND Buffer Space)
        needed = 1
        if buckets[p.type][0] >= needed:
            if len(buffer) < BUFFER_SIZE:
                buckets[p.type][0] -= needed # Spend token
                buffer.append(p)
            else:
                stats[p.type]['dropped'] += 1 # Has token, but buffer full
        else:
            stats[p.type]['dropped'] += 1 # No token (Throttled)

    while buffer:
        proc_p = buffer.popleft()
        stats[proc_p.type]['served'] += 1
            
    return stats

# --- METHOD 4: WEIGHTED FAIR QUEUING (WFQ) ---
def run_wfq(packets):
    print("Running WFQ...")
    priority_queue = [] # Heap
    stats = init_stats()
    
    # Virtual Time Tracking
    last_finish = {'Gold': 0, 'Silver': 0, 'Bronze': 0}
    
    for p in packets:
        # 1. Service (Smallest Finish Time First)
        if priority_queue and random.random() < ROUTER_SPEED:
            _, proc_p = heapq.heappop(priority_queue)
            stats[proc_p.type]['served'] += 1
            
        # 2. Calculate Finish Time
        prev_f = last_finish[p.type]
        weight = WEIGHTS[p.type]
        # virtual_finish = max(arrival, prev_finish) + (size / weight)
        virtual_finish = max(p.arrival_time, prev_f) + (p.size / weight)
        
        p.finish_time = virtual_finish
        last_finish[p.type] = virtual_finish
        
        # 3. Enqueue
        if len(priority_queue) < BUFFER_SIZE:
            heapq.heappush(priority_queue, (p.finish_time, p))
        else:
            stats[p.type]['dropped'] += 1
            
    while priority_queue:
        _, proc_p = heapq.heappop(priority_queue)
        stats[proc_p.type]['served'] += 1
            
    return stats

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    traffic = generate_traffic(TOTAL_PACKETS)
    
    s_base  = run_baseline(traffic.copy())
    s_choke = run_choke(traffic.copy())
    s_token = run_token_bucket(traffic.copy())
    s_wfq   = run_wfq(traffic.copy())
    
    def print_row(name, stats):
        gs, gd = stats['Gold']['served'], stats['Gold']['dropped']
        ss, sd = stats['Silver']['served'], stats['Silver']['dropped']
        bs, bd = stats['Bronze']['served'], stats['Bronze']['dropped']
        
        # Calculate percentages
        g_loss = (gd / (gs+gd)*100) if (gs+gd) else 0
        b_loss = (bd / (bs+bd)*100) if (bs+bd) else 0
        
        print(f"{name:<15} | {gs:>5} {gd:>5} | {ss:>5} {sd:>5} | {bs:>5} {bd:>5} | {g_loss:>6.1f}% | {b_loss:>6.1f}%")

    print(f"\n{'='*85}")
    print(f"{'METHOD':<15} | {'GOLD (S/D)':^11} | {'SILVER (S/D)':^11} | {'BRONZE (S/D)':^11} | {'G LOSS':^7} | {'B LOSS':^7}")
    print(f"{'-'*85}")
    
    print_row("Baseline", s_base)
    print_row("Choke (Gold)", s_choke)
    print_row("Token Bucket", s_token)
    print_row("WFQ", s_wfq)
    print(f"{'='*85}")
    print("Explanation: S = Served, D = Dropped. G LOSS = % of Gold packets lost.")