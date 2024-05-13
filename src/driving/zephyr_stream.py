"""
Provides zephyr biometrics data stream
"""

import logging
from multiprocessing import Pipe, Process

# Bioharness
from pylsl import StreamInlet, resolve_streams

# Open Sound Control (OSC)
from osc4py3.as_eventloop import (
    osc_startup,
    osc_udp_client,
    osc_udp_server,
    osc_method,
    osc_process,
    osc_terminate
)
from osc4py3 import oscmethod as osm


gsr_val = 0


class ZephyrStream:

    def __init__(self, child_conn, ip='127.0.0.1', port=8000):
        self.child_conn = child_conn
        self.ip = ip
        self.port = port
        self.gsr_val = 0

        osc_startup()
        osc_udp_client(self.ip, self.port, 'udplisten')
        osc_udp_server(self.ip, self.port, 'udpclient')

        # Resolve streams
        self.gen_inlet = self.resolve_streams()


    def resolve_streams(self):
        logging.info("Looking for an EEG stream...")
        streams = resolve_streams()
        gen_stream = None
        for stream in streams:
            if stream.name() == 'ZephyrSummary':
                gen_stream = stream
        gen_inlet = StreamInlet(gen_stream)

        logging.info('Initializing ZephyrGeneral...')
        self.child_conn.send('Zephyr stream is working!')
        logging.info('PAST STREAMS')

        return gen_inlet

    def get_biometrics(self, gen_inlet):
        gen_sample, _ = gen_inlet.pull_sample()
        hr = gen_sample[2]
        br = gen_sample[3]
        # print(f'gen_sample = {gen_sample}')
        # print()
        # print('heart rate:', str(gen_sample[2]))
        # print('resp. rate:', str(gen_sample[3]))
        # print('skin temp:', str(gen_sample[4]))
        # print('posture:', str(gen_sample[5]))
        # print('activity:', str(gen_sample[6]))
        # print('peak acc.:', str(gen_sample[7]))
        # print('batt. voltage:', str(gen_sample[8]))
        print('batt. percent:', str(gen_sample[9]))
        # print('breathing wave amp.:', str(gen_sample[10]))
        # print('breathing wave noise.:', str(gen_sample[11]))
        # print('breathing wave conf.:', str(gen_sample[12]))
        # print('ecg amp.:', str(gen_sample[13]))
        # print('ecg noise:', str(gen_sample[14]))
        # print('heart rate conf:', str(gen_sample[15]))
        # print('heart rate var.:', str(gen_sample[16]))
        # print('system conf:', str(gen_sample[17]))
        # print('GSR:', str(gen_sample[18]))
        # print('Other vals:', [str(v) for v in gen_sample[18:]])
        # print()
        return [hr, br]


def monitor_and_send_biometrics(child_conn, debug=False):

    zephyr_stream = ZephyrStream(child_conn)
    while True:
        if zephyr_stream.child_conn.poll():
            zephyr_stream.child_conn.close()
            break

        live = zephyr_stream.get_biometrics(zephyr_stream.gen_inlet)
        osc_process()

        live_stress = [*live, gsr_val]
        hr = str(live_stress[0])
        br = str(live_stress[1])
        gsr = str(live_stress[2])

        # send data to CARLA
        data = [hr, br, gsr]
        if debug:
            print(f'HR: {hr}, BR: {br}, GSR: {gsr}')
        zephyr_stream.child_conn.send(data)

    osc_terminate()


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    parent_conn, child_conn = Pipe()
    p = Process(target=monitor_and_send_biometrics, args=(child_conn, True))
    try:
        p.start()
        print(str(parent_conn.recv()))
    except (AttributeError, TypeError, ValueError) as e:
        logging.error('Error initializing Zephyr stream: %s', e.args[0])
    except KeyboardInterrupt:
        logging.info('Cancelled by user. Bye!')
    finally:
        p.join()
