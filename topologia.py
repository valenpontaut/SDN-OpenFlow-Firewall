#!/usr/bin/env python3
import argparse
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.term import makeTerms

YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"


class ChainTopo(Topo):
    def build(self, n_switches=3):
        if n_switches < 1:
            raise ValueError("n_switches debe ser >= 1")

        h1 = self.addHost("h1", ip="10.0.0.1/24")
        h2 = self.addHost("h2", ip="10.0.0.2/24")
        h3 = self.addHost("h3", ip="10.0.0.3/24")
        h4 = self.addHost("h4", ip="10.0.0.4/24")

        switches = []
        for i in range(1, n_switches + 1):
            s = self.addSwitch(f"s{i}", dpid=f"{i:016x}")
            switches.append(s)

        self.addLink(h1, switches[0])
        self.addLink(h2, switches[0])

        for i in range(len(switches) - 1):
            self.addLink(switches[i], switches[i + 1])

        self.addLink(switches[-1], h3)
        self.addLink(switches[-1], h4)


def show_network_info(net):
    """Muestra configuración de interfaces y colas (qdisc) de hosts y switches."""
    print(f"\n{YELLOW}{'#' * 62}{RESET}")
    print(f"{YELLOW}======== Interface and IP Configuration ========={RESET}")
    for h in net.hosts:
        print(f"\n[{h.name}] ifconfig:")
        print(h.cmd("ifconfig"))

    print(f"\n{YELLOW}{'#' * 62}{RESET}")
    print(f"{YELLOW}========== Qdisc (Queue) Configuration =========={RESET}")

    for h in net.hosts:
        for intf in h.intfList():
            print(f"\n[{h.name}] {intf}:")
            print(h.cmd(f"tc qdisc show dev {intf}"))

    for s in net.switches:
        for intf in s.intfList():
            print(f"\n[{s.name}] {intf}:")
            print(s.cmd(f"tc qdisc show dev {intf}"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chain topology for OpenFlow TP")
    parser.add_argument(
        "--switches",
        type=int,
        default=3,
        help="Number of switches in the chain (default: 3)",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Display detailed interface and queue information",
    )
    parser.add_argument(
        "--ctrl-ip",
        dest="ctrl_ip",
        default="127.0.0.1",
        help="Remote controller IP (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--ctrl-port",
        dest="ctrl_port",
        type=int,
        default=6633,
        help="Remote controller port (default: 6633 - POX default)",
    )
    args = parser.parse_args()

    net = Mininet(
        topo=ChainTopo(n_switches=args.switches),
        link=TCLink,
        switch=OVSKernelSwitch,
        controller=None,
        autoSetMacs=True,
        autoStaticArp=True,
    )

    # Controlador remoto (POX con l2_learning)
    c0 = net.addController(
        "c0",
        controller=RemoteController,
        ip=args.ctrl_ip,
        port=args.ctrl_port,
    )

    net.start()

    if args.info:
        show_network_info(net)

    print(f"\n{GREEN}Topology initialized successfully{RESET}\n")
    print(f"{YELLOW}Hosts en la topología:{RESET}")
    for h in net.hosts:
        print(f"  - {h.name} ({h.IP()})")
    print(f"{YELLOW}Switches en la topología:{RESET}")
    for s in net.switches:
        print(f"  - {s.name}")

    makeTerms(net.hosts)
    CLI(net)

    net.stop()
    print(f"\n{YELLOW}Network stopped and resources released{RESET}\n")
