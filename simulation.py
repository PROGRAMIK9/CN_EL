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

# ==========================================
# 4. SIMULATION ENGINES
# ==========================================

# --- METHOD A: BASELINE (Tail Drop / FIFO) ---
def run_baseline(packets):
    print(f"\n--- RUNNING BASELINE (Tail Drop) ---")
    buffer = deque()
    dropped = 0
    served = 0
    
    for p in packets:
        # 1. Process (Service) a packet if buffer has one
        if buffer:
            buffer.popleft() # Simulate sending one packet out
            served += 1
            
        # 2. Try to Enqueue new packet
        if len(buffer) < BUFFER_SIZE:
            buffer.append(p)
        else:
            # Buffer full -> DROP!
            # print(f"Dropped {p}") # Optional logging
            dropped += 1
            
    return served, dropped

def run_baseline_congested(packets):
    print(f"\n--- RUNNING BASELINE (Congested) ---")
    buffer = deque()
    dropped = 0
    served = 0
    
    for p in packets:
        # --- CHANGE 1: SIMULATE SLOW ROUTER ---
        # Only process a packet 70% of the time. 
        # 30% of the time, the router is "busy" and nothing leaves, but new packets keep coming.
        if buffer and random.random() < ROUTER_SPEED:
            buffer.popleft()
            served += 1
            
        # 2. Try to Enqueue (This happens every single time, 100% rate)
        if len(buffer) < BUFFER_SIZE:
            buffer.append(p)
        else:
            dropped += 1 # NOW this will actually happen!
            
    # --- CHANGE 2: FLUSH THE BUFFER (Fixing the 49999 issue) ---
    # After traffic stops, finish processing whatever is left in the queue
    while buffer:
        buffer.popleft()
        served += 1
            
    return served, dropped

# --- METHOD B: CHOKE PACKET (Gold Protected) ---
def run_choke_packet(packets):
    print(f"\n--- RUNNING CHOKE PACKET METHOD ---")
    buffer = deque()
    dropped = 0
    served = 0
    choke_active = False # Flag indicates if network is congested
    
    for p in packets:
        # 1. Service a packet
        if buffer and random.random() < ROUTER_SPEED: 
            buffer.popleft()
            served += 1
        
        # 2. Check Congestion Status
        if len(buffer) > CHOKE_THRESHOLD:
            choke_active = True
        elif len(buffer) < CHOKE_THRESHOLD / 2: # Hysteresis: turn off when calm
            choke_active = False
            
        # 3. Admission Control
        if choke_active:
            # If Choke is ON, we DROP Silver/Bronze to save space.
            # GOLD is IGNORED (Protected) and allowed in.
            if p.type == 'Gold':
                if len(buffer) < BUFFER_SIZE:
                    buffer.append(p)
                else:
                    dropped += 1 # Only drop Gold if physically full
            else:
                dropped += 1 # Intentionally drop Silver/Bronze to throttle
        else:
            # Normal operation
            if len(buffer) < BUFFER_SIZE:
                buffer.append(p)
            else:
                dropped += 1
                
    return served, dropped

# --- METHOD C: TOKEN BUCKET (QoS Shaping) ---
def run_token_bucket(packets):
    print(f"\n--- RUNNING TOKEN BUCKET (QoS) ---")
    # Each class has its own bucket of tokens
    # Format: [Current Tokens, Max Capacity, Refill Rate]
    buckets = {
        'Gold':   [10, 10, 2], # Rich bucket, refills fast
        'Silver': [5,  5,  1], # Medium bucket
        'Bronze': [2,  2,  0.5]# Poor bucket, refills slow
    }
    
    buffer = deque()
    dropped = 0
    served = 0
    
    for p in packets:
        # 1. Refill Logic (Simulated)
        for type in buckets:
            cur, cap, rate = buckets[type]
            buckets[type][0] = min(cap, cur + rate) # Add tokens, don't exceed max
            
        # 2. Service Packet from buffer
        if buffer and random.random() < ROUTER_SPEED: 
            buffer.popleft()
            served += 1
        # 3. Admission (Need a token to enter buffer)
        needed_tokens = 1 # Each packet costs 1 token
        
        if buckets[p.type][0] >= needed_tokens:
            if len(buffer) < BUFFER_SIZE:
                buckets[p.type][0] -= needed_tokens # Deduct token
                buffer.append(p)
            else:
                dropped += 1 # Has token, but buffer full
        else:
            dropped += 1 # Not enough tokens (Shaped/Throttled)
            
    return served, dropped

# --- METHOD D: WEIGHTED FAIR QUEUING (WFQ) ---
def run_wfq(packets):
    print(f"\n--- RUNNING WEIGHTED FAIR QUEUING (WFQ) ---")
    # Instead of a deque (FIFO), we use a Heap (Priority Queue)
    # The heap sorts by 'Finish Time'
    priority_queue = [] 
    dropped = 0
    served = 0
    
    # State tracking for virtual time
    last_finish_time = {'Gold': 0, 'Silver': 0, 'Bronze': 0}
    
    for p in packets:
        # 1. Service (Process the packet with SMALLEST finish time)
        #if priority_queue:
         #   heapq.heappop(priority_queue)
          #  served += 1
        if priority_queue and random.random() < ROUTER_SPEED:
            heapq.heappop(priority_queue)
            served += 1 
        # 2. Calculate Finish Time (The Mathematical Formula)
        # Formula: Finish = max(Arrival, Previous_Finish) + (Length / Weight)
        # Since arrival is essentially 'now' in this loop:
        prev_finish = last_finish_time[p.type]
        weight = WEIGHTS[p.type]
        
        # Virtual Finish Calculation
        virtual_finish = max(p.arrival_time, prev_finish) + (p.size / weight)
        
        p.finish_time = virtual_finish
        last_finish_time[p.type] = virtual_finish
        
        # 3. Enqueue
        if len(priority_queue) < BUFFER_SIZE:
            # Heap stores tuples: (sort_key, item)
            heapq.heappush(priority_queue, (p.finish_time, p))
        else:
            dropped += 1
            
    return served, dropped

# ==========================================
# 5. MAIN EXECUTION & COMPARISON
# ==========================================
if __name__ == "__main__":
    traffic_data = generate_traffic(TOTAL_PACKETS)
    
    # Run all 4
    base_s, base_d = run_baseline_congested(traffic_data.copy())
    choke_s, choke_d = run_choke_packet(traffic_data.copy())
    token_s, token_d = run_token_bucket(traffic_data.copy())
    wfq_s,   wfq_d   = run_wfq(traffic_data.copy())
    
    print(f"\n{'='*40}")
    print(f"{'METHOD':<20} | {'SERVED':<10} | {'DROPPED':<10}")
    print(f"{'-'*40}")
    print(f"{'Baseline (FIFO)':<20} | {base_s:<10} | {base_d:<10}")
    print(f"{'Choke (Gold Safe)':<20} | {choke_s:<10} | {choke_d:<10}")
    print(f"{'Token Bucket':<20} | {token_s:<10} | {token_d:<10}")
    print(f"{'WFQ (Formula)':<20} | {wfq_s:<10} | {wfq_d:<10}")
    print(f"{'='*40}")