# Webhook Notifications

OpenCVE supports webhook notifications to send CVE change alerts to your own applications and services via HTTP POST requests.

## Overview

When CVE changes match your project subscriptions, OpenCVE can send a JSON payload to your webhook endpoint. This allows you to:

- Integrate CVE alerts into your own systems
- Trigger automated workflows
- Send notifications to chat platforms (Slack, Discord, Teams, etc.)
- Store CVE data in your own database
- Create custom alerting logic

## Setting Up a Webhook

1. Navigate to your project in OpenCVE
2. Go to the **Notifications** tab
3. Click **Add Notification** and select **Webhook**
4. Configure the following settings:
   - **Name**: A unique name for this notification
   - **URL**: The HTTPS endpoint that will receive the webhook POST requests
   - **Headers** (optional): JSON object with custom HTTP headers (e.g., for authentication)
   - **Alert Settings**: Configure which CVE changes trigger notifications
   - **CVSS Score Filter**: Set minimum CVSS score threshold

### Example Configuration

**URL**: `https://your-app.com/api/webhooks/opencve`

**Headers** (for API key authentication):
```json
{
  "Authorization": "Bearer your-secret-token",
  "X-Custom-Header": "value"
}
```

## Webhook Payload Schema

Your endpoint will receive a POST request with `Content-Type: application/json` containing the following structure:

```json
{
  "organization": "string",
  "project": "string",
  "notification": "string",
  "subscriptions": {
    "raw": ["vendor1", "vendor2$PRODUCT$product1"],
    "human": ["Vendor1", "Product1"]
  },
  "matched_subscriptions": {
    "raw": ["vendor1"],
    "human": ["Vendor1"]
  },
  "title": "string",
  "period": {
    "start": "ISO8601 datetime",
    "end": "ISO8601 datetime"
  },
  "changes": [
    {
      "cve": {
        "cve_id": "string",
        "description": "string",
        "cvss31": number | null,
        "subscriptions": {
          "raw": ["vendor1"],
          "human": ["Vendor1"]
        }
      },
      "events": [
        {
          "type": "string",
          "data": {}
        }
      ]
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `organization` | string | Your organization name |
| `project` | string | The project name that triggered this notification |
| `notification` | string | The notification name |
| `subscriptions.raw` | array | All subscriptions in the project (raw format) |
| `subscriptions.human` | array | All subscriptions (human-readable) |
| `matched_subscriptions.raw` | array | Subscriptions that matched these changes |
| `matched_subscriptions.human` | array | Matched subscriptions (human-readable) |
| `title` | string | Summary title for this notification |
| `period.start` | string | Start of the reporting period (ISO8601) |
| `period.end` | string | End of the reporting period (ISO8601) |
| `changes` | array | Array of CVE changes |
| `changes[].cve.cve_id` | string | CVE identifier (e.g., "CVE-2024-1234") |
| `changes[].cve.description` | string | CVE description text |
| `changes[].cve.cvss31` | number/null | CVSS v3.1 score (0-10) or null |
| `changes[].cve.subscriptions` | object | Subscriptions matched by this CVE |
| `changes[].events` | array | Change events for this CVE |
| `changes[].events[].type` | string | Event type (e.g., "created", "metrics", "references") |
| `changes[].events[].data` | object | Event-specific data |

### Event Types

The `events[].type` field can be one of:

- `created` - New CVE was created
- `first_time` - Subscription first appeared in this CVE
- `metrics` - CVSS scores changed
- `cpes` - CPE (Common Platform Enumeration) changed
- `vendors` - Vendor or product information changed
- `weaknesses` - CWE (weakness) information changed
- `references` - References or advisories changed
- `description` - CVE description changed
- `title` - CVE title changed

## Example Payloads

### Single CVE Update

```json
{
  "organization": "acme-corp",
  "project": "web-applications",
  "notification": "critical-alerts",
  "subscriptions": {
    "raw": ["apache", "nginx", "microsoft$PRODUCT$windows_server"],
    "human": ["Apache", "Nginx", "Windows Server"]
  },
  "matched_subscriptions": {
    "raw": ["apache"],
    "human": ["Apache"]
  },
  "title": "1 change on Apache",
  "period": {
    "start": "2024-01-15T00:00:00+00:00",
    "end": "2024-01-15T23:59:59+00:00"
  },
  "changes": [
    {
      "cve": {
        "cve_id": "CVE-2024-1234",
        "description": "A critical vulnerability in Apache HTTP Server allows remote code execution...",
        "cvss31": 9.8,
        "subscriptions": {
          "raw": ["apache"],
          "human": ["Apache"]
        }
      },
      "events": [
        {
          "type": "metrics",
          "data": {
            "cvssV3_1": {
              "score": 9.8,
              "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
            }
          }
        }
      ]
    }
  ]
}
```

### Multiple CVE Changes

```json
{
  "organization": "acme-corp",
  "project": "infrastructure",
  "notification": "daily-digest",
  "subscriptions": {
    "raw": ["linux", "openssl"],
    "human": ["Linux", "Openssl"]
  },
  "matched_subscriptions": {
    "raw": ["linux", "openssl"],
    "human": ["Linux", "Openssl"]
  },
  "title": "3 changes on Linux, Openssl",
  "period": {
    "start": "2024-01-15T00:00:00+00:00",
    "end": "2024-01-15T23:59:59+00:00"
  },
  "changes": [
    {
      "cve": {
        "cve_id": "CVE-2024-1111",
        "description": "Linux kernel vulnerability...",
        "cvss31": 7.8,
        "subscriptions": {
          "raw": ["linux"],
          "human": ["Linux"]
        }
      },
      "events": [
        {
          "type": "created",
          "data": {}
        }
      ]
    },
    {
      "cve": {
        "cve_id": "CVE-2024-2222",
        "description": "OpenSSL buffer overflow...",
        "cvss31": 8.1,
        "subscriptions": {
          "raw": ["openssl"],
          "human": ["Openssl"]
        }
      },
      "events": [
        {
          "type": "references",
          "data": {
            "added": ["https://www.openssl.org/news/secadv/..."]
          }
        }
      ]
    },
    {
      "cve": {
        "cve_id": "CVE-2024-3333",
        "description": "Linux and OpenSSL interaction issue...",
        "cvss31": null,
        "subscriptions": {
          "raw": ["linux", "openssl"],
          "human": ["Linux", "Openssl"]
        }
      },
      "events": [
        {
          "type": "first_time",
          "data": {}
        }
      ]
    }
  ]
}
```

## Implementing a Webhook Endpoint

### Python (Flask)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/webhooks/opencve', methods=['POST'])
def opencve_webhook():
    # Verify authentication header
    api_key = request.headers.get('Authorization')
    if api_key != 'Bearer your-secret-token':
        return jsonify({'error': 'Unauthorized'}), 401

    # Parse the payload
    payload = request.json

    # Process CVE changes
    for change in payload['changes']:
        cve_id = change['cve']['cve_id']
        score = change['cve']['cvss31']
        description = change['cve']['description']

        print(f"New CVE: {cve_id} (CVSS: {score})")
        print(f"Description: {description}")

        # Your custom logic here
        # - Store in database
        # - Send to Slack/Teams
        # - Create tickets
        # - etc.

    return jsonify({'status': 'received'}), 200

if __name__ == '__main__':
    app.run(port=5000)
```

