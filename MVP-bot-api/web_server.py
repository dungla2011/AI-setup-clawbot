"""
Simple web server để serve HTML + proxy API requests
Giải quyết CORS issues
"""
import os
from dotenv import load_dotenv
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path

# Load environment variables
load_dotenv()

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler với CORS support"""
    
    def end_headers(self):
        """Thêm CORS headers"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)"""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        """Override GET to inject API_URL into index.html"""
        if self.path == '/' or self.path == '/index.html':
            # Read index.html and inject API_URL from .env
            try:
                with open('index.html', 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Replace placeholder with actual API_URL
                api_url = os.getenv("API_URL", "http://localhost:8000")
                html_content = html_content.replace('{{API_URL}}', api_url)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                return
            except Exception as e:
                print(f"Error reading index.html: {e}")
        
        # Default behavior for other files
        super().do_GET()
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{self.client_address[0]}] {format % args}")

if __name__ == "__main__":
    # Get config from .env
    web_host = os.getenv("WEB_HOST", "0.0.0.0")
    web_port = int(os.getenv("WEB_PORT", "8080"))
    web_url = os.getenv("WEB_URL", "http://localhost:8080")
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    server_address = (web_host, web_port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    
    print(f"\n{'='*50}")
    print(f"💻 Bot MVP Web Server")
    print(f"{'='*50}")
    print(f"🌐 Web URL: {web_url}/index.html")
    print(f"🔌 Port: {web_port}")
    print(f"🤖 API URL: {api_url}")
    print(f"📁 Directory: {script_dir}")
    print(f"\n⚠️  Chắc chắn API server chạy trên {api_url}")
    print(f"{'='*50}")
    print(f"Nhấn Ctrl+C để tắt server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Server đã tắt")
