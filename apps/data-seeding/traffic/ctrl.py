# standard imports
import socket
import os
import queue
import logging
import threading

logg = logging.getLogger(__name__)


def _default_socket(basepath='.'):
    sp = os.path.join(basepath, 'traffic.sock')
    try:
        os.stat(sp)
        os.unlink(sp)
    except FileNotFoundError:
        pass
    
    sck = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sck.settimeout(0.5)
    sck.bind(sp)
    sck.listen(1)

    logg.info('RPC socket path is {}'.format(sp))
    return (sck, sp,)


class Ctrl(threading.Thread):

    def __init__(self):
        super(Ctrl, self).__init__()
        (self.sck, self.sp) = _default_socket()
        self.q_req = queue.SimpleQueue()
        self.q_res = queue.SimpleQueue()
        self.req = {}
        self.handler = None
        self.q_quit = queue.Queue(1)
        self.q_quit.put("")
        self.req_c = 0


    def __del__(self):
        self.sck.close()
        os.unlink(self.sp)


    def set_handler(self, handler):
        self.handler = handler


    def quit(self):
        self.q_quit.get()
        self.join()


    def __check_quit(self):
        try:
            self.q_quit.put_nowait("")
        except queue.Full:
            return False
        return True


    def __process_responses(self):
        while True:
            msg = None
            try:
                msg = self.q_res.get_nowait()
            except queue.Empty:
                return
            try:
                conn = self.req[msg[0]]
            except KeyError:
                logg.error('invalid rpc request id {}'.format(msg[0]))
                continue

            if msg[1] != None:
                conn.sendall(msg[1].encode('utf-8'))

            conn.close()
            del self.req[msg[0]]


    def run(self):
        while True:
            conn = None
            addr = None
            try:
                conn, addr = self.sck.accept()
            except socket.timeout:
                if self.__check_quit():
                    logg.info('rpc shutdown rquested')
                    return
                self.__process_responses()
                continue

            cmd = None
            arg = None
            v = conn.recv(1024)
            try:
                (cmd, arg) = v.split(b' ', 1)
            except ValueError:
                cmd = v.rstrip()
                logg.debug('cmd is {}'.format(cmd))
            cmd = cmd.decode('utf-8')
            
            try:
                getattr(self, 'rpc_' + cmd)
            except AttributeError:
                logg.error('unknown rpc command {}'.format())
                continue

            if arg != None:
                arg = arg.decode('utf-8')
                arg = arg.rstrip()
           
            req_id = id(conn)
            self.req[req_id] = conn

            self.q_req.put((req_id, cmd, arg,))


    def process(self):
        while True:
            cmd = None
            arg = None
            conn = None
            try:
                (req_id, cmd, arg) = self.q_req.get_nowait()
            except queue.Empty:
                break

            m = getattr(self, 'rpc_' + cmd)
            m(req_id, arg)


    def rpc_i(self, req_id, v):
        router = self.handler.traffic_router
        s = ''
        for i in range(len(router.items)):
            s += '{} {} {}\n'.format(i, router.items[i].__name__, router.item_weights[i])
        self.q_res.put((req_id, s,))
