# Kubernetes Deployment Status

Retrieves deployment status information from a GitHub API endpoint. 

It encapsulates methods to interact with the API, handle retries, and extract relevant data from the API response.

Most of the data is memoized as well to avoid unnecessary API calls.

## Installation

```shell
pip install k8s-deployment-status
```
### Package dependencies(auto-install):

- kubernetes
- requests

## Usage

To use the package follow these steps,

### Kubernetes Environment Variables

Set necessary environment variables like so in your Kubernetes yaml file.

```yaml
    env:
    - name: GITHUB_OWNER
      value: "organisation/owner-name"
    - name: GITHUB_REPO
      value: "repo-name"
    - name: GITHUB_DEPLOYMENT_BRANCH
      value: "main"
    - name: GITHUB_API_PAGE_SIZE
      value: "5"
    - name: GITHUB_API_MAXIMUM_RETRIES
      value: "3"
```
All available options are mentioned above. GITHUB_OWNER, GITHUB_REPO are required.

Feel free to check config.py for default values per variable.

### Import and Actual usage

Import package and respective class in the respective module

```commandline
from deployment_status import DeploymentStatus

@app.route('/api/ros/v1/deployment_status', methods=['GET'])
    def deployment_status():
        deployment_status_data = DeploymentStatus().get()
        return jsonify(deployment_status_data)
```

## Response Data

The output data should look like so,

```commandline
{
    "branch": "main",
    "commit_merged": "Thu, 15 Jun 2023 14:38:16 UTC",
    "commit_msg": "Add redis as required dependency",
    "commit_sha": "9c2ee47951a8d25c7aa1402998344c5470956eb7",
    "deployed_at": "Thu, 15 Jun 2023 18:59:25 UTC"
}
```
