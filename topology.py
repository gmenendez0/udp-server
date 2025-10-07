from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import OVSController
from mininet.log import setLogLevel, info

class ClienteServidorTopo(Topo):
    def build(self):
        # Crear hosts
        cliente = self.addHost('h1')
        servidor = self.addHost('h2')
        switch = self.addSwitch('s1')

        # Enlaces con pérdida del 10%
        self.addLink(cliente, switch, cls=TCLink, loss=0)
        self.addLink(switch, servidor, cls=TCLink, loss=10)

def run():
    topo = ClienteServidorTopo()
    net = Mininet(topo=topo, controller=OVSController, link=TCLink)
    net.start()

    h1, h2 = net.get('h1', 'h2')
    info(f"h1 IP: {h1.IP()} | h2 IP: {h2.IP()}\n")

    # Ejecutar tu server.py en h2
    info("* Iniciando servidor en h2 *\n")
    h2.cmd('python3 -m server.start_server -H 10.0.0.2 -p 9999 server.log 2>&1 &')  # se ejecuta en segundo plano

    # Ejecutar tu client.py en h1
    info("* Iniciando cliente en h1 *\n")
    h1.cmd('python3 -m client.upload -s files/test.txt -n test_4mb.txt -H 10.0.0.2 -p 9999 -v client.log 2>&1')

    # Apagar red
    net.stop()


topos = {
    'clienteservidortopo': (lambda: ClienteServidorTopo())
}
if __name__ == '__main__':
    setLogLevel('info')
    run()