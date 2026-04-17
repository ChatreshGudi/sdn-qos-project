# SDN QoS Controller: Testing and Verification Guide

This guide provides detailed steps on how to verify your SDN Quality of Service (QoS) controller using Mininet. It covers how to inspect the flow rules installed on your switches, how to scale to multi-switch topologies, and how to accurately test the latency and bandwidth to ensure your QoS priority queues are working correctly.

---

## 1. Inspecting Flow Tables

To verify that your SDN controller is actually inserting the correct OpenFlow rules for QoS (such as directing traffic to specific queues), you need to dump the flow tables of your virtual switches.

### Dumping Flows for a Specific Switch
You can use the `ovs-ofctl` command. In the Mininet CLI, prepend `sh` to execute a shell command on the host.

1. **Start your Mininet topology** and controller.
2. In the Mininet CLI, run:
   ```bash
   mininet> sh ovs-ofctl dump-flows s1
   ```
3. **What to look for:** Look at the output for rules containing your specific match criteria (e.g., `nw_src`, `nw_dst`, `tp_port`) and check the `actions` field. If QoS is applied correctly, you should see actions like `actions=set_queue:1,output:2` or `actions=enqueue:2:1` (which means output to port 2 via queue 1).

### Dumping Flows for All Switches
To quickly see the flows across all switches in the topology simultaneously:
```bash
mininet> dpctl dump-flows
```

---

## 2. Testing with Multi-Switch Topologies

Your SDN controller handles multi-switch setups by viewing the entire network centrally. The key difference in testing multi-switch networks is that QoS queues and routing rules must be installed on **every** switch along the data path.

### Starting Multi-Switch Topologies in Mininet
Start Mininet with a custom topology to test multi-hop QoS routing:

- **Linear Topology (e.g., 4 switches connected in a line):**
  ```bash
  sudo mn --controller=remote --topo=linear,4 --mac --switch=ovsk
  ```

- **Tree Topology (e.g., depth 2, fanout 2):**
  ```bash
  sudo mn --controller=remote --topo=tree,depth=2,fanout=2 --mac --switch=ovsk
  ```

*Note: You must ensure that your external script initializing the `ovs-vsctl` queues targets the physical interfaces on all switches in the path, not just `s1`.*

---

## 3. Verifying QoS: Latency and Bandwidth Testing

To prove that your QoS controller works, you need to create network congestion. QoS only takes effect when a link's bandwidth is maxed out. We will use `iperf` to flood the network with low-priority traffic, and then use `ping` to measure the latency of high-priority traffic.

### Step 3.1: Establish a Baseline (No Congestion)
First, verify normal latency when the network is empty.
```bash
mininet> h1 ping -c 5 h2
```
*Observe the `time=X.XX ms`. This should be extremely low (usually <1ms).*

### Step 3.2: Create Background Congestion (Low Priority)
Assume `h1` sending to `h2` is considered **Low Priority** traffic by your controller. We will flood the network using UDP.

1. Open separate terminal windows for the hosts:
   ```bash
   mininet> xterm h1 h2
   ```
2. In the **h2 terminal** (Receiver), start the iperf server:
   ```bash
   iperf -s -u -i 1
   ```
3. In the **h1 terminal** (Sender), start flooding the link. *(Adjust `-b 10M` to a value higher than your configured link bottleneck/queue limit to ensure congestion).*
   ```bash
   iperf -c 10.0.0.2 -u -b 10M -t 60 -i 1
   ```

### Step 3.3: Measure Premium Traffic Latency (High Priority)
Assume `h3` sending to `h4` is configured by your controller as **High Priority** traffic (e.g., assigned to a premium queue).

While the `iperf` flood is actively running in the background, send ping packets from `h3` to `h4`:
```bash
mininet> h3 ping h4
```

### 4. Interpreting the Results

*   **If QoS is WORKING:** The ping times between `h3` and `h4` should remain low and stable, very close to the baseline measured in Step 3.1, with 0% packet loss. This signifies that your switch is prioritizing the ICMP packets over the flooded UDP packets.
*   **If QoS is NOT WORKING:** The ping times between `h3` and `h4` will spike significantly (hundreds of milliseconds) or packets will be dropped entirely. This occurs because the switch processes all packets equally, and the link is overwhelmed by the `h1` to `h2` traffic.
*   **Bandwidth Verification:** If you look at the `iperf` server output on `h2`, you will see packet loss and a drop in received bandwidth, which confirms the switch is intentionally dropping the low-priority traffic to make room for your high-priority pings.
