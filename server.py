import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

print("🚀 Starting MFF Bot Server", file=sys.stderr)
print(f"PORT: {os.getenv('PORT', 10000)}", file=sys.stderr)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """
        <html>
        <head><title>MFF Bot</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>✅ MFF Bot Server is Running!</h1>
            <p>Telegram bot should respond to /start</p>
            <p>Check logs for more information</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), format%args))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"✅ Server started on port {port}", file=sys.stderr)
    server.serve_forever()
