
import os
import requests

from datetime import datetime
from functools import lru_cache

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from kubernetes import config, client

from .config import (
    COMMITS_API_URL,
    GITHUB_API_MAXIMUM_RETRIES,
    GITHUB_DEPLOYMENT_BRANCH,
    GITHUB_API_PAGE_SIZE,
)


@lru_cache(maxsize=128)
def get_k8s_data():
    # Load Kubernetes configuration
    config.load_incluster_config()

    # Create a Kubernetes API client
    v1 = client.CoreV1Api()

    pod_name = os.environ.get('HOSTNAME')
    namespace_path = '/var/run/secrets/kubernetes.io/serviceaccount/namespace'
    with open(namespace_path) as f:
        namespace = f.read()

    # Retrieve the pod object data
    pod_data = v1.read_namespaced_pod(name=pod_name, namespace=namespace)

    # Get the pod's initialization time
    created_time = pod_data.metadata.creation_timestamp

    # Get the image tag i.e. commit SHA
    container_image = pod_data.spec.containers[0].image
    image_tag = container_image.split(":")[-1] if ":" in container_image else None
    return created_time, image_tag


class DeploymentStatus:
    """
    Retrieves deployment status information from a GitHub API endpoint.
    It encapsulates methods to interact with the API, handle retries,
    and extract relevant data from the API response.

    Attributes:
        github_commits_api_url (str): The URL of the GitHub API endpoint for retrieving commits.
        pod_created_time (str): The initialization time of the Kubernetes pod.
        pod_sha (str): The SHA of the commit associated with the pod.

    Methods:
        __init__(): Initializes the DeploymentStatus instance.
        make_api_request(): Makes requests using session retries to the GitHub API endpoint, returns the response data.
        get_deployment_data(): Extracts relevant deployment data from the API response.
        get(): Retrieves deployment status JSON.

    Usage:
        from k8s_deployment_status import DeploymentStatus
        k8s_deployment_status = DeploymentStatus().get()
    """

    def __init__(self):
        self.github_commits_api_url = COMMITS_API_URL
        pod_created_time_obj, pod_sha = get_k8s_data()
        self.pod_created_time = pod_created_time_obj.strftime("%a, %d %b %Y %H:%M:%S UTC")
        self.pod_sha = pod_sha

    def make_api_request(self):
        headers = {"Accept": "application/vnd.github+json"}
        params = {
            "sha": GITHUB_DEPLOYMENT_BRANCH,
            "per_page": GITHUB_API_PAGE_SIZE,
        }

        # Create a session with retries
        session = requests.Session()
        retry_strategy = Retry(
            total=GITHUB_API_MAXIMUM_RETRIES,  # Number of retries
            backoff_factor=1,  # Delay between retries (exponential backoff)
            status_forcelist=[500, 502, 503, 504, 408, 429]  # HTTP status codes to retry
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        # Make a request using the session
        response = session.get(self.github_commits_api_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
        else:
            data = [
                {
                    "msg": f"request failed with {response.status_code} from GitHub, try again later",
                    "status_code": 503
                }
            ]
        return data

    @lru_cache(maxsize=128)
    def get_deployment_data(self):
        deployment_json = {
            "msg": "unable to lookup commit SHA",
            "status_code": 400
        }
        commits_json = self.make_api_request()
        if "status_code" in commits_json[0].keys():
            deployment_json = commits_json[0]
        else:
            for item in commits_json:
                if (
                        isinstance(item, dict)
                        and self.pod_sha in item.get("sha", "")
                ):
                    commit_merged_timestamp = item.get("commit", {}).get("committer", {}).get("date", "")
                    datetime_obj = datetime.strptime(commit_merged_timestamp, "%Y-%m-%dT%H:%M:%SZ")
                    commit_merged_formatted_timestamp = datetime_obj.strftime("%a, %d %b %Y %H:%M:%S UTC")
                    deployment_json = {
                        "branch": GITHUB_DEPLOYMENT_BRANCH,
                        "commit_sha": item.get("sha", ""),
                        "commit_merged": commit_merged_formatted_timestamp,
                        "commit_msg": item.get("commit", {}).get("message", ""),
                        "deployed_at": self.pod_created_time
                    }
                    break
        return deployment_json

    def get(self):
        return self.get_deployment_data()
