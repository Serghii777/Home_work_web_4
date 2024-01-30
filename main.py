import threading
import mimetypes
import pathlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import urllib.parse
import json
import os
from datetime import datetime

# Порти серверів
HTTP_PORT = 3000
SOCKET_PORT = 5000
# Шлях до папки для зберігання файлів
STORAGE_PATH = 'storage'
# Ім'я JSON файлу
JSON_FILE = 'data.json'


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        print(data)
        data_parse = urllib.parse.unquote_plus(data.decode())
        print(data_parse)
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        print(data_dict)
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

        # Отправка данных на обработку Socket серверу
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_client.sendto(json.dumps(data_dict).encode(), ('localhost', SOCKET_PORT))

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/contact':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())


class SocketServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind(('localhost', SOCKET_PORT))
            print(f"[*] UDP Server listening on port {SOCKET_PORT}")
            while True:
                data, _ = udp_socket.recvfrom(1024)
                data = data.decode('utf-8')
                try:
                    data_dict = json.loads(data)
                    print("[*] Received data:", data_dict)
                    self.save_to_json(data_dict)
                except json.JSONDecodeError as e:
                    print(f"[-] Error decoding JSON: {e}")

    def save_to_json(self, data):
        if not os.path.exists(STORAGE_PATH):
            os.makedirs(STORAGE_PATH)
        file_path = os.path.join(STORAGE_PATH, JSON_FILE)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        with open(file_path, 'r+') as json_file:
            existing_data = json.load(json_file)
            existing_data[current_time] = data
            json_file.seek(0)
            json.dump(existing_data, json_file, indent=2)
            print(f"[*] Data saved to {file_path}")


def run():
    # Запуск HTTP сервера
    http_server_address = ('', HTTP_PORT)
    http_server = HTTPServer(http_server_address, HttpHandler)
    print(f"[*] HTTP Server listening on port {HTTP_PORT}")

    # Запуск Socket сервера
    socket_server = SocketServer()
    socket_server.start()

    http_server.serve_forever()


if __name__ == '__main__':
    run()