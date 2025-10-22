#!/usr/bin/env python3
"""
Simple webhook test server for OpenCVE notifications.

This server receives webhook POST requests from OpenCVE and displays
the CVE alerts in a formatted, easy-to-read way.

Usage:
    python3 webhook_test_server.py [--port PORT] [--host HOST]

Example:
    python3 webhook_test_server.py --port 8888

Then configure your OpenCVE webhook to: http://localhost:8888/webhook
"""

import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


class Color:
    """ANSI color codes for terminal output"""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def get_severity_color(score):
    """Get color based on CVSS score"""
    if score is None:
        return Color.YELLOW
    elif score >= 9.0:
        return Color.RED
    elif score >= 7.0:
        return Color.RED
    elif score >= 4.0:
        return Color.YELLOW
    else:
        return Color.GREEN


def format_cve_alert(payload):
    """Format the webhook payload into readable output"""
    lines = []

    # Header
    lines.append("\n" + "=" * 80)
    lines.append(
        f"{Color.BOLD}{Color.CYAN}📢 NEW OPENCVE WEBHOOK NOTIFICATION{Color.END}"
    )
    lines.append("=" * 80)

    # Metadata
    lines.append(
        f"\n{Color.BOLD}Organization:{Color.END} {payload.get('organization', 'N/A')}"
    )
    lines.append(f"{Color.BOLD}Project:{Color.END} {payload.get('project', 'N/A')}")
    lines.append(
        f"{Color.BOLD}Notification:{Color.END} {payload.get('notification', 'N/A')}"
    )
    lines.append(f"{Color.BOLD}Title:{Color.END} {payload.get('title', 'N/A')}")

    # Period
    period = payload.get("period", {})
    lines.append(f"\n{Color.BOLD}Period:{Color.END}")
    lines.append(f"  Start: {period.get('start', 'N/A')}")
    lines.append(f"  End:   {period.get('end', 'N/A')}")

    # Subscriptions
    matched = payload.get("matched_subscriptions", {})
    lines.append(
        f"\n{Color.BOLD}Matched Subscriptions:{Color.END} {', '.join(matched.get('human', []))}"
    )

    # Changes
    changes = payload.get("changes", [])
    lines.append(f"\n{Color.BOLD}CVE Changes: {len(changes)}{Color.END}")
    lines.append("-" * 80)

    for idx, change in enumerate(changes, 1):
        cve = change.get("cve", {})
        cve_id = cve.get("cve_id", "UNKNOWN")
        description = cve.get("description", "No description available")
        cvss31 = cve.get("cvss31")
        subscriptions = cve.get("subscriptions", {}).get("human", [])
        events = change.get("events", [])

        # CVE Header
        severity_color = get_severity_color(cvss31)
        cvss_display = f"{cvss31:.1f}" if cvss31 is not None else "N/A"

        lines.append(
            f"\n{Color.BOLD}{idx}. {severity_color}{cve_id}{Color.END} "
            f"{Color.BOLD}[CVSS: {severity_color}{cvss_display}{Color.END}{Color.BOLD}]{Color.END}"
        )

        # Description (truncate if too long)
        desc_preview = (
            description[:200] + "..." if len(description) > 200 else description
        )
        lines.append(f"   {Color.BLUE}Description:{Color.END} {desc_preview}")

        # Subscriptions
        if subscriptions:
            lines.append(
                f"   {Color.BLUE}Subscriptions:{Color.END} {', '.join(subscriptions)}"
            )

        # Events
        if events:
            event_types = [e.get("type", "unknown") for e in events]
            lines.append(f"   {Color.BLUE}Events:{Color.END} {', '.join(event_types)}")

            # Show event details if available
            for event in events:
                event_type = event.get("type", "unknown")
                event_data = event.get("data", {})
                if event_data:
                    lines.append(
                        f"      • {event_type}: {json.dumps(event_data, indent=8)[:100]}..."
                    )

    lines.append("\n" + "=" * 80 + "\n")

    return "\n".join(lines)


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhook notifications"""

    received_count = 0

    def log_message(self, format, *args):
        """Override to customize logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")

    def do_GET(self):
        """Handle GET requests (for health checks)"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "status": "healthy",
                "server": "OpenCVE Webhook Test Server",
                "received_webhooks": WebhookHandler.received_count,
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = f"""
            <html>
            <head><title>OpenCVE Webhook Test Server</title></head>
            <body>
                <h1>🔗 OpenCVE Webhook Test Server</h1>
                <p>Server is running and ready to receive webhooks!</p>
                <h2>Status</h2>
                <ul>
                    <li>Webhooks received: <strong>{WebhookHandler.received_count}</strong></li>
                    <li>Webhook endpoint: <code>POST /webhook</code></li>
                    <li>Health check: <code>GET /health</code></li>
                </ul>
                <h2>Configuration</h2>
                <p>Configure your OpenCVE webhook with:</p>
                <pre>URL: http://{self.server.server_name}:{self.server.server_port}/webhook</pre>
                <p>Check the terminal/console for detailed webhook output.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

    def do_POST(self):
        """Handle POST requests (webhook notifications)"""
        parsed_path = urlparse(self.path)

        if parsed_path.path != "/webhook":
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            return

        # Check authentication header if provided
        auth_header = self.headers.get("Authorization")
        if auth_header:
            print(f"{Color.CYAN}Auth Header:{Color.END} {auth_header}")

        # Read the request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            # Parse JSON payload
            payload = json.loads(body.decode("utf-8"))

            # Increment counter
            WebhookHandler.received_count += 1

            # Display formatted output
            print(format_cve_alert(payload))

            # Save to file for later inspection
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"webhook_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump(payload, f, indent=2)
            print(f"{Color.GREEN}✅ Webhook saved to: {filename}{Color.END}\n")

            # Send success response
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "status": "received",
                "message": "Webhook processed successfully",
                "cve_count": len(payload.get("changes", [])),
                "received_count": WebhookHandler.received_count,
            }
            self.wfile.write(json.dumps(response).encode())

        except json.JSONDecodeError as e:
            print(f"{Color.RED}❌ Error: Invalid JSON{Color.END}")
            print(f"   {str(e)}")
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())

        except Exception as e:
            print(f"{Color.RED}❌ Error processing webhook:{Color.END}")
            print(f"   {str(e)}")
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())


