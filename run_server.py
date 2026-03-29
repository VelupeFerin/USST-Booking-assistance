from http.server import HTTPServer
from threading import Thread

from tasks import perform_tasks
from server import MainHTTPRequestHandler

httpd = HTTPServer(('', 8192), MainHTTPRequestHandler)

Thread(target=perform_tasks).start()

print("Server started on port 8192...")
httpd.serve_forever()

