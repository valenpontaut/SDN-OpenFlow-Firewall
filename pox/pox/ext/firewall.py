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
        dpid = event.connection.dpid

        if dpid != self.firewall_dpid:
            return 
        
        log.info(">>> REGISTRANDO FIREWALL EN SWITCH %s", dpid)
        for rule in self.rules:
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match()
            msg.match.dl_type = 0x0800   # IPv4

            # Protocolos
            if "protocol" in rule:
                proto = rule["protocol"].upper()
                if proto == "TCP": msg.match.nw_proto = 6
                elif proto == "UDP": msg.match.nw_proto = 17
                elif proto == "ICMP": msg.match.nw_proto = 1

            # IPs
            if "src_ip" in rule:
                msg.match.nw_src = rule["src_ip"]
            if "dst_ip" in rule:
                msg.match.nw_dst = rule["dst_ip"]

            # Puertos
            if "src_port" in rule:
                msg.match.tp_src = int(rule["src_port"])
            if "dst_port" in rule:
                msg.match.tp_dst = int(rule["dst_port"])

            if rule.get("action", "DENY").upper() == "ALLOW":
                msg.actions.append(of.ofp_action_output(port=of.OFPP_NORMAL))
                msg.priority = 10
                log.info("Regla ALLOW instalada: %s", rule)
            else:
                msg.priority = 20  # Más alta para DROP
                log.info("Regla DROP instalada: %s", rule)

            event.connection.send(msg)

        log.info(">>> Todas las reglas fueron instaladas correctamente")


def launch(rules="rules_file.json", dpid=1):
    core.registerNew(Firewall, rules, dpid)