### Node.js (Express)

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/api/webhooks/opencve', (req, res) => {
    // Verify authentication
    const authHeader = req.headers.authorization;
    if (authHeader !== 'Bearer your-secret-token') {
        return res.status(401).json({ error: 'Unauthorized' });
    }

    const payload = req.body;

    // Process CVE changes
    payload.changes.forEach(change => {
        const { cve_id, cvss31, description } = change.cve;

        console.log(`New CVE: ${cve_id} (CVSS: ${cvss31})`);
        console.log(`Description: ${description}`);

        // Your custom logic here
    });

    res.json({ status: 'received' });
});

app.listen(5000, () => {
    console.log('Webhook server running on port 5000');
});
```

### Go

```go
package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
)

type WebhookPayload struct {
    Organization string `json:"organization"`
    Project      string `json:"project"`
    Title        string `json:"title"`
    Changes      []struct {
        CVE struct {
            CVEID       string   `json:"cve_id"`
            Description string   `json:"description"`
            CVSS31      *float64 `json:"cvss31"`
        } `json:"cve"`
        Events []map[string]interface{} `json:"events"`
    } `json:"changes"`
}

func opencveWebhook(w http.ResponseWriter, r *http.Request) {
    // Verify authentication
    if r.Header.Get("Authorization") != "Bearer your-secret-token" {
        http.Error(w, "Unauthorized", http.StatusUnauthorized)
        return
    }

    var payload WebhookPayload
    if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Process CVE changes
    for _, change := range payload.Changes {
        fmt.Printf("New CVE: %s (CVSS: %v)\n",
            change.CVE.CVEID, change.CVE.CVSS31)

        // Your custom logic here
    }

    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(map[string]string{"status": "received"})
}

