# SDN-Based QoS Traffic Prioritization

This repository contains a Software-Defined Networking (SDN) project that implements **Quality of Service (QoS)** management. Using the **Ryu Controller** and **Mininet**, we classify traffic based on protocol and dynamically assign it to prioritized hardware queues on an Open vSwitch (OVS).

## 🚀 Overview
In a standard network, all traffic is treated equally ("Best Effort"). This project demonstrates how an SDN controller can:
1.  **Identify** traffic types (TCP vs. UDP).
2.  **Tag** specific protocols for priority.
3.  **Enforce** bandwidth limits using hardware queues.

## 🛠 Prerequisites
* **OS:** Ubuntu 22.04 LTS (or similar)
* **Network:** Mininet & Open vSwitch (OVS)
* **Language:** Python 3.10+
* **Framework:** Ryu SDN Framework

## 🔧 Installation & Compatibility Patches
Ryu requires specific patches to run on Python 3.10+ due to changes in the `collections` and `eventlet` libraries.

```bash
# 1. Install Ryu
pip3 install ryu

# 2. Fix Eventlet version issues
pip3 uninstall eventlet -y
pip3 install eventlet==0.33.3

# 3. Patch Ryu for Python 3.10 Collections compatibility
sed -i 's/collections.Callable/collections.abc.Callable/g' ~/.local/lib/python3.10/site-packages/ryu/utils.py
sed -i 's/collections.MutableMapping/collections.abc.MutableMapping/g' ~/.local/lib/python3.10/site-packages/ryu/lib/ovs/bridge.py
sed -i 's/collections.MutableMapping/collections.abc.MutableMapping/g' ~/.local/lib/python3.10/site-packages/dns/namedict.py

# 4. Patch Ryu WSGI for Eventlet compatibility
sed -i 's/from eventlet.wsgi import ALREADY_HANDLED/ALREADY_HANDLED = object()/g' ~/.local/lib/python3.10/site-packages/ryu/app/wsgi.py
```

## 💻 How to Run
### 1. Launch the Network
In the first terminal, start the Mininet topology:
```bash
sudo mn --custom topology.py --topo qostopo --controller remote --switch ovs,protocols=OpenFlow13
```

### 2. Configure Hardware Queues
In a second terminal, define the "Slow Lane" (1 Mbps) and "Fast Lane" (10 Mbps).
We use the provided `setup_queues.sh` script to cleanly apply these rules (this script clears old queues and can be easily modified for multi-switch topologies):

Make the script executable (only needed once) and run it:
```bash
chmod +x setup_queues.sh
./setup_queues.sh
```
*(Note: To test across multi-switch topologies, edit `setup_queues.sh` and add to the `INTERFACES` array, e.g., `"s1-eth2" "s2-eth2" "s3-eth2"`).*

### 3. Start the Ryu Controller
In a third terminal, start the prioritization logic:
```bash
ryu-manager qos_controller.py
```

## 📊 Verification & Results
To verify the QoS enforcement, run tests from the Mininet CLI demonstrating functional correctness, throughput, and latency.

### 1. Throughput & Routing Behavior
We assign heavy bulk data to the "Slow Lane" and priority to the "Fast Lane". The controller logs will demonstrate the match-action mapping applied dynamically based on protocol.

| Traffic Type | Protocol | Routing Logic | Expected Bandwidth | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Best Effort**| TCP | Assigned to Queue 0 | **~1.0 Mbps** | Throttled |
| **Priority** | UDP | Assigned to Queue 1 | **~10.0 Mbps** | Prioritized |
| **Control** | ICMP | Assigned to Queue 1 | **Low latency** | Prioritized |

* **TCP Test:** `h1 iperf -c h2 -t 10`
* **UDP Test:** `h1 iperf -u -c h2 -b 10M -t 10`

### 2. Measuring Latency Impact
To prove that our controller successfully separates and prioritizes traffic, we will intentionally flood the Slow Lane (Queue 0) with a heavy TCP flow, and then measure the latency of our Fast Lane (Queue 1) using ICMP pings.

**Complete Test Sequence:**
1. **Start the TCP Server in the background:** (Prepare the receiver)
   ```bash
   mininet> h2 iperf -s &
   ```
2. **Start the TCP Flood in the background:** (Congest the Slow Lane from h1 to h2)
   ```bash
   mininet> h1 iperf -c 10.0.0.2 -t 60 &
   ```
3. **Run your Ping Test:** (Measure Fast Lane latency)
   ```bash
   mininet> h1 ping -c 20 h2
   ```

**Expected Results:** 
Because the TCP flood is restricted to the 1 Mbps Queue 0, the ICMP ping (which is routed by the controller to Queue 1) will bypass the congestion entirely. You should observe average ping latencies (RTT) of around `~0.4 ms` with 0% packet loss, completely unaffected by the massive TCP data transfer occurring on the exact same physical link!

### 3. Controller & Flow Observations
Verify flow logic by checking the controller output in the terminal or inspecting the switches:
```bash
mininet> dpctl dump-flows
```
*Note: Due to the `idle_timeout=20` and `hard_timeout=60` programmed into `qos_controller.py`, the flow rules will automatically delete themselves from the switch if no traffic is seen for 20 seconds. You must run `dpctl dump-flows` **while** the traffic is actively running to see the `set_queue` actions applied!*

---

## 📂 File Structure
* `topology.py`: Defines the 2-host, 1-switch network.
* `qos_controller.py`: Ryu application for MAC learning and QoS tagging.
* `README.md`: Project documentation.
