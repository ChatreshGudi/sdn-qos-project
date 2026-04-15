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
In a second terminal, define the "Slow Lane" (1 Mbps) and "Fast Lane" (10 Mbps):
```bash
sudo ovs-vsctl set Port s1-eth2 qos=@newqos -- \
--id=@newqos create QoS type=linux-htb other-config:max-rate=10000000 queues=0=@q0,1=@q1 -- \
--id=@q0 create Queue other-config:max-rate=1000000 -- \
--id=@q1 create Queue other-config:max-rate=10000000
```

### 3. Start the Ryu Controller
In a third terminal, start the prioritization logic:
```bash
ryu-manager qos_controller.py
```

## 📊 Verification & Results
To verify the QoS enforcement, run `iperf` tests from the Mininet CLI.

| Traffic Type | Protocol | Logic | Measured Bandwidth | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Standard** | TCP | Assigned to Queue 0 | **~1.2 Mbps** | Throttled |
| **Priority** | UDP | Assigned to Queue 1 | **~9.0 Mbps** | Prioritized |

### Test Commands
* **TCP Test:** `h1 iperf -c h2 -t 10`
* **UDP Test:** `h1 iperf -u -c h2 -b 10M -t 10`

---

## 📂 File Structure
* `topology.py`: Defines the 2-host, 1-switch network.
* `qos_controller.py`: Ryu application for MAC learning and QoS tagging.
* `README.md`: Project documentation.
