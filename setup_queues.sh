#!/bin/bash

# Define the list of switch ports that need the QoS queues applied.
# By default, it targets the single-switch topology (s1-eth2). 
# For multi-switch setups, add more egress interfaces (e.g., "s1-eth2" "s2-eth2" "s3-eth2")
INTERFACES=("s1-eth2")

# Clear existing QoS on all switches first to prevent leftover configuration conflicts
sudo ovs-vsctl --all destroy QoS
sudo ovs-vsctl --all destroy Queue

echo "Applying QoS to switches..."

# Loop through each interface and apply the HTB queues
for INTF in "${INTERFACES[@]}"
do
  echo "Setting up queues for $INTF..."
  sudo ovs-vsctl set Port $INTF qos=@newqos -- \
  --id=@newqos create QoS type=linux-htb other-config:max-rate=10000000 queues=0=@q0,1=@q1 -- \
  --id=@q0 create Queue other-config:max-rate=1000000 -- \
  --id=@q1 create Queue other-config:max-rate=10000000
done

echo "QoS configuration complete!"
