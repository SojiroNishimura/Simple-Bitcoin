from concurrent.futures import ThreadPoolExecutor
import socket
import os

def __handle_message(args_tuple):
    conn, addr, data_sum = args_tuple
    while True:
        data = conn.recv(1024)
        data_sum = data_sum + data.decode('utf-8')

        if not data:
            break

    if data_sum != '':
        print(data_sum)


def __get_myip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    return s.getsockname()[0]

def main():
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    myhost = __get_myip()
    print('my ip address is now ...', myhost)
    my_socket.bind((myhost, 8080))
    my_socket.listen(1)

    while True:
        print('Waiting for the connection ...')
        conn, addr = my_socket.accept()
        print('Connedted by ...', addr)
        data_sum = ''
        executor.submit(__handle_message, (conn, addr, data_sum))


if __name__ == '__main__':
    main()
