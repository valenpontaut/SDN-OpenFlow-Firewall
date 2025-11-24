from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import EventMixin
import os
import json

log = core.getLogger()

class Firewall(EventMixin):
    def __init__(self, rules_file):
        self.listenTo(core.openflow)
        self.rules = []
        self.mac_table = {}

        module_dir = os.path.dirname(__file__)
        rules_path = os.path.join(module_dir, rules_file)

        try:
            with open(rules_path, "r") as f:
                self.rules = json.load(f)
                log.info("Reglas cargadas: %s", self.rules)
        except Exception as e:
            log.error("NO se pudo cargar %s: %s", rules_file, e)

        log.info("Firewall habilitado")

    def _handle_ConnectionUp(self, event):
        log.info("Switch conectado (dpid=%s)", event.connection.dpid)

    def packet_matches_rule(self, rule, packet):
        #Devuelve True si el paquete coincide con la regla al llegar al final

        ip_packet = packet.find('ipv4')

        src_ip = dst_ip = proto = src_port = dst_port = None
        if ip_packet:
            src_ip = str(ip_packet.srcip)
            dst_ip = str(ip_packet.dstip)
            proto = ip_packet.protocol  

        l4 = packet.find('tcp') or packet.find('udp')
        if l4:
            src_port = l4.srcport
            dst_port = l4.dstport

        if "dst_port" in rule:
            if dst_port is None or int(rule["dst_port"]) != int(dst_port):
                return False

        if "src_port" in rule:
            if src_port is None or int(rule["src_port"]) != int(src_port):
                return False

        if "protocol" in rule:
            p = rule["protocol"].upper()
            if p == "UDP" and proto != 17:
                return False
            if p == "TCP" and proto != 6:
                return False
            if p == "ICMP" and proto != 1:
                return False

        if "src_ip" in rule:
            if src_ip != rule["src_ip"]:
                return False

        if "dst_ip" in rule:
            if dst_ip != rule["dst_ip"]:
                return False

        if "block_pair" in rule:
            a, b = rule["block_pair"]
            if not ip_packet:
                return False

            if (src_ip == a and dst_ip == b) or (src_ip == b and dst_ip == a):
                return True
            return False

        return True

    def _handle_PacketIn(self, event):
        log.info("Llego PacketIn en el switch %s", event.connection.dpid)

        packet = event.parsed
        dpid = event.connection.dpid
        in_port = event.port

        src = packet.src
        dst = packet.dst
        self.mac_table[(dpid, src)] = in_port

        for rule in self.rules:
            if self.packet_matches_rule(rule, packet):
                log.info("Bloqueado: regla=%s", rule)
                return

        if (dpid, dst) in self.mac_table:
            out_port = self.mac_table[(dpid, dst)]
        else:
            out_port = of.OFPP_FLOOD

        msg = of.ofp_packet_out()
        msg.data = event.data
        msg.in_port = in_port
        msg.actions.append(of.ofp_action_output(port=out_port))
        event.connection.send(msg)

def launch(rules="rules_file.json"):
    core.registerNew(Firewall, rules)
