import socket

my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
my_socket.connect(('10.132.24.233', 8080))
my_text = "Hello! This is test message from my sample client!"
my_socket.sendall(my_text.encode('utf-8'))
