# Copyright 2025 Google LLC All Rights Reserved.
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

"""Client initialization for the Google Analytics APIs."""

import contextlib
import os
import subprocess
import threading
from importlib import metadata
from unittest.mock import patch

import google.auth
from google.analytics import (
    admin_v1beta,
    data_v1beta,
    admin_v1alpha,
    data_v1alpha,
)
from google.api_core.gapic_v1.client_info import ClientInfo
from google.oauth2 import service_account


def _get_package_version_with_fallback():
    """Returns the version of the package.

    Falls back to 'unknown' if the version can't be resolved.
    """
    try:
        return metadata.version("analytics-mcp")
    except:
        return "unknown"


# Client information that adds a custom user agent to all API requests.
_CLIENT_INFO = ClientInfo(
    user_agent=f"analytics-mcp/{_get_package_version_with_fallback()}"
)

# Read-only scope for Analytics Admin API and Analytics Data API.
_READ_ONLY_ANALYTICS_SCOPE = (
    "https://www.googleapis.com/auth/analytics.readonly"
)

# Lock to ensure client and credential creation is thread-safe
_client_lock = threading.Lock()
_CREDENTIALS = None


@contextlib.contextmanager
def prevent_stdio_inheritance():
    """Prevents child processes from inheriting the parent's stdio handles.

    Fixes a deadlock on Windows where `google.auth.default()` spawns `gcloud`
    via subprocess without redirecting stdin, causing it to inherit the
    ProactorEventLoop's overlapping I/O handles used by MCP's stdio transport.
    """
    original_popen = subprocess.Popen

    def safe_popen(*args, **kwargs):
        if kwargs.get("stdin") is None:
            kwargs["stdin"] = subprocess.DEVNULL
        return original_popen(*args, **kwargs)

    with patch("subprocess.Popen", new=safe_popen):
        yield


def _get_credentials():
    """Returns credentials for Google Analytics API calls.

    Resolution order:

    1. **Domain-Wide Delegation (DWD)** — if both `GOOGLE_APPLICATION_CREDENTIALS`
       (path to a service-account JSON key) and `GOOGLE_DWD_SUBJECT` (email
       of the user to impersonate) env vars are set, load the SA key and
       apply `.with_subject(GOOGLE_DWD_SUBJECT)` for DWD impersonation. The
       SA's client_id must be granted DWD with the analytics.readonly scope
       in the impersonated user's Workspace admin. Use this path in
       restrictive Workspace orgs where the gcloud OAuth client is blocked
       or where SA emails cannot be added directly to GA4 property access.
    2. **Application Default Credentials (ADC)** — fallback to standard
       `google.auth.default()`. Uses gcloud user credentials, GCE metadata,
       or a SA key referenced by `GOOGLE_APPLICATION_CREDENTIALS` *without*
       impersonation.
    """
    global _CREDENTIALS
    # Expected to be called under _client_lock
    if _CREDENTIALS is None:
        sa_key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        dwd_subject = os.environ.get("GOOGLE_DWD_SUBJECT")
        if sa_key_path and dwd_subject:
            _CREDENTIALS = service_account.Credentials.from_service_account_file(
                sa_key_path,
                scopes=[_READ_ONLY_ANALYTICS_SCOPE],
            ).with_subject(dwd_subject)
        else:
            with prevent_stdio_inheritance():
                _CREDENTIALS, _ = google.auth.default(
                    scopes=[_READ_ONLY_ANALYTICS_SCOPE]
                )
    return _CREDENTIALS


def create_admin_api_client() -> admin_v1beta.AnalyticsAdminServiceClient:
    """Returns the Google Analytics Admin API client."""
    with _client_lock:
        return admin_v1beta.AnalyticsAdminServiceClient(
            client_info=_CLIENT_INFO, credentials=_get_credentials()
        )


def create_data_api_client() -> data_v1beta.BetaAnalyticsDataClient:
    """Returns the Google Analytics Data API client."""
    with _client_lock:
        return data_v1beta.BetaAnalyticsDataClient(
            client_info=_CLIENT_INFO, credentials=_get_credentials()
        )


def create_admin_alpha_api_client() -> (
    admin_v1alpha.AnalyticsAdminServiceClient
):
    """Returns the Google Analytics Admin API (alpha) client."""
    with _client_lock:
        return admin_v1alpha.AnalyticsAdminServiceClient(
            client_info=_CLIENT_INFO, credentials=_get_credentials()
        )


def create_data_api_alpha_client() -> data_v1alpha.AlphaAnalyticsDataClient:
    """Returns the Google Analytics Data API (Alpha) client."""
    with _client_lock:
        return data_v1alpha.AlphaAnalyticsDataClient(
            client_info=_CLIENT_INFO, credentials=_get_credentials()
        )
