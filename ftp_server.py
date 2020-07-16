"""
ftp_server.py
TERM PROJECT FOR POSTECH CSED353 SPRING 2020
IMPLEMENTED BY JINHO KO (jinho.ko@postech.ac.kr)
DISTRIBUTION OR COMMERCIAL USE ONLY AVAILABLE UPON APPROVAL OF THE AUTHOR.
"""

""" load libraries """
import socket
import os
import enum
import csv
import copy
import sys
import subprocess
import traceback
import random
from time import gmtime, strftime
from threading import Thread

""" configuration """
SFTP_FOLDER_PATH = os.path.expanduser("~") + "/.sftp-jhko/"
USER_TABLE_PATH = SFTP_FOLDER_PATH + "auth.csv"
ADMIN_ID = 'admin'
ADMIN_PW = 'adminpw'
CONN_BUFFER_SIZE = 10240000 # 10MB
DATA_BLOCK_SIZE = 2048000 # 2MB
KEEPALIVE_SEC = 60
RESEND_COUNT = 5
SFTP_DISCRIMINATOR_TOKEN = b'dg'


""" MSGTYPE """
@enum.unique
class MsgToSend(enum.Enum):

    ALIVE_CHECK = enum.auto()
    AUTH_PROCEED = enum.auto()  # 02 auth
    AUTH_FAILURE = enum.auto()
    AUTH_SUCCESS = enum.auto()
    CD_PATHERR = enum.auto()    # 05 cd
    CD_PROCEED = enum.auto()
    CD_SUCCESS = enum.auto()
    PWD_SUCCESS = enum.auto()   # 08 pwd
    LS_PATHERR = enum.auto()    # 09 ls
    LS_PROCEED = enum.auto()
    LS_DATA = enum.auto()
    LS_SUCCESS = enum.auto()
    LS_FAILURE = enum.auto()
    GET_PATHERR = enum.auto()   # 15 get
    GET_PROCEED = enum.auto()
    GET_DATA = enum.auto()
    GET_SUCCESS = enum.auto()
    GET_FAILURE = enum.auto()
    PUT_PATHERR =  enum.auto()  # 20 put
    PUT_PROCEED =  enum.auto()
    PUT_SUCCESS =  enum.auto()
    PUT_FAILURE =  enum.auto()
    EXIT_SUCCESS = enum.auto()  # 24 exit

@enum.unique
class MsgToRecv(enum.Enum):

    ALIVE_SIGNAL = enum.auto()  # 01 alive signal
    AUTH_HI = enum.auto()       # 02 auth
    AUTH_ID = enum.auto()
    AUTH_PW = enum.auto()
    CMD_CD = enum.auto()        # 05 cmd
    CMD_PWD = enum.auto()
    CMD_LS = enum.auto()
    CMD_GET = enum.auto()
    CMD_PUT = enum.auto()
    CMD_EXIT = enum.auto()
    CD_PROCEED = enum.auto()    # 11 cd
    LS_PROCCED = enum.auto()    # 12 ls
    GET_PROCEED = enum.auto()   # 13 get
    GET_STOP = enum.auto()
    PUT_PROCEED = enum.auto()   # 15 put
    PUT_STOP = enum.auto()
    PUT_DATA = enum.auto()

