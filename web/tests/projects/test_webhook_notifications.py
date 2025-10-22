import json
from unittest.mock import Mock, patch

import pytest
from django.urls import reverse

from projects.models import Notification, Project


@pytest.mark.django_db
class TestWebhookForm:
    """Test webhook form validation"""

    def test_webhook_form_valid_url(
        self, auth_client, create_organization, create_project, create_user
    ):
        """Test that valid webhook URLs are accepted"""
        user = create_user()
        org = create_organization("test-org", user)
        project = create_project("test-project", org)
        client = auth_client(user)

        url = reverse(
            "create_notification",
            kwargs={"org_name": org.name, "project_name": project.name},
        )
        response = client.get(f"{url}?type=webhook")
        assert response.status_code == 200

    def test_webhook_form_headers_validation(
        self, auth_client, create_organization, create_project, create_user
    ):
        """Test that webhook headers must be valid JSON"""
        user = create_user()
        org = create_organization("test-org", user)
        project = create_project("test-project", org)
        client = auth_client(user)

        url = reverse(
            "create_notification",
            kwargs={"org_name": org.name, "project_name": project.name},
        )

        # Valid headers
        response = client.post(
            f"{url}?type=webhook",
            {
                "name": "test-webhook",
                "url": "https://example.com/webhook",
                "headers": json.dumps({"Authorization": "Bearer token"}),
                "is_enabled": True,
                "cvss31_score": "0",
                "created": True,
            },
        )
        assert response.status_code == 302  # Redirect on success

        # Invalid headers (non-string values should fail)
        response = client.post(
            f"{url}?type=webhook",
            {
                "name": "test-webhook-2",
                "url": "https://example.com/webhook",
                "headers": json.dumps({"count": 123}),  # numeric value
                "is_enabled": True,
                "cvss31_score": "0",
                "created": True,
            },
        )
        # Should fail validation because headers must have string values
        assert response.status_code == 200  # Form redisplayed with errors


@pytest.mark.django_db
class TestWebhookNotification:
    """Test webhook notification creation and management"""

    def test_create_webhook_notification(
        self, auth_client, create_organization, create_project, create_user
    ):
        """Test creating a webhook notification"""
        user = create_user()
        org = create_organization("test-org", user)
        project = create_project("test-project", org)
        client = auth_client(user)

        url = reverse(
            "create_notification",
            kwargs={"org_name": org.name, "project_name": project.name},
        )

        response = client.post(
            f"{url}?type=webhook",
            {
                "name": "my-webhook",
                "url": "https://example.com/webhook",
                "headers": json.dumps({"X-API-Key": "secret"}),
                "is_enabled": True,
                "cvss31_score": "7.0",
                "created": True,
                "metrics": True,
            },
        )

        assert response.status_code == 302
        notification = Notification.objects.get(project=project, name="my-webhook")
        assert notification.type == "webhook"
        assert (
            notification.configuration["extras"]["url"] == "https://example.com/webhook"
        )
        assert notification.configuration["extras"]["headers"]["X-API-Key"] == "secret"
        assert notification.configuration["metrics"]["cvss31"] == "7.0"
        assert "created" in notification.configuration["types"]
        assert "metrics" in notification.configuration["types"]

    def test_update_webhook_notification(
        self,
        auth_client,
        create_organization,
        create_project,
        create_notification,
        create_user,
    ):
        """Test updating a webhook notification"""
        user = create_user()
        org = create_organization("test-org", user)
        project = create_project("test-project", org)
        notification = create_notification(
            "test-webhook",
            project,
            type="webhook",
            configuration={
                "types": ["created"],
                "metrics": {"cvss31": "0"},
                "extras": {
                    "url": "https://example.com/old",
                    "headers": {},
                },
            },
        )
        client = auth_client(user)

        url = reverse(
            "edit_notification",
            kwargs={
                "org_name": org.name,
                "project_name": project.name,
                "notification": notification.name,
            },
        )

        response = client.post(
            url,
            {
                "name": "test-webhook",
                "url": "https://example.com/new",
                "headers": json.dumps({"Authorization": "Bearer new-token"}),
                "is_enabled": True,
                "cvss31_score": "9.0",
                "created": True,
                "first_time": True,
            },
        )

        assert response.status_code == 302
        notification.refresh_from_db()
        assert notification.configuration["extras"]["url"] == "https://example.com/new"
        assert (
            notification.configuration["extras"]["headers"]["Authorization"]
            == "Bearer new-token"
        )
        assert notification.configuration["metrics"]["cvss31"] == "9.0"
        assert "first_time" in notification.configuration["types"]


@pytest.mark.django_db
class TestWebhookTest:
    """Test the webhook test functionality"""

    @patch("requests.post")
    def test_webhook_test_success(
        self,
        mock_post,
        auth_client,
        create_organization,
        create_project,
        create_notification,
        create_user,
    ):
        """Test successful webhook test"""
        user = create_user()
        org = create_organization("test-org", user)
        project = create_project("test-project", org)
        notification = create_notification(
            "test-webhook",
            project,
            type="webhook",
            configuration={
                "types": ["created"],
                "metrics": {"cvss31": "0"},
                "extras": {
                    "url": "https://example.com/webhook",
                    "headers": {"X-API-Key": "secret"},
                },
            },
        )
        client = auth_client(user)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        url = reverse(
            "test_notification",
            kwargs={
                "org_name": org.name,
                "project_name": project.name,
                "notification": notification.name,
            },
        )

        response = client.post(url)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["status_code"] == 200

        # Verify the webhook was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args.kwargs["url"] == "https://example.com/webhook"
        assert "X-API-Key" in call_args.kwargs["headers"]
        assert call_args.kwargs["headers"]["X-API-Key"] == "secret"
        assert "json" in call_args.kwargs
        payload = call_args.kwargs["json"]
        assert payload["organization"] == org.name
        assert payload["project"] == project.name
        assert payload["notification"] == notification.name
        assert payload["title"] == "Test notification from OpenCVE"

    @patch("requests.post")
    def test_webhook_test_failure(
        self,
        mock_post,
        auth_client,
        create_organization,
        create_project,
        create_notification,
        create_user,
    ):
        """Test failed webhook test (HTTP error)"""
        user = create_user()
        org = create_organization("test-org", user)
        project = create_project("test-project", org)
        notification = create_notification(
            "test-webhook",
            project,
            type="webhook",
            configuration={
                "types": ["created"],
                "metrics": {"cvss31": "0"},
                "extras": {
                    "url": "https://example.com/webhook",
                    "headers": {},
                },
            },
        )
        client = auth_client(user)

        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        url = reverse(
            "test_notification",
            kwargs={
                "org_name": org.name,
                "project_name": project.name,
                "notification": notification.name,
            },
        )

        response = client.post(url)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["status_code"] == 500

    def test_webhook_test_email_notification_fails(
        self,
        auth_client,
        create_organization,
        create_project,
        create_notification,
        create_user,
    ):
        """Test that testing email notifications is not allowed"""
        user = create_user()
        org = create_organization("test-org", user)
        project = create_project("test-project", org)
        notification = create_notification(
            "test-email",
            project,
            type="email",
            configuration={
                "types": ["created"],
                "metrics": {"cvss31": "0"},
                "extras": {"email": "test@example.com"},
            },
        )
        client = auth_client(user)

        url = reverse(
            "test_notification",
            kwargs={
                "org_name": org.name,
                "project_name": project.name,
                "notification": notification.name,
            },
        )

        response = client.post(url)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "Only webhook" in data["error"]
