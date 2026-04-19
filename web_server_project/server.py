import socket
import os
import time
import threading
from datetime import datetime

# Server settings
HOST = '127.0.0.1'
PORT = 8080
BASE_DIR = 'www'
LOG_FILE = 'log.txt'

def get_content_type(filepath):
    # This function returns the MIME type based on the file extension.
    # The MIME type tells the browser what kind of file it is receiving.
    if filepath.endswith('.html'):
        return 'text/html'
    elif filepath.endswith('.txt'):
        return 'text/plain'
    elif filepath.endswith('.jpg') or filepath.endswith('.jpeg'):
        return 'image/jpeg'
    elif filepath.endswith('.png'):
        return 'image/png'
    else:
        return 'text/html'

def write_log(client_ip, request_line, status_code):
    # This function writes a log entry to log.txt.
    # Each entry contains the time, client IP, request line, and status code.
    with open(LOG_FILE, 'a') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp} | {client_ip} | {request_line} | {status_code}\n")
    print(f"[LOG] {timestamp} | {client_ip} | {request_line} | {status_code}")

def parse_headers(request_data):
    # This function turns the raw HTTP headers into a dictionary.
    # This makes it easy to look up specific header values later.
    headers = {}
    lines = request_data.split('\r\n')
    for line in lines[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key.lower()] = value
    return headers

def send_response(client_socket, status_code, content_type='text/html', body=None, extra_headers=None, keep_alive=False):
    # This function builds and sends an HTTP response.
    # It adds the status line, headers, and body if there is one.
    
    # This dictionary maps status codes to their text descriptions.
    status_text = {
        200: 'OK', 304: 'Not Modified', 400: 'Bad Request',
        403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed', 500: 'Internal Server Error'
    }
    # Build the status line.
    response = f'HTTP/1.1 {status_code} {status_text[status_code]}\r\n'
    
    # Add Content-Type and Content-Length headers for responses that are not 304.
    if status_code != 304:
        response += f'Content-Type: {content_type}\r\n'
       # If there is a body, use its length
        if body is not None:
            response += f'Content-Length: {len(body)}\r\n'
        # For HEAD requests, body is None, so get the length from extra_headers.
        elif extra_headers and 'Content-Length' in extra_headers:
            response += f'Content-Length: {extra_headers["Content-Length"]}\r\n'
    
    # Add the Connection header based on keep_alive.
    if keep_alive:
        response += 'Connection: keep-alive\r\n'
    else:
        response += 'Connection: close\r\n'
    
    # Add any extra headers provided by the caller.
    if extra_headers:
        for k, v in extra_headers.items():
            if k != 'Content-Length':  
                response += f'{k}: {v}\r\n'
    response += '\r\n'
    
    # Send the status line and headers
    client_socket.send(response.encode())
     # Send the body if there is one and the status is not 304.
    if body and status_code != 304:
        client_socket.send(body if isinstance(body, bytes) else body.encode())

def handle_client(client_socket, client_address):
    # This function handles a single client connection.
    # It runs in its own thread so multiple clients can be served at the same time.
    try:
        # Set a timeout to avoid waiting forever for a slow client.
        client_socket.settimeout(5)
        
        # This loop allows keep-alive connections to handle multiple requests.
        while True:
            try:
                # Receive the request data from the client.
                request_data = client_socket.recv(4096).decode('utf-8', errors='ignore')
                if not request_data:
                    break
            except socket.timeout:
                # If no data arrives within the timeout, close the connection.
                break
            
            request_line = request_data.split('\r\n')[0]
            parts = request_line.split(' ')
            
            # If the request line does not have at least two parts, it is malformed.
            if len(parts) < 2:
                send_response(client_socket, 400)
                write_log(client_address[0], request_line, '400')
                break
            
            method = parts[0]
            filepath = parts[1]
            
            print(f"[REQUEST] {method} {filepath} from {client_address[0]}")
           
            # Check for directory traversal attacks like "..".
            if '..' in request_line:
                send_response(client_socket, 403)
                write_log(client_address[0], request_line, '403')
                break
            
            # Only GET and HEAD methods are supported.
            if method not in ['GET', 'HEAD']:
                send_response(client_socket, 405)
                write_log(client_address[0], request_line, '405')
                break
            
            # Parse the headers.
            headers = parse_headers(request_data)
            connection_header = headers.get('connection', '').lower()
            keep_alive = (connection_header == 'keep-alive')
            
            # If the client requests the root path, serve index.html.
            if filepath == '/':
                filepath = '/index.html'
            
            # If the path ends with a slash, the client is trying to list a directory.
            if filepath.endswith('/'):
                send_response(client_socket, 403, keep_alive=keep_alive)
                write_log(client_address[0], request_line, '403')
                break
            
            # Build the full file system path.
            full_path = BASE_DIR + filepath
            
            # If the path points to a directory, do not allow directory listing.
            if os.path.isdir(full_path):
                send_response(client_socket, 403, keep_alive=keep_alive)
                write_log(client_address[0], request_line, '403')
                break
            
            # If the file does not exist, return 404 Not Found.
            if not os.path.exists(full_path):
                send_response(client_socket, 404, keep_alive=keep_alive)
                write_log(client_address[0], request_line, '404')
                break
            
            # Read the file content.
            with open(full_path, 'rb') as f:
                content = f.read()
            
            # Get the file type and last modification time.
            content_type = get_content_type(full_path)
            mtime = os.path.getmtime(full_path)
            last_modified = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mtime))
            
            # Check for conditional request using If-Modified-Since.
            if_modified_since = headers.get('if-modified-since', '')
            should_return_304 = False
            
            if if_modified_since:
                # If the file has not changed, return 304 Not Modified.
                if if_modified_since == last_modified:
                    should_return_304 = True
                    print(f"[INFO] 304 Not Modified: {filepath}")
            
            extra_headers = {'Last-Modified': last_modified}
            
            # For HEAD requests, add Content-Length to extra_headers.
            if method == 'HEAD':
                extra_headers['Content-Length'] = str(len(content))
            
            # If the file has not changed, send 304 and skip sending the body.
            if should_return_304:
                send_response(client_socket, 304, extra_headers=extra_headers, keep_alive=keep_alive)
                write_log(client_address[0], request_line, '304')
                if not keep_alive:
                    break
                continue # Go back to wait for the next request.
            
            # For GET requests, send the full response with body.
            if method == 'GET':
                send_response(client_socket, 200, content_type, content, extra_headers, keep_alive)
            else:  # For HEAD requests, send only headers.
                send_response(client_socket, 200, content_type, None, extra_headers, keep_alive)
            
            write_log(client_address[0], request_line, '200')
            
            # If the client does not want keep-alive, close the connection.
            if not keep_alive:
                break
            
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        client_socket.close()

def main():
    # This is the main function that starts the server.
    
    # Create the www directory if it does not exist.
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    
    # Create a default index.html file if it does not exist.
    index_path = os.path.join(BASE_DIR, 'index.html')
    if not os.path.exists(index_path):
        with open(index_path, 'w') as f:
            f.write('<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello from Web Server!</h1></body></html>')
    
    # Create the server socket.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(10)
    
    print(f"[START] Server at http://{HOST}:{PORT}")
    print(f"[INFO] Features: GET, HEAD, 200/304/400/403/404/405/500, keep-alive")
    
    # Main loop: accept connections and start a new thread for each client.
    while True:
        try:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client, addr))
            t.start()
        except KeyboardInterrupt:
            print("\n[SHUTDOWN]")
            break

if __name__ == '__main__':
    main()