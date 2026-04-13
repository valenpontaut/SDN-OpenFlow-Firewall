# SDN OpenFlow Firewall

Implementación de una red definida por software (SDN) utilizando el protocolo **OpenFlow** sobre un entorno emulado con **Mininet** y el controlador **POX**.

Se implementa una topología en cadena de switches OpenFlow con un módulo de **firewall configurable por archivo JSON**, aplicado sobre un único switch de la cadena, combinado con un módulo de **L2 learning switch** para el resto del tráfico.

**Integrantes:**
- Milton Formiga
- María Agustina Fontana
- Santiago Novaro
- Franco Daniel Capra
- Valentina Llanos Pontaut


## Arquitectura

### Topología en cadena

```
h1 ──┐                          ┌── h3
     s1 ── s2 ── ... ── sN ────┤
h2 ──┘                          └── h4
```

- `h1` y `h2` se conectan al primer switch (`s1`)
- `h3` y `h4` se conectan al último switch (`sN`)
- La cantidad de switches es configurable por parámetro
- Cada switch tiene `dpid` igual a su índice (`s1` → dpid=1, `s2` → dpid=2, etc.)
- Todos los switches se configuran como Open vSwitch (OVS) conectados a un controlador remoto

### Controlador POX

El plano de control combina dos módulos:

- **`forwarding.l2_learning`**: learning switch de capa 2, aprende MACs por puerto y encamina el tráfico normalmente.
- **`ext.firewall`**: módulo propio que instala reglas OpenFlow (`ofp_flow_mod`) en el switch designado como firewall. Las reglas se definen en un archivo JSON externo y matchean tráfico IPv4 por protocolo, IPs y/o puertos. Los flujos se instalan sin acciones, lo que en OpenFlow 1.0 implica que el tráfico coincidente se descarta directamente en el switch.

El firewall solo se aplica en el switch cuyo `dpid` coincide con el configurado. El resto de los switches operan únicamente con L2 learning.

### Estructura de archivos

```
~/pox/pox/ext/
├── firewall.py          # Módulo del firewall
└── rules_file.json      # Reglas del firewall (JSON)

~/topologia.py           # Script de Mininet
```

---

## Requisitos

```bash
sudo apt-get update
sudo apt-get install mininet xterm
```

También se necesita tener **POX** instalado.

---

## Ejecución

### 1. Iniciar el controlador POX

```bash
./pox/pox.py log.level --DEBUG ext.firewall --rules=rules_file.json --dpid=2 forwarding.l2_learning
```

| Parámetro | Obligatorio | Descripción | Default |
|---|---|---|---|
| `log.level --DEBUG` | No | Nivel de log detallado | INFO |
| `--rules` | No* | Archivo JSON con las reglas del firewall | `rules_file.json` |
| `--dpid` | No* | Switch que actuará como firewall (por su dpid) | `1` |

*Requeridos por la consigna del TP.

### 2. Iniciar la topología en Mininet

En otra terminal, mientras POX está corriendo:

```bash
sudo python3 topologia.py --switches 3 --ctrl-ip 127.0.0.1 --ctrl-port 6633
```

| Parámetro | Tipo | Descripción | Default |
|---|---|---|---|
| `--switches` | int | Cantidad de switches en la cadena | `3` |
| `--ctrl-ip` | string | IP del controlador remoto | `127.0.0.1` |
| `--ctrl-port` | int | Puerto TCP del controlador | `6633` |
| `--info` | flag | Muestra configuración de interfaces y colas al iniciar | `False` |

### 3. Pruebas desde el CLI de Mininet

```bash
mininet> pingall
mininet> iperf h1 h3
mininet> h1 iperf -c 10.0.0.4 -p 80
mininet> h4 iperf -s -u -p 5001
```

### 4. Finalizar

```bash
mininet> exit
sudo mn -c   # limpia interfaces virtuales
```

Detener POX con `Ctrl+C`.

---

## Formato de reglas (`rules_file.json`)

Cada regla puede especificar los siguientes campos (todos opcionales salvo que la consigna lo requiera):

```json
[
  {
    "nw_proto": 6,
    "tp_dst": 80
  },
  {
    "nw_proto": 17,
    "nw_src": "10.0.0.1",
    "tp_dst": 5001
  },
  {
    "nw_src": "10.0.0.2",
    "nw_dst": "10.0.0.3"
  }
]
```

| Campo | Descripción |
|---|---|
| `nw_proto` | Protocolo IP (6=TCP, 17=UDP) |
| `nw_src` | IP de origen |
| `nw_dst` | IP de destino |
| `tp_src` | Puerto de origen |
| `tp_dst` | Puerto de destino |

Todo tráfico que matchee una regla es **descartado** en el switch firewall.

---

## Pruebas realizadas

| Escenario | Resultado esperado |
|---|---|
| Sin reglas (`rules_file.json` vacío) | `pingall` con 0% de pérdida entre h1, h2, h3, h4 |
| Bloqueo TCP puerto destino 80 | h4 no recibe tráfico HTTP desde ningún host |
| Bloqueo UDP desde h1 al puerto 5001 | Paquetes descartados en s2, no llegan a s2-eth2 |
| Bloqueo entre dos hosts específicos | 100% packet loss entre el par bloqueado, resto de la red sin afectar |

Las capturas de Wireshark sobre `s2-eth1` y `s2-eth2` confirman que el tráfico coincidente con las reglas no avanza más allá del switch firewall, mientras que el tráfico no afectado continúa fluyendo normalmente.