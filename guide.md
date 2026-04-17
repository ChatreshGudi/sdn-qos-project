# SDN QoS Controller: Complete Testing & Verification Guide

This guide details exactly how to test and prove that your SDN Controller and Open vSwitch (OVS) hardware queues are actively analyzing traffic and enforcing Quality of Service (QoS).

---

## 1. Traffic Separation & Latency Testing

The ultimate test of QoS is demonstrating that low-priority "Best Effort" congestion cannot disrupt high-priority "Fast Lane" ping latency. 

Based on your `qos_controller.py` logic:
*   **TCP Traffic** = Assigned to Queue 0 (Slow Lane, 1 Mbps)
*   **ICMP Traffic (Ping)** = Assigned to Queue 1 (Fast Lane, 10 Mbps)
*   **UDP Traffic** = Assigned to Queue 1 (Fast Lane, 10 Mbps)

### The Definitive Test (TCP vs. ICMP)
We will swamp the "Slow Lane" with an enormous TCP data transfer and prove that ICMP pings in the "Fast Lane" bypass the traffic jam.

1.  **Start the TCP Server on h2:** Wait for incoming connections.
    ```bash
    mininet> h2 iperf -s &
    ```
2.  **Start the TCP Flood from h1:** Send an unlimited TCP data flood for 60 seconds.
    ```bash
    mininet> h1 iperf -c 10.0.0.2 -t 60 &
    ```
3.  **Run the Ping Test:** Ping while the TCP flood is ongoing.
    ```bash
    mininet> h1 ping -c 20 h2
    ```

**Interpreting the Results:**
If QoS is working, the TCP data is forcefully trapped by the switch inside Queue 0. When your ICMP pings arrive, the controller recognizes them and puts them into the completely empty Queue 1. You should see an average Round Trip Time (RTT) of less than `1.0 ms` with `0% packet loss`. *This is the definitive proof of your QoS controller working.*

---

## 2. Bandwidth Shaping & Queue Limitations (UDP Test)

What happens if you flood the "Fast Lane" itself? Because both UDP and ICMP share Queue 1, if you flood UDP, your pings will get stuck in queue buffers.

1.  Start a UDP server:
    ```bash
    mininet> h2 iperf -u -s &
    ```
2.  Flood UDP traffic at 20 Mbps (which is higher than Queue 1's 10 Mbps limit):
    ```bash
    mininet> h1 iperf -u -c 10.0.0.2 -b 20M -t 60 &
    ```
3.  Run the Ping Test simultaneously:
    ```bash
    mininet> h1 ping -c 20 h2
    ```

**Interpreting the Results:**
Queue 1 gets completely saturated by UDP. You will observe the average ping latency jump to `~150 ms`. Because the Queue 1 traffic limit was set to 10 Mbps in `setup_queues.sh`, the switch prevents the 20 Mbps flood from taking over, naturally shaping it down to ~7.5 - 10 Mbps. 

---

## 3. Inspecting Flow Tables

To verify the OpenFlow rules your Ryu controller installs, use `ovs-ofctl` or `dpctl`.

```bash
mininet> dpctl dump-flows
```

### Why is my flow table empty? (The Timeout Feature)
If you run `dpctl dump-flows` after your test finishes and you only see `priority=0 actions=CONTROLLER:65535`, you might think the controller failed. **This is normal and intended!**

In your `qos_controller.py`, the flow rules are explicitly installed with:
`idle_timeout=20, hard_timeout=60`

This means Open vSwitch automatically deletes the flow rules if no packets match them for 20 seconds. This prevents the switch memory from filling up over time. 
*To see the actual `set_queue` actions, you MUST run `dpctl dump-flows` in the middle of an active ping or iperf test before the timeout expires!*

---

## 4. Multi-Switch Topologies

When moving beyond a single switch, QoS queues must be applied to all forwarding egress interfaces in the topology path. 

Use the provided `setup_queues.sh` script to automate this. 
Simply edit the script before running it:

```bash
# Edit setup_queues.sh and update this array
INTERFACES=("s1-eth2" "s2-eth2" "s3-eth2")
```

When you start your custom linear or tree topology, running `./setup_queues.sh` will ensure the hardware queues are applied everywhere, allowing end-to-end QoS.
