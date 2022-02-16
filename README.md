# reproduce-script
This is a script to reproduce the problems we're experiencing with OVN-kubernetes on OCP4.8.

We are aware that this does not represent normal use of a cluster.

## Requirements
- Be logged in as a user with `cluster-admin` permissions.
- Have Ansible installed.
- Have pip3 installed. (For installing the Python `requests` module.)

## Usage
1. `cd` to the same directory as this file.
2. Run the playbook:
```bash
ansible-playbook deploy-script.yml
```
3. Run the script:
```bash
./run.sh
```

## Actions done to your cluster
This playbook and script applies some changes to your cluster.   
Changes made by the playbook:
- Creates a ServiceAccount within the `openshift` namespace. (I had to put it somewhere...)
- Creates a ClusterRoleBinding ("`health-check-script-self-provisioner`").
- It configures config.ini in the `app` directory with your default clusterdomain, the API token of the SA and your API URL.

Changes made by the script:
- The script creates a namespace `health-check` **and DELETES it afterwards**.
- It deploys an S2I app within that namespace.