""" in each thread """
class ClientThread(Thread):

    def __init__(self, conn, ip, port):
        Thread.__init__(self)
        self.conn = conn
        self.ip = ip
        self.port = port

        self.conn_buffer_size = copy.deepcopy(CONN_BUFFER_SIZE)
        self.user_table_path = copy.deepcopy(USER_TABLE_PATH)
        self.last_conn_time = copy.deepcopy(KEEPALIVE_SEC)
        self.token = copy.deepcopy(SFTP_DISCRIMINATOR_TOKEN)

        self.user_info = "" # filled at auth stage.
        self.pwd = os.path.expanduser("~") + '/' # initialized to user base path

    def authenticate(self):

        # MSG1 : recv hello
        (m1t, m1) = self.recv()
        # MSG2 : send hello back
        self.send( MsgToSend.AUTH_PROCEED, 'hello+back')
        # MSG3 :recv id
        (m3t, m3) = self.recv()
        # MSG4 : send what is pw
        self.send(MsgToSend.AUTH_PROCEED , 'givemepw')

        while True:
            # MSG5 : recv pw
            (m5t, m5) = self.recv()
            # open file read mode and query password
            with open(self.user_table_path, 'r') as f:
                auth_granted = False
                ff = csv.reader(f)
                for line in ff:
                    if line[0] == m3.decode() and line[1] == m5.decode():
                        auth_granted = True
                f.close()
            if auth_granted:
                self.user_info = m3.decode()
                break
            else:
                # MSG6: send passwd error
                self.send( MsgToSend.AUTH_FAILURE , 'passwderror')
        # MSG7 : send auth ok
        self.send( MsgToSend.AUTH_SUCCESS , 'auth ok')
        return

    def terminate(self):

        try:
            self.send(MsgToSend.EXIT_SUCCESS)
        except:
            pass

        print('[INFO] client at {}:{} thread terminated.'.format(self.ip, self.port))
        # exit thread
        sys.exit()

    def recv(self):

        recv_binary = b''
        msg_len = -1
        firstMsgArrived = False
        while True:
            recved = self.conn.recv(self.conn_buffer_size)
            recv_binary = recv_binary + recved
            if recv_binary[:2] != b'dg':
                return (MsgToRecv.PUT_STOP, b'')
            if not firstMsgArrived:
                msg_len = int(recv_binary[2:10])
                firstMsgArrived = True
            if len(recv_binary) >= msg_len :
                break

        recv_msgtype = MsgToRecv(int(recv_binary[10:12]))
        recv_data_bin = recv_binary[12:]

        if recv_msgtype == MsgToRecv.CMD_EXIT:
            self.terminate()

        return recv_msgtype, recv_data_bin  # (MsgToRecv, bytes)

    def send(self, send_msgtype, send_data=''):

        send_msgtype_bin = str(send_msgtype.value).zfill(2).encode()
        send_data_bin = send_data if type(send_data) is bytes \
                                    else send_data.encode()
        send_binary = send_msgtype_bin + send_data_bin
        send_len_bin = str(int(len(send_binary))+10).zfill(8).encode()
        send_binary = self.token + send_len_bin + send_binary

        self.conn.send(send_binary)


    def absolutify(self, path_str):
        if path_str[0] != '/':  # convert to abs. path
            path_str = self.pwd + ('/' if self.pwd[-1]!='/' else '') \
                                    + path_str
        return path_str

    def existance_check(self, path_str, isDir):
        if isDir:
            return os.path.isdir(self.absolutify(path_str))
        else: # isFile
            return os.path.isfile(self.absolutify(path_str))

    def get_absolute_path(self, path_str):
        return os.path.realpath(self.absolutify(path_str))

    def main_func(self):

        while True:
            # MSG1 : recv command and arguments
            (m1t, m1) = self.recv()

            # parse and verify arguments
            if m1t == MsgToRecv.ALIVE_SIGNAL :
                pass

            elif m1t == MsgToRecv.CMD_CD :
                path_str = m1.decode()
                if not self.existance_check(path_str, True):
                    self.send(MsgToSend.CD_PATHERR)
                    continue
                self.send(MsgToSend.CD_PROCEED)
                (m2t, m2) = self.recv()
                self.pwd = self.get_absolute_path(path_str)
                self.send(MsgToSend.CD_SUCCESS)

            elif m1t == MsgToRecv.CMD_PWD :
                self.send(MsgToSend.PWD_SUCCESS, self.pwd)

            elif m1t == MsgToRecv.CMD_LS :
                path_str = m1.decode()
                if len(m1)!=0 and (not self.existance_check(path_str, True)) :
                    self.send(MsgToSend.LS_PATHERR)
                    continue
                self.send(MsgToSend.LS_PROCEED)
                (m2t, m2) = self.recv()

                ls_data_bin = b''
                ls_success = True
                try:
                    if len(path_str) == 0 : # no arg
                        ls_data_bin = subprocess.Popen(['ls', self.pwd ], stdout=subprocess.PIPE) \
                            .communicate()[0]
                    else:
                        ls_data_bin = subprocess.Popen(['ls', path_str], stdout=subprocess.PIPE) \
                            .communicate()[0]

                    num_blocks = int( len(ls_data_bin) / DATA_BLOCK_SIZE) + 1
                    for idx, _ in enumerate(range(num_blocks)):
                        self.send(MsgToSend.LS_DATA,
                                  ls_data_bin[idx*DATA_BLOCK_SIZE : (idx+1)*DATA_BLOCK_SIZE] )
                        _, _ = self.recv()
                    self.send(MsgToSend.LS_DATA, '')
                    _, _ = self.recv()

                except Exception as e:
                    ls_success = False

                _ = self.send(MsgToSend.LS_SUCCESS) if ls_success \
                    else self.send(MsgToSend.LS_FAILURE)

            elif m1t == MsgToRecv.CMD_GET :
                path_str = m1.decode()
                if not self.existance_check(path_str, False) :
                    self.send(MsgToSend.GET_PATHERR, self.absolutify(path_str))
                    continue
                self.send(MsgToSend.GET_PROCEED, self.absolutify(path_str))
                (m2t, m2) = self.recv()
                if m2t != MsgToRecv.GET_PROCEED :
                    self.send(MsgToSend.GET_FAILURE)
                    continue

                file_addr = self.absolutify(path_str)
                try:
                    with open(file_addr, 'rb') as f:
                        while True:
                            data_frag_bin = f.read(DATA_BLOCK_SIZE)
                            self.send(MsgToSend.GET_DATA, data_frag_bin)
                            if not data_frag_bin : # empty ; end
                                break
                            m3t, m3 = self.recv()
                            if m3t == MsgToRecv.GET_STOP:
                                raise Exception
                except Exception as e:
                    self.send(MsgToSend.GET_FAILURE)

            elif m1t == MsgToRecv.CMD_PUT :
                m1_decoded = m1.decode()
                if len(m1_decoded) != 0 :
                    if not self.existance_check(m1_decoded, True) : # isDir
                        self.send(MsgToSend.PUT_PATHERR)
                        continue

                put_path = self.absolutify(m1_decoded) if m1_decoded else self.pwd
                put_path = put_path + ('' if put_path[-1] == '/' else '/')

                self.send(MsgToSend.PUT_PROCEED, self.absolutify(put_path))
                m2t, m2 = self.recv()

                # prepare
                file_name = m2.decode()
                tmpfile_name = str(random.randint(10000000, 99999999))  # 8-digit number
                tmpfile_name = '.' + tmpfile_name

                recv_success = False
                try:
                    with open(put_path + tmpfile_name, 'wb') as f:
                        while True:
                            self.send(MsgToSend.PUT_PROCEED)
                            m3t, m3 = self.recv()
                            if m3t == MsgToRecv.PUT_STOP:
                                raise Exception
                            if not m3 : # empty
                                recv_success = True
                                break
                            f.write(m3)
                except Exception as e:
                    pass
                    #traceback.print_exc()
                    #self.send(MsgToSend.PUT_FAILURE)

                if recv_success:
                    os.system('mv {} {}'.format(put_path + tmpfile_name, put_path + file_name))
                    continue
                os.system('rm {}'.format(put_path + tmpfile_name))

            elif m1t == MsgToRecv.CMD_EXIT :
                self.terminate()

    def run(self):

        try:
            self.authenticate()
            # main function
            self.main_func()
        except Exception as e:
            self.terminate()

