"""
ftp_client.py
TERM PROJECT FOR POSTECH CSED353 SPRING 2020
IMPLEMENTED BY JINHO KO (jinho.ko@postech.ac.kr)
DISTRIBUTION OR COMMERCIAL USE ONLY AVAILABLE UPON APPROVAL OF THE AUTHOR.
"""

""" load libraries """
import socket
import os
import sys
import time
import enum
import getpass
import random
import traceback
import warnings

""" configuration """
warnings.filterwarnings("ignore")
ADMIN_ID = 'admin'
SOCKET_TIMEOUT = 10

""" global variables """
CONN = None
CONN_BUFFER_SIZE = 10240000 # 10MB
DATA_BLOCK_SIZE = 2048000 # 2MB
SFTP_DISCRIMINATOR_TOKEN = b'dg'

""" MSGTYPE ; Exactly opposite with server msg """
@enum.unique
class MsgToRecv(enum.Enum):

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
class MsgToSend(enum.Enum):

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


class Client():

    def __init__(self):
        self.conn = None
        self.ip = None
        self.port = None
        self.uid = None
        self.pwd = os.path.abspath(os.getcwd())

        self.conn_buffer_size = CONN_BUFFER_SIZE
        self.token = SFTP_DISCRIMINATOR_TOKEN

    def recv(self):

        recv_binary = b''
        msg_len = -1
        firstMsgArrived = False
        stop_raised = False

        while True:
            try:
                recved = self.conn.recv(self.conn_buffer_size)
                recv_binary = recv_binary + recved
                if recv_binary[:2] != b'dg':
                    return (MsgToRecv.GET_FAILURE, b'')
            except KeyboardInterrupt:
                stop_raised = True
                flush = b'1'
                while flush:
                    flush = self.conn.recv(self.conn_buffer_size)
                break
            else:
                if not firstMsgArrived:
                    msg_len = int(recv_binary[2:10])
                    firstMsgArrived = True
                if len(recv_binary) == msg_len :
                    break

        if stop_raised:
            raise KeyboardInterrupt

        recv_msgtype = MsgToRecv(int(recv_binary[10:12]))
        recv_data_bin = recv_binary[12:]

        return recv_msgtype, recv_data_bin  # (MsgToRecv, bytes)

    def send(self, send_msgtype, send_data=''):

        send_msgtype_bin = str(send_msgtype.value).zfill(2).encode()
        send_data_bin = send_data if type(send_data) is bytes \
                                    else send_data.encode()
        send_binary = send_msgtype_bin + send_data_bin
        send_len_bin = str(int(len(send_binary))+10).zfill(8).encode()
        send_binary = self.token + send_len_bin + send_binary

        try:
            self.conn.send(send_binary)
        except KeyboardInterrupt:
            self.conn.send(send_binary)
            raise KeyboardInterrupt

    def close(self, ever_connected):
        try:
            self.send(MsgToSend.CMD_EXIT)
        except:
            pass
        finally:
            self.conn.close()
            # exit
            if ever_connected:
                print('Connection closed.')
            sys.exit(0)
        return

    def connect(self, user, ip, port):
        # connect to port
        try:
            self.conn.connect( (ip, port) )
        except:
            print('ssh: Could not connect to {} {} {}'.format(self.uid, self.ip, self.port))
            return False, False
        # say hi
        try:
            self.send(MsgToSend.AUTH_HI, 'hi')
            (_, _) = self.recv()
        except Exception as e :
            print('ssh: connect to {} {} port {}: Connection refused'.format(self.uid, self.ip, self.port))
            return False, True
        return True, True

    def authenticate(self, uid):

        self.send(MsgToSend.AUTH_ID, uid)
        _, _ = self.recv()
        while True:
            pw = self.get_user_input("{}@{}'s password : ", (self.uid, self.ip), hide=True)
            self.send(MsgToSend.AUTH_PW, pw)
            m1t, m1 = self.recv()
            if m1t == MsgToRecv.AUTH_FAILURE :
                print('Permission denied, please try again.')
                continue
            elif m1t == MsgToRecv.AUTH_SUCCESS :
                print('Connected to {}@{}'.format(self.uid, self.ip))
                break

    def argparse(self, cmd_str):

        isValid = True
        result = [None, None, None] # cmd1, cmd2, cmd3

        # change '\ ' to '\n' temporarily
        cmd_str = cmd_str.replace('\ ', '\n')

        # split by ' ' (multiple spaces are also removed)
        cmd_list = cmd_str.split(' ')
        cmd_ls = []
        for elem in cmd_list:
            if '\n' in elem:
                cmd_ls.append(elem.replace('\n', '\ '))
            elif elem != '':
                cmd_ls.append(elem)
            else:
                pass

        # arg check
        if len(cmd_ls) == 0:
            isValid = False
        elif cmd_ls[0] == 'cd' and len(cmd_ls) is 2 :
            result[0], result[1] = cmd_ls[0], cmd_ls[1]
        elif cmd_ls[0] == 'lcd' and len(cmd_ls) is 2 :
            result[0], result[1] = cmd_ls[0], cmd_ls[1]
        elif cmd_ls[0] == 'pwd' and len(cmd_ls) >= 1 :
            result[0] = cmd_ls[0]
        elif cmd_ls[0] == 'lpwd' and len(cmd_ls) >= 1 :
            result[0] = cmd_ls[0]
        elif cmd_ls[0] == 'ls' and len(cmd_ls) in (1, 2):
            result[0] = cmd_ls[0]
            if len(cmd_ls) == 2 :
                result[1] = cmd_ls[1]
        elif cmd_ls[0] == 'lls' and len(cmd_ls) in (1, 2):
            result[0] = cmd_ls[0]
            if len(cmd_ls) == 2 :
                result[1] = cmd_ls[1]
        elif cmd_ls[0] == 'get' and len(cmd_ls) in (2, 3):
            result[0] = cmd_ls[0]
            result[1] = cmd_ls[1]
            if len(cmd_ls) == 3 :
                result[2] = cmd_ls[2]
        elif cmd_ls[0] == 'put' and len(cmd_ls) in (2, 3):
            result[0] = cmd_ls[0]
            result[1] = cmd_ls[1]
            if len(cmd_ls) == 3 :
                result[2] = cmd_ls[2]
        elif cmd_ls[0] == 'exit' and len(cmd_ls) >= 1 :
            result[0] = cmd_ls[0]
        else:
            isValid = False

        return isValid, result

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

    def stats(self, recent_time, uptime, upspeed, data_size): # (ms, ms, B/s, B)

        curr_mil = int(round(time.time() * 1000))
        if curr_mil - recent_time <= 1000: # less than 1sec
            return (False, None, None)

        delta_time_s = (curr_mil - recent_time) / 1000.0
        tot_size_B = (upspeed * uptime)/1000.0 + data_size
        tot_time_s = (uptime + delta_time_s)/1000.0
        Bps = tot_size_B / tot_time_s
        return (True, delta_time_s/1000.0, Bps)

    def disp_mpbs(self, filename, uptime_ms, upbyte):

        time_s = int(uptime_ms*1000.0)
        upbyte_MB = round(upbyte/1000000.0 * 2.0, 2)

        size_str = '{}   {}s   {}MB'.format(filename, time_s, upbyte_MB)
        sys.stdout.write('%s\r' % size_str)
        sys.stdout.flush()

    def disp_flush(self):
        print('')
        sys.stdout.flush()

    def main_func_iter(self):
        cmd_str = self.get_user_input('sftp> ')
        valid_cmd, parsed = self.argparse(cmd_str)
        if not valid_cmd:
            print('Invalid command.')
            return

        cmd1, cmd2, cmd3 = parsed
        if cmd1 == 'cd':
            self.send(MsgToSend.CMD_CD, cmd2)
            m1t, m1 = self.recv()
            if m1t == MsgToRecv.CD_PATHERR:
                print('''Couldn't stat remote file: No such file or directory''')
                return
            elif m1t == MsgToRecv.CD_PROCEED:
                self.send(MsgToSend.CD_PROCEED)
                m2t, m2 = self.recv()
                if m2t != MsgToRecv.CD_SUCCESS:
                    print('Error Occured')
            return

        elif cmd1 == 'lcd':
            if not self.existance_check(cmd2, True):
                print('''Couldn't change local directory to "{}": No such file or directory'''.format(cmd2))
                return
            self.pwd = self.get_absolute_path(cmd2)
        elif cmd1 == 'pwd':
            self.send(MsgToSend.CMD_PWD)
            m1t, m1 = self.recv()
            print('Remote working directory: {}'.format(m1.decode()))
        elif cmd1 == 'lpwd':
            print('Local working directory: {}'.format(self.pwd))
        elif cmd1 == 'ls':
            cmd2 = '' if cmd2 is None else cmd2
            self.send(MsgToSend.CMD_LS, cmd2)
            m1t, m1 = self.recv()
            if m1t == MsgToRecv.LS_PATHERR:
                print('''Couldn't stat remote file: No such file or directory''')
                return
            elif m1t == MsgToRecv.LS_PROCEED:
                self.send(MsgToSend.LS_PROCCED)
                recv_data = b''
                while True:
                    m2t, m2 = self.recv()
                    if m2t == MsgToRecv.LS_FAILURE:
                        print('Error Occured??')
                        return
                    self.send(MsgToSend.LS_PROCCED)
                    if len(m2) == 0:
                        break
                    recv_data = recv_data + m2
                # check success or failure
                m3t, m3 = self.recv()
                if m3t == MsgToRecv.LS_SUCCESS:
                    print(recv_data.decode(), end='')
                else:
                    print('Error Occured')
            return
        elif cmd1 == 'lls':
            if not cmd2:
                os.system('ls ' + self.pwd)
            else:
                os.system('ls ' + cmd2)
        elif cmd1 == 'get':
            if cmd3:
                if not self.existance_check(cmd3, True):  # isDir
                    print('''Couldn't get to local directory "{}": No such file or directory'''.format(cmd3))

            self.send(MsgToSend.CMD_GET, cmd2)
            m1t, m1 = self.recv()
            foreign_path_name = m1.decode()
            if m1t == MsgToRecv.GET_PATHERR:
                print('''File "{}" not found.'''.format(foreign_path_name))
                return

            get_path = (self.absolutify(cmd3) if cmd3 else self.pwd)
            get_path = get_path + ('' if get_path[-1] == '/' else '/')
            file_name = cmd2.split('/')[-1]
            tmpfile_name = str(random.randint(10000000, 99999999))  # 8-digit number
            tmpfile_name = '.' + tmpfile_name

            recv_success = False
            turn_to_send = True
            user_cancellation = False

            uptime = 0
            upspeed = 0.0
            upbyte = 0
            recent_time = int(round(time.time() * 1000))

            try:
                with open(get_path + tmpfile_name, 'wb') as f:
                    self.send(MsgToSend.GET_PROCEED)  # be ready!
                    print('''Fetching {} to {}'''.format(foreign_path_name, get_path + file_name))
                    while True:
                        turn_to_send = not turn_to_send
                        m2t, m2 = self.recv()
                        # stats
                        val, dta, spd = self.stats(recent_time, uptime, upspeed, len(m2))
                        if val:
                            uptime = uptime + dta
                            recent_time = int(round(time.time() * 1000))
                            upspeed = spd
                            upbyte = upbyte + len(m2)
                            self.disp_mpbs(foreign_path_name, uptime, upbyte)
                        # end stats
                        turn_to_send = not turn_to_send
                        if m2t == MsgToRecv.GET_FAILURE:
                            break
                        if not m2:  # empty
                            recv_success = True
                            break
                        f.write(m2)
                        self.send(MsgToSend.GET_PROCEED)
            except KeyboardInterrupt:
                user_cancellation = True
                #traceback.print_exc()
                self.send(MsgToSend.GET_STOP)
                _, _ = self.recv()  # recv fail
            except Exception as e:
                #traceback.print_exc()
                self.send(MsgToSend.GET_STOP)
                _, _ = self.recv()  # recv fail

            self.disp_flush()

            if recv_success:
                os.system('mv {} {}'.format(get_path + tmpfile_name, get_path + file_name))
                return
            os.system('rm {}'.format(get_path + tmpfile_name))
            if not user_cancellation:
                print('Error Occured')

        elif cmd1 == 'put':

            if not self.existance_check(cmd2, False):  # isFile?
                print('''Couldn't get to local directory "{}": No such file'''.format(cmd2))
                return

            target_path = cmd3 if cmd3 else ''
            self.send(MsgToSend.CMD_PUT, target_path)
            m1t, m1 = self.recv()
            if m1t == MsgToRecv.PUT_PATHERR:
                print('''Directory "{}" not found.'''.format(target_path))
                return

            put_filepath = self.absolutify(cmd2)
            put_filename = cmd2.split('/')[-1]
            self.send(MsgToSend.PUT_PROCEED, put_filename)

            uptime = 0
            upspeed = 0.0
            upbyte = 0
            recent_time = int(round(time.time() * 1000))

            user_cancellation = False
            send_success = False
            print('''Uploading {} to {}'''.format(put_filepath + put_filename, m1.decode()))
            try:
                with open(put_filepath, 'rb') as f:
                    while True:
                        m2t, m2 = self.recv()
                        if m2t == MsgToRecv.PUT_FAILURE:
                            break
                        data_frag_bin = f.read(DATA_BLOCK_SIZE)
                        self.send(MsgToSend.PUT_DATA, data_frag_bin)
                        # stats
                        val, dta, spd = self.stats(recent_time, uptime, upspeed, len(data_frag_bin))
                        if val:
                            uptime = uptime + dta
                            recent_time = int(round(time.time() * 1000))
                            upspeed = spd
                            upbyte = upbyte + len(data_frag_bin)
                            self.disp_mpbs(put_filepath, uptime, upbyte)
                        # end stats
                        if not data_frag_bin:
                            send_success = True
                            break
            except KeyboardInterrupt:
                user_cancellation = True
                #traceback.print_exc()
                self.send(MsgToSend.PUT_STOP)
                self.send(MsgToSend.PUT_STOP)
                _, _ = self.recv()
            except Exception as e:
                #traceback.print_exc()
                self.send(MsgToSend.PUT_STOP)
                _, _ = self.recv()

            self.disp_flush()

            if not user_cancellation and not send_success:
                print('Error Occured')

        elif cmd1 == 'exit':
            self.close(True)

    def main_func(self):
        while True:
            try:
                self.main_func_iter()
            except KeyboardInterrupt:
                continue

    def get_user_input(self, display, disp_params = (), hide=False):
        result = ''
        if hide:
            while True:
                try:
                    result = getpass.getpass(display.format(*disp_params))
                except KeyboardInterrupt:
                    print('')
                    self.close(True)
                except Exception as e:
                    print('')
                    continue
                else:
                    break
        else:
            while True:
                try:
                    result = input(display.format(*disp_params))
                except KeyboardInterrupt:
                    print('')
                    continue
                else:
                    break

        return result

    """ main """
    def run(self, uid, ip, port):

        try:
            if uid == '':
                uid = ADMIN_ID
            # open socket
            self.ip, self.port, self.uid = ip, port, uid
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect
            con_success, conned = self.connect(uid, ip, port)
            if not con_success:
                self.close(conned)

            # authenticate
            self.authenticate(uid)

            # main_func
            self.main_func()

        except KeyboardInterrupt as e:
            traceback.print_exc()
            self.close(True)

        self.close(True)

if __name__ == "__main__":


    tcpPORT = 2022
    tcpIP = None
    argparse_success = True
    uID = ''

    try:
        if len(sys.argv) >= 3 : # PORT option
            tcpPORT = int(sys.argv[2])

        if '@' in sys.argv[1]:
            uID = sys.argv[1].split('@')[0]
            tcpIP = sys.argv[1].split('@')[1]
        else:
            tcpIP = sys.argv[1]

    except:
        argparse_success = False

    # Argparse OK
    if argparse_success:
        cli = Client()
        cli.run(uID, tcpIP, tcpPORT)
    else:
        print('sftp: illegal argument(s)')