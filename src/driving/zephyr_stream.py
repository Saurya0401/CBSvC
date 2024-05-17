"""
Provides a Zephyr biometrics data stream, transmitting data via OSC.
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
    osc_process,
    osc_terminate
)


class ZephyrStream:
    """
    Handles the Zephyr biometrics data stream and sends biometrics data via a pipe.

    Attributes:
        child_conn (Connection): Multiprocessing connection for communication.
        ip (str): IP address for OSC client and server.
        port (int): Port number for OSC client and server.
        gen_inlet (StreamInlet): Inlet for the resolved Zephyr stream.
    """

    def __init__(self, child_conn, ip='127.0.0.1', port=8000):
        """
        Initializes the ZephyrStream with OSC setup and resolves the biometrics stream.

        Args:
            child_conn (Connection): Multiprocessing connection for communication.
            ip (str, optional): IP address for OSC client and server. Defaults to '127.0.0.1'.
            port (int, optional): Port number for OSC client and server. Defaults to 8000.
        """
        self.child_conn = child_conn
        self.ip = ip
        self.port = port

        osc_startup()
        osc_udp_client(self.ip, self.port, 'udplisten')
        osc_udp_server(self.ip, self.port, 'udpclient')

        # Resolve streams
        self.gen_inlet = self.resolve_streams()


    def resolve_streams(self):
        """
        Resolves available LSL streams and initializes the Zephyr biometrics stream.

        Returns:
            StreamInlet: Inlet for the resolved Zephyr stream.
        """
        logging.info("Looking for an EEG stream...")
        streams = resolve_streams()
        gen_stream = None
        for stream in streams:
            if stream.name() == 'ZephyrSummary':
                gen_stream = stream
        gen_inlet = StreamInlet(gen_stream)

        logging.info('Initializing ZephyrGeneral...')
        self.child_conn.send('Zephyr stream is working!')

        return gen_inlet

    def get_biometrics(self, gen_inlet):
        """
        Extracts biometrics data from the Zephyr stream.

        Args:
            gen_inlet (StreamInlet): Inlet for the resolved Zephyr stream.

        Returns:
            list: Heart rate and breathing rate from the biometrics data.
        """
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
        logging.info('batt. percent: %s', str(gen_sample[9]))
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
    """
    Monitors the Zephyr biometrics stream and sends data via OSC.

    Args:
        child_conn (Connection): Multiprocessing connection for communication.
        debug (bool, optional): Flag to enable debug logging. Defaults to False.
    """
    logging.basicConfig(
        format='ZEPHYR-%(levelname)s: %(message)s',
        level=logging.DEBUG if debug else logging.INFO
    )
    zephyr_stream = ZephyrStream(child_conn)
    while True:
        if zephyr_stream.child_conn.poll():
            zephyr_stream.child_conn.close()
            break

        live = zephyr_stream.get_biometrics(zephyr_stream.gen_inlet)
        osc_process()

        hr = str(live[0])
        br = str(live[1])

        # send data to CARLA
        data = [hr, br]
        logging.debug('HR: %s, BR: %s', hr, br)
        zephyr_stream.child_conn.send(data)

    osc_terminate()


if __name__ == '__main__':
    logging.basicConfig(format='ZEPHYR-%(levelname)s: %(message)s', level=logging.DEBUG)
    parent_conn, child_conn = Pipe()
    p = Process(target=monitor_and_send_biometrics, args=(child_conn, True))
    try:
        p.start()
        logging.info(str(parent_conn.recv()))
    except (AttributeError, TypeError, ValueError) as e:
        logging.error('Error initializing Zephyr stream: %s', e.args[0])
    except KeyboardInterrupt:
        logging.info('Cancelled by user. Bye!')
    finally:
        p.join()
