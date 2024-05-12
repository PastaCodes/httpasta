import sys
import socket
import threading
import os.path

DEFAULT_SERVER_PORT = 8080


def respond(client_connection, status_code, reason_phrase, body):
    client_connection.send(f'HTTP/1.1 {status_code} {reason_phrase}\r\n\r\n{body}\r\n'.encode())


REASON_PHRASES = {
    400: 'Bad Request',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    505: 'HTTP Version Not Supported',
}
ERROR_BODY = '<html><head><title>{0} {1}</title></head><body><h1>{0} {1}</h1></body></html>'


def error(client_connection, status_code, request_line, client_id):
    reason_phrase = REASON_PHRASES[status_code]
    print(f'Responding with error {status_code} ({reason_phrase}) to request {request_line!r} from {client_id}.')
    respond(client_connection, status_code, reason_phrase, ERROR_BODY.format(status_code, reason_phrase))


def success(client_connection, content, file_name, request_line, client_id):
    print(f'Responding with file {file_name!r} to request {request_line!r} from {client_id}.')
    respond(client_connection, 200, 'OK', content)


POSTFIXES = ['', '/index.html']


def handle_request(client_connection, client_id):
    with client_connection:
        request = client_connection.recv(1024).decode()
        request_lines = request.splitlines()
        request_line = request_lines[0]
        match request_line.split():
            case ['GET', url, 'HTTP/1.1']:
                if url.startswith('/'):
                    path = url[1:].split('?')[0]
                    path = os.path.normpath(path)
                    if not path.startswith('..'):
                        for postfix in POSTFIXES:
                            try:
                                with open(path + postfix, 'r') as file:
                                    content = file.read()
                                success(client_connection, content, file.name, request_line, client_id)
                                break
                            except FileNotFoundError:
                                continue
                        else:
                            error(client_connection, 404, request_line, client_id)  # Not Found
                    else:
                        error(client_connection, 403, request_line, client_id)  # Forbidden
                else:
                    error(client_connection, 400, request_line, client_id)  # Bad Request
            case [_, _, b'HTTP/1.1']:
                error(client_connection, 405, request_line, client_id)  # Method Not Allowed
            case [_, _, _]:
                error(client_connection, 505, request_line, client_id)  # HTTP Version Not Supported
            case _:
                error(client_connection, 400, request_line, client_id)  # Bad Request


def main():
    if len(sys.argv) == 1:
        server_port = DEFAULT_SERVER_PORT
    elif len(sys.argv) == 2 and sys.argv[1].isnumeric():
        server_port = int(sys.argv[1])
    else:
        print('Usage: httpasta.py [port]', file=sys.stderr)
        exit(1)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with server_socket:
        server_socket.bind(('localhost', server_port))
        server_socket.listen(1)

        print(f"Listening on port {server_port}.")
        while True:
            client_connection, client_address = server_socket.accept()
            client_id = f'{client_address[0]}:{client_address[1]}'
            print(f'Connected to {client_id}.')
            handler_thread = threading.Thread(target=handle_request, args=(client_connection, client_id))
            handler_thread.daemon = True
            handler_thread.start()


if __name__ == '__main__':
    main()