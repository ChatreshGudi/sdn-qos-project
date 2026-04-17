from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import packet, ethernet, ipv4

class SimpleQoS(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleQoS, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, hard_timeout=0, idle_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, 
                                instructions=inst, hard_timeout=hard_timeout, idle_timeout=idle_timeout)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn the MAC address to avoid flooding next time
        self.mac_to_port[dpid][src] = in_port

        # Determine output port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # If the destination MAC is known, we can install a specific flow rule rather than just forwarding.
        if out_port != ofproto.OFPP_FLOOD:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            
            # QoS Classification Logic
            # We classify packets based on their IPv4 protocol number and assign them to hardware queues.
            if ip_pkt:
                # Explicit protocol handling based on project requirements:
                if ip_pkt.proto == 6:  # TCP Traffic
                    # TCP is assigned to Queue 0 (Best Effort / Slow Lane - e.g. 1 Mbps)
                    # This prevents bulk data transfers from consuming all bandwidth.
                    q_id = 0
                    proto_name = "TCP"
                    
                elif ip_pkt.proto == 17:  # UDP Traffic
                    # UDP is assigned to Queue 1 (Priority / Fast Lane - e.g. 10 Mbps)
                    # Used for time-sensitive or streaming data.
                    q_id = 1
                    proto_name = "UDP"
                    
                elif ip_pkt.proto == 1:  # ICMP Traffic (Ping)
                    # ICMP is assigned to Queue 1 (Priority / Fast Lane)
                    # This guarantees low-latency pings even when Queue 0 is completely congested.
                    q_id = 1
                    proto_name = "ICMP"
                    
                else:
                    # All other IPv4 traffic defaults to Best Effort (Queue 0)
                    q_id = 0
                    proto_name = "OTHER IPv4"

                self.logger.info("Packet_In: %s received, src=%s, dst=%s, mapping to Queue %d", proto_name, ip_pkt.src, ip_pkt.dst, q_id)

                # Set the action to push the packet into the assigned queue before outputting it.
                actions = [parser.OFPActionSetQueue(queue_id=q_id), parser.OFPActionOutput(out_port)]
                match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, ip_proto=ip_pkt.proto, ipv4_dst=ip_pkt.dst, ipv4_src=ip_pkt.src)
                
                # Add flow to the switch's flow table.
                # idle_timeout=20: The rule deletes itself if no packets match it for 20 seconds.
                # hard_timeout=60: The rule deletes itself absolutely after 60 seconds regardless of traffic.
                # This prevents the switch memory from filling up with old rules (which is why dump-flows may appear empty after testing).
                self.add_flow(datapath, 10, match, actions, idle_timeout=20, hard_timeout=60)

        # Send packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