def run_server(host="0.0.0.0", port=8888):
    """Start the webhook test server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, WebhookHandler)

    print(f"\n{Color.BOLD}{Color.CYAN}{'=' * 80}{Color.END}")
    print(f"{Color.BOLD}{Color.GREEN}🚀 OpenCVE Webhook Test Server Started{Color.END}")
    print(f"{Color.BOLD}{Color.CYAN}{'=' * 80}{Color.END}\n")
    print(f"{Color.BOLD}Server Address:{Color.END} http://{host}:{port}")
    print(f"{Color.BOLD}Webhook URL:{Color.END}    http://{host}:{port}/webhook")
    print(f"{Color.BOLD}Health Check:{Color.END}   http://{host}:{port}/health")
    print(
        f"\n{Color.YELLOW}📝 Configure your OpenCVE webhook with the URL above{Color.END}"
    )
    print(
        f"{Color.YELLOW}💾 Webhooks will be saved as JSON files in the current directory{Color.END}"
    )
    print(f"\n{Color.CYAN}Press Ctrl+C to stop the server{Color.END}\n")
    print(f"{Color.BOLD}{Color.CYAN}{'=' * 80}{Color.END}\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\n{Color.YELLOW}🛑 Server stopped by user{Color.END}")
        print(
            f"{Color.GREEN}Total webhooks received: {WebhookHandler.received_count}{Color.END}\n"
        )
        httpd.server_close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="OpenCVE Webhook Test Server - Receive and display webhook notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server on default port 8888
  python3 webhook_test_server.py

  # Start server on custom port
  python3 webhook_test_server.py --port 9000

  # Start server on specific host and port
  python3 webhook_test_server.py --host 192.168.1.100 --port 8080

  # Allow connections from any IP (useful for Docker)
  python3 webhook_test_server.py --host 0.0.0.0

Then configure your OpenCVE webhook to point to this server.
        """,
    )

    parser.add_argument(
        "--port", "-p", type=int, default=8888, help="Port to listen on (default: 8888)"
    )

    parser.add_argument(
        "--host",
        "-H",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0 - all interfaces)",
    )

    args = parser.parse_args()

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