""" receive connections and run threads """
def runServer(soc):

    threads = []
    while True:
        soc.listen(4)
        (cli_conn, (ip, port)) = soc.accept()
        cli_thread = ClientThread(cli_conn, ip, port)
        cli_thread.start()
        print('[INFO] client at {}:{} thread started.'.format(ip, port))
        threads.append(cli_thread)

        # if not alive) Collect and remove from thread list
        for th in threads:
            try:
                if not th.is_alive():
                    threads.remove(th)
                    th.join()
            except:
                pass

""" main """
def main(tcpIP, tcpPORT):

    """ init server """
    print("[INFO] server initialize")
    # user auth file
    if not os.path.isdir(SFTP_FOLDER_PATH):
        os.mkdir(SFTP_FOLDER_PATH)
    if not os.path.isfile(USER_TABLE_PATH):
        open(USER_TABLE_PATH, 'a').close()
    # always enable admin
    admin_exist = False
    f = open(USER_TABLE_PATH, 'r')
    ff = csv.reader(f)
    for line in ff:
        if 'admin' in line:
            admin_exist = True
    f.close()
    if not admin_exist:
        f = open(USER_TABLE_PATH, 'a')
        wr = csv.writer(f)
        wr.writerow([ADMIN_ID, ADMIN_PW])
        f.close()

    # open socket
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    soc.bind((tcpIP, tcpPORT))

    """ run """
    print("[INFO] server running in {} port {}".format(tcpIP, tcpPORT))
    runServer(soc)

    """ terminate server """
    sys.exit()

if __name__ == "__main__":

    tcpIP = '0.0.0.0'
    tcpPORT = 2022

    if len(sys.argv) >= 2 : # PORT option
        tcpPORT = int(sys.argv[1])

    print("[INFO] argparse OK")
    main(tcpIP, tcpPORT)