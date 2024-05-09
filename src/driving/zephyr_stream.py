"""
Provides zephyr biometrics data stream
"""

import logging
from multiprocessing import Pipe, Process

# Bioharness
from pylsl import StreamInlet, resolve_streams

# Open Sound Control (OSC)
from osc4py3.as_eventloop import *
from osc4py3 import oscmethod as osm

import numpy as np


class ZephyrStream:

    def __init__(self, child_conn, ip='127.0.0.1', port=8000):
        self.child_conn = child_conn
        self.ip = ip
        self.port = port
        self.gsr_val = 0

        osc_startup()
        osc_udp_client(self.ip, self.port, 'udplisten')
        osc_udp_server(self.ip, self.port, 'udpclient')

        # Associate Python functions with message address patterns, using defaults argument
        osc_method('/edaMikroS', self.handler_func, argscheme=osm.OSCARG_DATAUNPACK)

        # Resolve streams
        self.gen_inlet, self.rr_inlet = self.resolve_streams()


    def resolve_streams(self):
        logging.info("Looking for an EEG stream...")
        streams = resolve_streams()
        gen_stream = None
        rr_stream = None
        for stream in streams:
            if stream.name() == 'ZephyrGeneral':
                gen_stream = stream
            elif stream.name() == 'ZephyrRtoR':
                rr_stream = stream
        gen_inlet = StreamInlet(gen_stream)
        rr_inlet = StreamInlet(rr_stream)

        logging.info('Initializing ZephyrGeneral...')
        self.child_conn.send('Zephyr stream is working!')
        logging.info('PAST STREAMS')

        return gen_inlet, rr_inlet


    def get_biometrics(self, gen_inlet, rr_inlet):
        gen_sample, _ = gen_inlet.pull_sample()
        rr_sample, _ = rr_inlet.pull_sample()
        hr = gen_sample[2]
        br = gen_sample[3]
        rr = rr_sample[0]
        return np.array([hr, br, rr])

    def handler_func(self, *args):
        for arg in args:
            self.gsr_val = arg

    def monitor_and_send_biometrics(self):
        while True:
            if self.child_conn.poll():
                self.child_conn.close()
                break

            live = self.get_biometrics(self.gen_inlet, self.rr_inlet)
            osc_process()

            live_stress = np.append(live, self.gsr_val)
            hr = str(live_stress[0])
            br = str(live_stress[1])
            gsr = str(live_stress[2])

            # send data to CARLA
            data = [hr, br, gsr]
            logging.debug('HR: %s, BR: %s, GSR: %s', str(hr), str(br), str(gsr))
            self.child_conn.send(data)

        osc_terminate()


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    parent_conn, child_conn = Pipe()
    zephyr_stream = ZephyrStream(child_conn)
    p = Process(target=zephyr_stream.monitor_and_send_biometrics)
    try:
        p.start()
        print(parent_conn.recv())   # prints "Hello"
    finally: 
        pass 
