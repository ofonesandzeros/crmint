# Copyright 2024 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Worker to create Google Ads BigQuery Data Transfer Service with Backfill option."""

from google.cloud import bigquery_datatransfer_v1
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
from datetime import datetime, timedelta
from jobs.workers.bigquery import bq_worker


class BQGoogleAdsTransferWorker(bq_worker.BQWorker):
    """Worker to create Google Ads BigQuery Data Transfer Service with Backfill."""

    PARAMS = [
        ('gcp_project_id', 'string', True, '', 'GCP Project ID'),
        ('bq_dataset_id', 'string', True, '', 'BigQuery Dataset ID'),
        ('google_ads_customer_id', 'string', True, '', 'Google Ads Customer ID'),
        ('backfill', 'boolean', False, False, 'Backfill data from the earliest available date')
    ]

    def _get_transfer_client(self):
        """Returns the BigQuery Data Transfer Service client."""
        return bigquery_datatransfer_v1.DataTransferServiceClient()

    def _create_dataset_if_not_exists(self, project_id: str, dataset_id: str):
        """Creates the dataset if it doesn't already exist."""
        bq_client = self._get_client()
        dataset_ref = bigquery.Dataset(f"{project_id}.{dataset_id}")

        try:
            bq_client.get_dataset(dataset_ref)
            self.log_info(f"Dataset {dataset_id} already exists.")
        except NotFound:
            self.log_info(f"Dataset {dataset_id} not found, creating a new one.")
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            bq_client.create_dataset(dataset)
            self.log_info(f"Dataset {dataset_id} created successfully.")

    def _create_google_ads_transfer(self, project_id: str, dataset_id: str, customer_id: str, backfill: bool):
        """Creates a BigQuery Data Transfer Service for Google Ads with optional backfill."""
        transfer_client = self._get_transfer_client()

        transfer_config = bigquery_datatransfer_v1.TransferConfig(
            destination_dataset_id=dataset_id,
            display_name='Google Ads Transfer',
            data_source_id='google_ads',
            params={"customer_id": customer_id},
        )

        parent = f"projects/{project_id}/locations/us"

        # If backfill is enabled, set the start time to the earliest date (e.g., 365 days ago).
        if backfill:
            earliest_start_time = (datetime.utcnow() - timedelta(days=365))
            transfer_config.start_time = earliest_start_time
            self.log_info(f"Backfill enabled, starting data transfer from {earliest_start_time}.")

        response = transfer_client.create_transfer_config(
            parent=parent, transfer_config=transfer_config
        )

        self.log_info(f"Transfer created: {response.name}")

    def _execute(self):
        project_id = self._params['gcp_project_id']
        dataset_id = self._params['bq_dataset_id']
        customer_id = self._params['google_ads_customer_id']
        backfill = self._params['backfill']

        self._create_dataset_if_not_exists(project_id, dataset_id)
        self._create_google_ads_transfer(project_id, dataset_id, customer_id, backfill)
