# Multi-threaded Web Server

## How to Run

1. Make sure you have Python 3.6 or higher installed.

2. Open a terminal in the project folder.

3. Run the server with the following command.

```bash
python server.py
```

4. Open a web browser and go to `http://127.0.0.1:8080/`

## Testing Commands

### Test 1: GET request with 200 OK

```bash
curl.exe http://127.0.0.1:8080/
```

### Test 2: GET request with 404 Not Found

```bash
curl.exe http://127.0.0.1:8080/notexist.html
```

### Test 3: GET request with 403 Forbidden

```bash
curl.exe http://127.0.0.1:8080/www/
```

### Test 4: HEAD command

```bash
curl.exe -I http://127.0.0.1:8080/
```

### Test 5: 304 Not Modified with conditional request

Step 1: Get the Last-Modified time from the server.

```bash
curl.exe -I http://127.0.0.1:8080/ 2>&1 | findstr "Last-Modified"
```

Step 2: Send a request with that exact timestamp in the If-Modified-Since header. Replace the timestamp with the one you got from Step 1.

```bash
curl.exe -v -H "If-Modified-Since: Sun, 19 Apr 2026 12:26:35 GMT" http://127.0.0.1:8080/ 2>&1 | findstr "HTTP/"
```

### Test 6: Non-persistent connection with Connection: close

```bash
curl.exe -v http://127.0.0.1:8080/ 2>&1 | findstr "Connection"
```

### Test 7: Persistent connection with Connection: keep-alive

```bash
curl.exe -v -H "Connection: keep-alive" http://127.0.0.1:8080/ 2>&1 | findstr "Connection"
```

### Test 8: Multi-threading test

```bash
(1..3) | ForEach-Object { Start-Job { curl.exe http://127.0.0.1:8080/ } } | Wait-Job | Receive-Job
```

### Test 9: Image file request

```bash
curl.exe -I http://127.0.0.1:8080/image.jpg
```

### Test 10: Check the log file

```bash
type log.txt
```

