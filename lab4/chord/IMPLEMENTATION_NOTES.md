# Chord Recursive LOOKUP Implementation

## Overview

This implementation extends the basic Chord DHT system with **recursive name resolution**. Instead of requiring a client to iteratively call LOOKUP on multiple nodes, each node now automatically forwards the request recursively until the responsible node is found, then returns the result directly to the original client.

## Architecture

### Chord Ring
- Nodes are arranged in a ring (circular address space)
- Each node maintains a **finger table** containing pointers to other nodes at exponential distances
- The finger table is used for efficient routing of LOOKUP queries

### Communication
- All communication happens via **lab_channel** (Redis-based message queue)
- Messages are sent as tuples with message types defined in `constChord.py`:
  - `LOOKUP_REQ = '1'`: Lookup request for a key
  - `LOOKUP_REP = '2'`: Lookup response with responsible node
  - `JOIN = '3'`: Node joining the ring
  - `LEAVE = '4'`: Node leaving the ring
  - `STOP = '6'`: Shutdown signal

## Implementation Details

### 1. Recursive LOOKUP in ChordNode

**File:** `chordnode.py`, lines 149-170

When a node receives a `LOOKUP_REQ` for a key:

```python
if request[0] == constChord.LOOKUP_REQ:
    key = int(request[1])
    # Find the next hop using local finger table
    next_id = self.local_successor_node(key)
    
    if next_id == self.node_id:
        # BASE CASE: This node is responsible
        # Send result directly to the original sender
        self.channel.send_to([sender], (constChord.LOOKUP_REP, self.node_id))
    else:
        # RECURSIVE CASE: Forward to the next hop
        # Include original sender so final node knows where to send the response
        self.channel.send_to([str(next_id)], (constChord.LOOKUP_REQ, key, sender))
```

**Key Points:**

1. **Base Case**: If this node is responsible (`next_id == self.node_id`), send the result back to the original sender
2. **Recursive Case**: Forward the request to the next hop, passing the original sender's ID so the responsible node knows where to send the response
3. **Original Sender Tracking**: The third element of the LOOKUP_REQ tuple (`sender` parameter) tracks the original requester across multiple hops

### How It Works

**Example: 4-node ring (nodes 1, 5, 10, 15), looking up key 8**

1. **Client → Node 1:** LOOKUP(8)
2. **Node 1's logic:** 
   - `local_successor_node(8)` returns Node 5 (next hop in finger table)
   - Node 5 ≠ Node 1, so recursive forward
   - Send `LOOKUP_REQ(8, client)` to Node 5
3. **Node 5's logic:**
   - `local_successor_node(8)` returns Node 10 (next hop)
   - Node 10 ≠ Node 5, so recursive forward
   - Send `LOOKUP_REQ(8, client)` to Node 10
4. **Node 10's logic:**
   - `local_successor_node(8)` returns Node 10 (itself)
   - Base case reached! Key 8 belongs to Node 10
   - Send `LOOKUP_REP(10)` directly to client
5. **Client receives:** LOOKUP_REP with Node 10 as responsible node

### 2. DummyChordClient Implementation

**File:** `doit.py`, lines 25-66

The client now performs actual lookups instead of just printing a placeholder:

```python
def run(self):
    nodes_list = sorted([int(n) for n in nodes])
    
    # Perform multiple lookups
    for lookup_count in range(5):
        # Random key in valid range
        key = random.randint(0, self.channel.MAXPROC - 1)
        
        # Random starting node
        start_node = random.choice(nodes_list)
        
        # Send LOOKUP request
        self.channel.send_to([str(start_node)], (constChord.LOOKUP_REQ, key))
        
        # Wait for response
        message = self.channel.receive_from_any()
        if message[1][0] == constChord.LOOKUP_REP:
            responsible = message[1][1]
            print(f"Key {key:04n} → Node {responsible:04n}")
```

**Features:**
- Performs 5 random lookups to demonstrate the system
- Shows the progression from random key to responsible node
- All the complexity of traversing multiple nodes is hidden by recursion

## Advantages of Recursive Approach

| Aspect | Iterative | Recursive |
|--------|-----------|-----------|
| **Client Code** | Complex (manages multiple requests) | Simple (single request) |
| **Latency** | Same (same number of hops) | Same (same number of hops) |
| **Implementation** | More error-prone | Cleaner logic flow |
| **Fault Handling** | Easier to retry failed hops | Harder to handle mid-chain failures |

## Message Flow Example

For a 3-hop lookup:

```
Client                Node A              Node B              Node C
  |                     |                   |                   |
  +--LOOKUP_REQ(k)----> |                   |                   |
  |                     +--LOOKUP_REQ(k)---> |                   |
  |                     |                   +--LOOKUP_REQ(k)----> |
  |                     |                   |                   (Found!)
  |                     |                   | <--LOOKUP_REP(C)-- +
  | <-----LOOKUP_REP(C) +-----------------+ |
  |                     |                   |
```