func main() {
    http.HandleFunc("/api/webhooks/opencve", opencveWebhook)
    log.Fatal(http.Listen AndServe(":5000", nil))
}
```

## Testing Your Webhook

OpenCVE provides a built-in test feature:

1. Go to your webhook notification settings
2. Click the **Test Webhook** button
3. OpenCVE will send a sample payload to your endpoint
4. You'll see the HTTP status code and any error messages

The test payload uses fake CVE data (`CVE-2024-TEST`) so you can verify your endpoint works without processing real alerts.

## Best Practices

### Security

- **Use HTTPS**: Always use HTTPS endpoints to encrypt webhook data in transit
- **Verify Authentication**: Use headers to authenticate requests (API keys, Bearer tokens, etc.)
- **Validate Payloads**: Check that the payload structure matches the expected schema
- **Rate Limiting**: Implement rate limiting on your endpoint to prevent abuse
- **HMAC Signatures** (future): Consider implementing HMAC signature verification for added security

### Reliability

- **Return Quickly**: Your endpoint should respond within 10 seconds
- **Use Async Processing**: Queue webhook data for background processing
- **Idempotency**: Handle duplicate deliveries gracefully (same CVE may appear in multiple notifications)
- **Error Handling**: Return appropriate HTTP status codes (200 for success, 4xx/5xx for errors)
- **Logging**: Log all webhook deliveries for debugging

### Performance

- **Acknowledge Fast**: Return 200 status quickly, then process data asynchronously
- **Batch Processing**: Process multiple CVE changes efficiently
- **Database Indexing**: Index CVE IDs and timestamps if storing data

## Troubleshooting

### Webhooks Not Being Delivered

1. **Check Notification Status**: Ensure the notification is enabled
2. **Verify URL**: Confirm the webhook URL is correct and accessible
3. **Check Firewall**: Ensure your endpoint accepts connections from OpenCVE
4. **Review Filters**: Check CVSS score and event type filters aren't too restrictive
5. **Test Endpoint**: Use the "Test Webhook" button to verify connectivity

### Authentication Errors

- Verify your authentication headers are correctly formatted in the JSON field
- Check that your endpoint correctly validates the authentication headers
- Ensure header names are case-sensitive matches

### Timeout Errors

- Webhook requests timeout after 10 seconds
- Ensure your endpoint responds quickly (< 5 seconds recommended)
- Move heavy processing to background jobs

## Common Integration Patterns

### Slack Notification

Forward OpenCVE webhooks to Slack:

```python
import requests

def send_to_slack(payload):
    slack_webhook = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

    for change in payload['changes']:
        cve = change['cve']
        score = cve['cvss31'] or 'N/A'
        severity = 'critical' if isinstance(score, float) and score >= 9.0 else 'warning'

        message = {
            "attachments": [{
                "color": "danger" if severity == "critical" else "warning",
                "title": f"{cve['cve_id']} (CVSS: {score})",
                "text": cve['description'][:200] + "...",
                "fields": [
                    {
                        "title": "Project",
                        "value": payload['project'],
                        "short": True
                    },
                    {
                        "title": "Subscriptions",
                        "value": ", ".join(cve['subscriptions']['human']),
                        "short": True
                    }
                ]
            }]
        }

        requests.post(slack_webhook, json=message)
```

### Database Storage

Store CVE alerts in your database:

```python
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class CVEAlert(Base):
    __tablename__ = 'cve_alerts'

    cve_id = Column(String, primary_key=True)
    project = Column(String)
    cvss_score = Column(Float, nullable=True)
    description = Column(String)
    events = Column(JSON)
    received_at = Column(DateTime, default=datetime.utcnow)

def store_webhook(payload):
    engine = create_engine('postgresql://user:pass@localhost/db')
    Session = sessionmaker(bind=engine)
    session = Session()

    for change in payload['changes']:
        cve = change['cve']
        alert = CVEAlert(
            cve_id=cve['cve_id'],
            project=payload['project'],
            cvss_score=cve['cvss31'],
            description=cve['description'],
            events=change['events']
        )
        session.merge(alert)  # Insert or update

    session.commit()
```

## Support

For issues or questions about webhook notifications:

- Check the [OpenCVE Documentation](https://docs.opencve.io)
- Open an issue on [GitHub](https://github.com/opencve/opencve/issues)
- Review your notification configuration and filters

## Changelog

- **v2.0**: Initial webhook notification support
- **v2.1**: Added test webhook feature
- **v2.1**: Added payload example in UI
