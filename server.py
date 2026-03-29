import base64
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler

import tasks
from Config import max_half_fields


class MainHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.is_time_valid():
            self.send_error(1001, "time error", 'time error. Please visit between 7:00 and 00:00.')
            return
        if self.path == "/booking":
            self.do_GET_booking()
        elif self.path == "/login":
            self.do_GET_login()
        elif self.path == "/venue":
            self.do_GET_venue()
        else:
            self.redirect("/booking")

    def do_POST(self):
        if not self.is_time_valid():
            return
        if self.path == "/login":
            self.do_POST_login()
        elif self.path == "/venue":
            self.do_POST_venue()

    def do_GET_login(self):
        self.serve_html('page/loginPage.html')

    def do_POST_login(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        try:
            username = base64.b64decode(data.get('username', '')).decode('utf-8')
            password = base64.b64decode(data.get('password', '')).decode('utf-8')
        except Exception as e:
            self.send_error(1064, f"Error: {e}")
            return

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        response = {}
        if self.authenticate(username, password):
            response['success'] = True
            cookie = base64.b64encode(f"is_login".encode('utf-8')).decode('utf-8')
            self.send_header('Set-Cookie', f"user={cookie}; Max-Age=600000; Path=/")  # 604800
        else:
            response['success'] = False
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def do_GET_booking(self):
        if not self.is_cookie_valid():
            self.redirect('/login')
        self.serve_html('page/bookingPage.html')

    def do_GET_venue(self):
        if not self.is_cookie_valid():
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        data = tasks.tasks_data
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_POST_venue(self):
        if not self.is_cookie_valid():
            return
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        response = {}
        if len(data) > max_half_fields:
            response['success'] = False
        else:
            tasks.tasks_data = data
            response['success'] = True
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def is_time_valid(self):
        return 7 <= datetime.now().hour < 24

    def is_cookie_valid(self):
        if base64.b64decode(self.get_cookie()).decode('utf-8') == "is_login":
            return True
        else:
            return False

    def get_cookie(self):
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookies = cookie_header.split(';')
            for cookie in cookies:
                key, value = cookie.strip().split('=', 1)
                if key == 'user':
                    return value
        return ""

    def authenticate(self, name, password):
        # 计算SHA256值
        # password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        # 密码：中文名的sha256哈希值
        login_list = {"mlx": "228c79210b6411fa4cb909711b8e18ac9c774099457e14a61e7559d25b1a6fba",
                      "wcc": "15fbc9175b9bcf8986f84b424c368d8ef8693f001df312f3377d466bfdbe8277",
                      "jht": "f6beca10c37fd1efec41f4ca681906876c5970c4e1b10781598354240aa2b20c",
                      "cyl": "92d7c3c146cf56b50d199f1975d635c059bdc273e12c768b25cd572e588cec5e",
                      "lsx": "d3427db35b9289007d024ab58811903e33863e0658c074b55cc5fb88e1e638ce",
                      "fyq": "2692e9fc3608db6fa26507399be6b75d9a8969165497b2362282e9d783f29b3d"
                      }
        if name in login_list and login_list[name] == password:
            return True
        else:
            return False

    def redirect(self, path):
        self.send_response(302)
        self.send_header('Content-type', 'text/html')
        self.send_header('Location', path)
        self.end_headers()

    def serve_html(self, file_name):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(file_name, 'r', encoding='utf-8') as file:
            self.wfile.write(file.read().encode('utf-8'))
