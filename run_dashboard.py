import http.server, threading, sys, os, webbrowser

PORT = 8080
os.chdir(r"C:\Users\fung2\.mavis\agents\mavis\workspace\project_x")

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

server = http.server.HTTPServer(('', PORT), Handler)
print(f"Dashboard running at http://localhost:{PORT}")
print("Opening browser...")
webbrowser.open(f"http://localhost:{PORT}")
server.serve_forever()
