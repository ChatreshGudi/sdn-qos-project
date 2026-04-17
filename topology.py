from mininet.topo import Topo

class QoSTopo(Topo):
    """
    A simple custom topology for testing QoS priority queues.
    This creates a single Open vSwitch and connects two hosts to it.
    Traffic flows between h1 and h2 through s1, where QoS queues are applied.
    """
    def build(self):
        # Add host 1 with a static IP address
        h1 = self.addHost('h1', ip='10.0.0.1')
        
        # Add host 2 with a static IP address
        h2 = self.addHost('h2', ip='10.0.0.2')
        
        # Add a single Open vSwitch
        s1 = self.addSwitch('s1')
        
        # Connect both hosts to the central switch.
        # Flow rules will be installed on s1 to manage traffic between the hosts.
        self.addLink(h1, s1)
        self.addLink(h2, s1)

# Register the topology so it can be invoked via the Mininet CLI
# Example: sudo mn --custom topology.py --topo qostopo
topos = {'qostopo': (lambda: QoSTopo())}
