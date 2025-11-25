from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import EventMixin
import os
import json

log = core.getLogger()

class Firewall(EventMixin):
    def __init__(self, rules_file, dpid):
        self.listenTo(core.openflow)
        self.rules = []
        self.mac_table = {}
        self.firewall_dpid = int(dpid)

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

        return True

    def _handle_PacketIn(self, event):
        dpid = event.connection.dpid
        if dpid != self.firewall_dpid:
            return
        packet = event.parsed
        log.info("Llego PacketIn en el switch %s", event.connection.dpid)

        for rule in self.rules:
            if self.packet_matches_rule(rule, packet):
                log.info("Bloqueado: regla=%s", rule)
                event.halt = True
                return

def launch(rules="rules_file.json", dpid=1):
    core.registerNew(Firewall, rules, dpid)
