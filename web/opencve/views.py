"""
Admin views for OpenCVE.

These views provide administrative functionality like manual sync triggering.
"""

import logging
import os
from datetime import datetime, timezone

import requests
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

logger = logging.getLogger(__name__)


class TriggerSyncView(UserPassesTestMixin, View):
    """
    Trigger CVE synchronization by calling Airflow API to run the DAG.

    This view is restricted to superusers only and provides a way to
    manually trigger CVE data synchronization without waiting for the
    hourly schedule.
    """

    def test_func(self):
        """Only allow superusers to trigger sync"""
        return self.request.user.is_superuser

    def get_airflow_config(self):
        """Get Airflow configuration from environment or defaults"""
        return {
            "url": os.environ.get("AIRFLOW_URL", "http://airflow-webserver:8080"),
            "username": os.environ.get("AIRFLOW_USERNAME", "airflow"),
            "password": os.environ.get("AIRFLOW_PASSWORD", "airflow"),
        }

    def post(self, request, *args, **kwargs):
        """Trigger the opencve DAG via Airflow REST API"""
        airflow_config = self.get_airflow_config()
        dag_id = "opencve"
        api_url = f"{airflow_config['url']}/api/v1/dags/{dag_id}/dagRuns"

        # Create DAG run payload
        payload = {
            "logical_date": datetime.now(timezone.utc).isoformat(),
            "note": f"Manual trigger by {request.user.username} via web UI",
        }

        try:
            logger.info(
                f"User {request.user.username} triggering CVE sync DAG at {airflow_config['url']}"
            )

            response = requests.post(
                api_url,
                json=payload,
                auth=(airflow_config["username"], airflow_config["password"]),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            dag_run = response.json()

            dag_run_id = dag_run.get("dag_run_id")
            state = dag_run.get("state")

            logger.info(
                f"DAG run triggered successfully: {dag_run_id} (state: {state})"
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "CVE sync triggered successfully",
                    "dag_run_id": dag_run_id,
                    "state": state,
                    "airflow_url": f"{airflow_config['url']}/dags/{dag_id}/grid?dag_run_id={dag_run_id}",
                }
            )

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Airflow: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "Failed to connect to Airflow. Is the Airflow service running?",
                },
                status=503,
            )

        except requests.exceptions.HTTPError as e:
            logger.error(f"Airflow API error: {e}")
            error_detail = "Unknown error"
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get(
                        "detail", error_data.get("title", str(e))
                    )
                except:
                    error_detail = e.response.text or str(e)

            return JsonResponse(
                {
                    "success": False,
                    "error": f"Airflow API error: {error_detail}",
                },
                status=e.response.status_code if hasattr(e, "response") else 500,
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error when triggering DAG: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to trigger sync: {str(e)}",
                },
                status=500,
            )

        except Exception as e:
            logger.exception(f"Unexpected error when triggering DAG: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "An unexpected error occurred. Please check the logs.",
                },
                status=500,
            )
