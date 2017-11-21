import _thread
import time
from threading import Thread

from pymodbus.client.sync import ModbusTcpClient
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSparseDataBlock
from pymodbus.server.sync import ModbusTcpServer

time_address = 0
ready_flag_address = 0
t_o_address = 100
t_zco_address = 200
t_cob_address = 420
f_cob_address = 422
ub_address = 424
tr_address = 426
CONTROLLER_IP = '192.168.1.115'
LOGGER_IP = '192.168.1.115'
OWN_IP = '192.168.1.116'
PORT = 5555


# example function registered after as a time callback
def step():
    print('doing some stuff')
    server.set_ready_flag()
    print(server.get_ready_flag())
    print(server.get_holding_register(time_address))
    print(time_address)

    logger.send_update()
    water_flow_controller.send_update()
    # set ready flag when you finish your job! it is really very important


class Receiver(ModbusTcpClient):
    def __init__(self, host, port, name):
        super(Receiver, self).__init__(host, port)
        self.name = name
        self.initialization = True

    def connected(self):
        return self.socket

    def get_name(self):
        return self.name


class WaterFlowController(Receiver):
    def __init__(self):
        super(WaterFlowController, self).__init__(CONTROLLER_IP, PORT, 'WaterFlowController')

    def send_update(self):
        super(WaterFlowController, self).write_register(t_cob_address, 420)
        super(WaterFlowController, self).write_register(f_cob_address, 422)


class Logger(Receiver):
    def __init__(self):
        super(Logger, self).__init__(LOGGER_IP, PORT, 'Logger')

    def send_update(self):
        super(Logger, self).write_register(t_cob_address, 420)
        super(Logger, self).write_register(f_cob_address, 422)
        super(Logger, self).write_register(ub_address, 424)
        super(Logger, self).write_register(tr_address, 426)


class CoilsDataBlock(ModbusSparseDataBlock):
    def __init__(self, values):
        super(CoilsDataBlock, self).__init__(values)
        self.time_flag_callback = None

    def setValues(self, address, values):
        super(CoilsDataBlock, self).setValues(address, values)
        if address == ready_flag_address:
            if (super(CoilsDataBlock, self).getValues(address, 1)) == [False]:
                _thread.start_new_thread(self.time_flag_callback, ())

    def set_time_flag_callback(self, function):
        self.time_flag_callback = function


class HoldingRegisterDataBlock(ModbusSparseDataBlock):
    def __init__(self, values):
        super(HoldingRegisterDataBlock, self).__init__(values)
        self.timestamp = 0
        self.time_callback = None

    def setValues(self, address, values):
        super(HoldingRegisterDataBlock, self).setValues(address, values)
        if address == time_address:
            self.timestamp = self.__calculate_timestamp__(values)

    def get_time(self):
        return self.timestamp

    @staticmethod
    def __calculate_timestamp__(register_values):
        time1 = register_values[0]
        time2 = register_values[1]
        return (time1 << 16) | time2


class Server:
    def __init__(self, address, port):
        self.holding_register_block = HoldingRegisterDataBlock.create()
        self.coil_block = CoilsDataBlock.create()
        self.store = ModbusSlaveContext(hr=self.holding_register_block, co=self.coil_block, zero_mode=True)
        self.context = ModbusServerContext(slaves=self.store, single=True)
        self.server = ModbusTcpServer(self.context, address=(address, port))
        self.thread = Thread(target=self.__run_thread__, args=())

    def __run_thread__(self):
        self.server.serve_forever()

    def run(self):
        self.thread.start()

    def stop(self):
        self.server.server_close()
        self.server.shutdown()
        self.thread.join()

    def get_holding_register(self, index):
        return self.holding_register_block.getValues(index, 1)

    def set_time_flag_callback(self, function):
        self.coil_block.set_time_flag_callback(function)

    def set_ready_flag(self):
        self.coil_block.setValues(ready_flag_address, True)

    def get_ready_flag(self):
        return self.coil_block.getValues(ready_flag_address, 1)

    def get_time(self):
        return self.holding_register_block.get_time()


if __name__ == '__main__':
    # start new server
    server = Server(OWN_IP, 5555)
    # add a callback function which will be called with new timestamp each time new time is received
    server.set_time_flag_callback(step)
    # run the server
    server.run()
    print('Server is running')

    water_flow_controller = WaterFlowController()
    logger = Logger()
    close = False
    while not close:
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            close = True

    # remember to stop server while closing your application
    server.stop()

    print('finished!')