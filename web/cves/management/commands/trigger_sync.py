"""
Django management command to trigger CVE synchronization via Airflow DAG.

This command connects to the Airflow API and triggers the 'opencve' DAG run.
It's useful for manual syncs or testing purposes.

Usage:
    python manage.py trigger_sync
    python manage.py trigger_sync --wait  # Wait for sync to complete
"""

import os
import time
from datetime import datetime, timezone

import requests
from django.conf import settings

from opencve.commands import BaseCommand


class Command(BaseCommand):
    help = "Trigger CVE synchronization by running the Airflow DAG"

    def add_arguments(self, parser):
        parser.add_argument(
            "--wait",
            action="store_true",
            help="Wait for the DAG run to complete before returning",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Maximum time to wait for completion (in seconds, default: 300)",
        )

    def get_airflow_config(self):
        """Get Airflow configuration from environment or defaults"""
        return {
            "url": os.environ.get("AIRFLOW_URL", "http://localhost:8080"),
            "username": os.environ.get("AIRFLOW_USERNAME", "airflow"),
            "password": os.environ.get("AIRFLOW_PASSWORD", "airflow"),
        }

    def trigger_dag(self, airflow_config):
        """Trigger the opencve DAG via Airflow REST API"""
        dag_id = "opencve"
        api_url = f"{airflow_config['url']}/api/v1/dags/{dag_id}/dagRuns"

        # Create DAG run payload
        payload = {
            "logical_date": datetime.now(timezone.utc).isoformat(),
            "note": "Manual trigger via Django management command",
        }

        try:
            response = requests.post(
                api_url,
                json=payload,
                auth=(airflow_config["username"], airflow_config["password"]),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.error(f"Failed to trigger DAG: {e}")
            if hasattr(e.response, "text"):
                self.error(f"Response: {e.response.text}")
            return None

    def get_dag_run_state(self, airflow_config, dag_run_id):
        """Get the state of a DAG run"""
        dag_id = "opencve"
        api_url = f"{airflow_config['url']}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"

        try:
            response = requests.get(
                api_url,
                auth=(airflow_config["username"], airflow_config["password"]),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("state")

        except requests.exceptions.RequestException as e:
            self.error(f"Failed to get DAG run state: {e}")
            return None

    def wait_for_completion(self, airflow_config, dag_run_id, timeout):
        """Wait for DAG run to complete"""
        self.info(f"Waiting for DAG run to complete (timeout: {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            state = self.get_dag_run_state(airflow_config, dag_run_id)

            if state is None:
                self.error("Failed to get DAG run state")
                return False

            if state == "success":
                self.info(
                    f"DAG run completed {self.style.SUCCESS('successfully')} "
                    f"in {self.blue(f'{round(time.time() - start_time, 1)}s')}"
                )
                return True

            if state == "failed":
                self.error(
                    f"DAG run {self.style.ERROR('failed')} "
                    f"after {round(time.time() - start_time, 1)}s"
                )
                return False

            # Still running
            elapsed = round(time.time() - start_time, 1)
            self.info(f"State: {self.blue(state)} (elapsed: {elapsed}s)", ending="\r")
            time.sleep(2)

        self.error(f"Timeout reached ({timeout}s)")
        return False

    def handle(self, *args, **options):
        airflow_config = self.get_airflow_config()

        self.info(f"Triggering CVE sync DAG on {self.blue(airflow_config['url'])}")

        # Trigger the DAG
        dag_run = self.trigger_dag(airflow_config)

        if not dag_run:
            self.error("Failed to trigger DAG run")
            return

        dag_run_id = dag_run.get("dag_run_id")
        state = dag_run.get("state")

        self.info(f"DAG run triggered: {self.bold(dag_run_id)}")
        self.info(f"State: {self.blue(state)}")
        self.info(
            f"View in Airflow UI: {airflow_config['url']}/dags/opencve/grid?dag_run_id={dag_run_id}"
        )

        # Wait for completion if requested
        if options["wait"]:
            success = self.wait_for_completion(
                airflow_config, dag_run_id, options["timeout"]
            )
            if not success:
                self.error("DAG run did not complete successfully")