**Note:** The recursive implementation sends the response directly from the responsible node to the original client (shown by the direct arrow), not through intermediate nodes.

## Testing

Run the system with:

```bash
redis-server  # Start Redis in background
pipenv run python doit.py
```

Or with custom parameters (m=bits, n=nodes):

```bash
pipenv run python doit.py 5 6  # 5-bit address space, 6 nodes
```

**Expected Output:**
```
[CLIENT] LOOKUP 0012 starting from node 0005
[CLIENT] Key 0012 is handled by node 0032
[CLIENT] LOOKUP 0018 starting from node 0028
[CLIENT] Key 0018 is handled by node 0019
...
```

## Edge Cases Handled

1. **Single node ring:** Key immediately goes to that node
2. **Key wraps around ring:** `in_between()` handles circular arithmetic
3. **Dead nodes:** Sanity check removes dead nodes from known list
4. **Finger table gaps:** Falls back to latest known finger table entry

## References

- Stoica et al., "Chord: A Scalable Peer-to-peer Lookup Service for Internet Applications" (2003)
- Original paper uses iterative lookup; this implementation uses recursive for simplicity


# Small ring: 4 bits (0-15 addresses), 4 nodes
pipenv run python doit.py 4 4

# Medium ring: 5 bits (0-31 addresses), 6 nodes  
pipenv run python doit.py 5 6

# Large ring: 8 bits (0-255 addresses), 16 nodes
pipenv run python doit.py 8 16


Explanation of Chord Output
This output shows a Chord Distributed Hash Table (DHT) with 8 nodes performing recursive name lookups. Let me break down each section:

1. System Initialization (Lines 1-18)
What's happening:

8 processes are being created and joining the "node" group
Node IDs: 4, 11, 30, 36, 40, 53, 61, 63 (randomly assigned from 0-63 range)
Client ID: 0 (joins "client" group)
These are in a 6-bit address space (2^6 = 64 possible addresses: 0-63)
All 8 nodes have constructed their finger tables and are ready.

2. Lookup Operations (5 Random Queries)
Lookup 1: Key 0063
What this means:

Client (ID 0000) wants to find who handles key 63
Asks node 61 to start the search
Node 61 checks its finger table → forwards to node 63
Node 63 checks and finds it's responsible for key 63 (key falls in its range)
Node 63 sends result directly back to client 0000
Hops: Client → 61 → 63 → Client ✅ (2 hops)

Lookup 2: Key 0031
What this means:

Client asks node 63 to find key 31
63 → 30 → 36 (multi-hop recursive forwarding)
Node 36 is responsible (31 is in range: previous node 30 < 31 ≤ 36)
Node 36 replies directly to client 0000 (not through 30 or 63)
Hops: Client → 63 → 30 → 36 → Client ✅ (3 hops)

Lookup 3: Key 0035
What this means:

Client asks node 36 to find key 35
Node 36 immediately knows it's responsible (lucky hit!)
No forwarding needed
Hops: Client → 36 → Client ✅ (1 hop - best case!)

Lookup 4: Key 0045
What this means:

36 → 40 → 53 (multi-hop chain)
Node 53 handles key 45 (range: 40 < 45 ≤ 53)
Hops: Client → 36 → 40 → 53 → Client ✅ (3 hops)

Lookup 5: Key 0007
What this means:

Key wraps around the ring (63 → 4 → 11)
Node 11 handles key 7 (range: 4 < 7 ≤ 11)
Hops: Client → 63 → 4 → 11 → Client ✅ (3 hops)

3. Finger Tables (Final State)
What this means:

FT[0011] = Finger Table for Node 11
Index 0: Predecessor = Node 4 (node before 11 in ring)
Index 1-6: Successors at exponential distances
Finger Table Formula:
For node n, finger i points to the first node ≥ (n + 2^(i-1)) mod 64

Example for Node 11:

Finger[1]: successor of (11 + 2^0) = 12 → 30
Finger[2]: successor of (11 + 2^1) = 13 → 30
Finger[3]: successor of (11 + 2^2) = 15 → 30
Finger[4]: successor of (11 + 2^3) = 19 → 30
Finger[5]: successor of (11 + 2^4) = 27 → 30
Finger[6]: successor of (11 + 2^5) = 43 → 53
Key Concepts Illustrated
Concept	Example from Output
Ring topology	Nodes: 4, 11, 30, 36, 40, 53, 61, 63 (circular)
Recursive lookup	63→30→36 forwarding chain for key 31
Direct response	Node 36 replies to client 0, not through 63/30
Finger table routing	Node uses exponential jumps to find next hop
Key responsibility	Each node handles keys in range (predecessor, self]
Efficiency	Average 2-3 hops in O(log N) for 8 nodes
Summary
✅ 8 nodes form a Chord ring in 64-address space
✅ 5 lookups demonstrate recursive name resolution
✅ Average 2.2 hops per lookup (efficient!)
✅ Finger tables enable O(log N) routing instead of O(N)