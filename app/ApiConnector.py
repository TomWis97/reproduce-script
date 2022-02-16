import json
import requests
import base64
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ApiConnector:
    headers = {
               "Accept": "application/json, */*",
               "User-Agent": "health-check-script/v0.1"}

    def __init__(self, host, namespace, token=None,
            username=None, password=None):
        self.host = host
        self.namespace = namespace
        if (token is not None):
            self.token = token
        elif (username is not None and password is not None):
            self.token = self.__login(username, password)
        else:
            ValueError("No credentials provided!")
        self.headers['Authorization'] = "Bearer " + self.token
        
    def __login(self, username, password):
        """Login to OpenShift with username and password.
        Returns access token."""
        r = requests.get(self.host + '/oauth/authorize?client_id=openshift-challenging-client&response_type=token',
                         auth=(username, password), verify=False, allow_redirects=False)
        # In de location header wordt de URL genoemd. Nu moeten we deze URL parsen zodat
        # we het token kunnen vinden. Sorry voor degene die dit ooit moet reverse engineren.
        urlItems = [ x.split('=') for x in r.headers['Location'].split('#')[1].split('&')]
        urlItemsDict = {}
        for urlItem in urlItems:
            urlItemsDict[urlItem[0]] = urlItem[1]
        return urlItemsDict['access_token']

    def __do_post(self, url, data):
        """Execute a POST action. Raises exception when 
        status code is not successful."""
        headers = self.headers
        headers["Content-Type"] = "application/json"
        r = requests.post(self.host + url,
                          verify=False,
                          json=data,
                          headers=self.headers)
        # Generate exception when this failed.
        r.raise_for_status()
        return r

    def __do_put(self, url, data):
        """Execute a PUT action. Raises exception when 
        status code is not successful."""
        r = requests.put(self.host + url,
                          verify=False,
                          json=data,
                          headers=self.headers)
        # Generate exception when this failed.
        r.raise_for_status()
        return r

    def __do_patch(self, url, data):
        """Execute a PATCH action. Raises exception when 
        status code is not successful."""
        headers = self.headers
        headers["Content-Type"] = "application/strategic-merge-patch+json"
        r = requests.patch(self.host + url,
                           verify=False,
                           json=data,
                           headers=headers)
        # Generate exception when this failed.
        r.raise_for_status()
        return r

    def __do_get(self, url):
        """Execute a GET action. Returns requests object."""
        r = requests.get(self.host + url,
                         verify=False,
                         headers=self.headers)
        return r

    def __do_delete(self, url):
        """Execute a DELETE action. Returns requests object."""
        body = {"propagationPolicy": "Background"}
        r = requests.delete(self.host + url,
                         verify=False,
                         json=body,
                         headers=self.headers)
        return r

    def check_if_namespace_exists(self):
        """Check if namespace exists. Returns True or False."""
        r = requests.get(self.host + '/api/v1/namespaces/{}'.format(self.namespace),
                         headers=self.headers,
                         verify=False)
        if r.status_code == 404:
            return False
        elif r.status_code == 403:
            # We don't know if we're just not authorized to the namespace
            # or if it does not exist. Just assume that it doesn't exist.
            return False
        elif r.status_code == 200:
            return True
        else:
            raise RuntimeError("Unexpected status code: {}".format(r.status_code))

    def set_namespace_labels(self, labels):
        """Set labels on namespace. labels is a dictionary."""
        self.__do_patch('/api/v1/namespaces/{}?fieldManager=kubectl-label'.format(self.namespace), {'metadata': {'labels': labels }})

    def get_namespace_labels(self):
        """Returns list of labels on namespace."""
        data = self.__do_get('/api/v1/namespaces/{}'.format(self.namespace))
        if data.status_code in [404, 403]:
            raise ValueError("Cannot get labels of non-existing namespace!")
        return data.json()['metadata']['labels']

    def create_status_cm(self):
        """Create a configmap with status."""
        self.__do_post('/api/v1/namespaces/{}/configmaps'.format(self.namespace),
            {'kind': 'ConfigMap',
             'apiVersion': 'v1',
             'metadata': {'name': 'health-check-status'},
             'data': {'attempts': "1"}})

    def delete_status_cm(self):
        """Delete configmap with status."""
        self.__do_delete('/api/v1/namespaces{}/configmaps/health-check-status')

    def get_status_attempts(self):
        """Get attempts from configmap."""
        configmap = self.__do_get('/api/v1/namespaces/{}/configmaps/health-check-status'.format(self.namespace))
        return int(configmap.json()['data']['attempts'])

    def set_status_attempts(self, number):
        """Set attempts in configmap to number."""
        configmap = {"data": {"attempts": str(number)}}
        self.__do_patch('/api/v1/namespaces/{}/configmaps/health-check-status'.format(self.namespace),
                        configmap)

    def add_status_attempts(self):
        """Get current attempts and change to n+1."""
        current = int(self.get_status_attempts())
        self.set_status_attempts(current + 1)

    def create_namespace(self):
        """Create a new project based on namespace defined in object.
        Only creates namespace if it doesn't exist yet."""
        body = {
                "kind": "ProjectRequest",
                "apiVersion": "project.openshift.io/v1",
                "metadata": {
                    "name": self.namespace,
                    "creationTimestamp": None }}

        # Multiple attempts for creating a namespace
        for attempt in range(0, 5):
            try:
                r = self.__do_post('/apis/project.openshift.io/v1/projectrequests', body)
                break
            except requests.exceptions.HTTPError as ex:
                if "409 Client Error: Conflict for url" in str(ex):
                    # This happens when we're too quick with creating a new namespace.
                    time.sleep(5)
                else:
                    # Something else went wrong. Raise exception anyway.
                    r.raise_for_status()
                    break
        try:
            return r
        except UnboundLocalError:
            raise RuntimeError("Failed to create project. Check if previous NS has been removed and permissions of serviceaccount.")
        
    def create_secret(self, ssh_key, secret_name):
        """Create secret from given SSH key (as string)."""
        bytes_ssh_key = ssh_key.encode()
        body = {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "creationTimestamp": None,
                    "name": secret_name },
                "data": {
                    "ssh-privatekey": base64.b64encode(bytes_ssh_key).decode()}}
        self.__do_post('/api/v1/namespaces/{}/secrets'.format(self.namespace), body)

    def link_secret(self, service_account, secret_name):
        """Link a secret to a service account."""
        source = self.__do_get(
            '/api/v1/namespaces/{}/serviceaccounts/{}'.format(
                self.namespace, service_account))
        # This should be succesful.
        source.raise_for_status()
        data = source.json()
        # Returned data is a dict. We have to add our new secret to the 
        # secrets list.
        data['secrets'].append({"name": secret_name})
        # ...and send data back.
        self.__do_put(
            '/api/v1/namespaces/{}/serviceaccounts/builder'.format(
                self.namespace),
            data)

    def unlink_secret(self, service_account, secret_name):
        """Unlink a secret from a service account."""
        source = self.__do_get(
            '/api/v1/namespaces/{}/serviceaccounts/{}'.format(
                self.namespace, service_account))
        # This should be succesful.
        source.raise_for_status()
        data = source.json()
        # Returned data is a dict. We have to remove all secrets from the
        # secrets list. First build a new dict without the secret
        new_secrets = []
        for secret in data['secrets']:
            if secret['name'] != secret_name:
                new_secrets.append({"name": secret['name']})

        # Put it in place
        data['secrets'] = new_secrets
        # ...and send data back.
        self.__do_put(
            '/api/v1/namespaces/{}/serviceaccounts/builder'.format(
                self.namespace),
            data)

    def create_imagestream(self, name, app_name):
        """Create an ImageStream with a name and app_name as label."""
        body = {
                "apiVersion": "image.openshift.io/v1",
                "kind": "ImageStream",
                "metadata": {
                    "annotations": {
                        "openshift.io/generated-by": "health-check-script"},
                    "creationTimestamp": None,
                    "labels": {
                        "app": app_name },
                    "name": name},
                "spec": {
                    "lookupPolicy": {
                        "local": False}},
                "status": {
                    "dockerImageRepository": ""}}
        self.__do_post('/apis/image.openshift.io/v1/namespaces/{}/imagestreams'.format(
                self.namespace),
            body)

    def create_buildconfig(self, name, app_name, imagestreamtag, source_git,
        source_context_dir, source_secret, source_image):
        """Create a buildconfig. Takes the following arguments:
        - name: Name of new build config.
        - app_name: Name of application in labels.
        - imagestreamtag: Image stream tag to write the image to.
        - source_git: Git URL from where to pull the source from
        - source_context_dir: Directory in source_git to use.
        - source_secret: Secret to use when pulling source.
        - source_image: Image to use as base.
        """
        body = {
                "apiVersion": "build.openshift.io/v1",
                "kind": "BuildConfig",
                "metadata": {
                    "annotations": {
                        "openshift.io/generated-by": "health-check-script"},
                    "creationTimestamp": None,
                    "labels": {
                        "app": app_name},
                    "name": name},
                "spec": {
                    "nodeSelector": None,
                    "output": {
                        "to": {
                            "kind": "ImageStreamTag",
                            "name": imagestreamtag}},
                    "postCommit": {},
                    "resources": {},
                    "source": {
                        "sourceSecret": {
                            "name": source_secret},
                        "type": "git",
                        "contextDir": source_context_dir,
                        "git": {
                            "uri": source_git}},
                    "strategy": {
                        "sourceStrategy": {
                            "from": {
                                "kind": "ImageStreamTag",
                                "name": source_image,
                                "namespace": "openshift"}},
                        "type": "Source"},
                    "Triggers": []},
                "status": {
                    "lastVersion": 0}}
        self.__do_post('/apis/build.openshift.io/v1/namespaces/{}/buildconfigs'.format(
            self.namespace),
            body)

    def create_deploymentconfig(self, app_name, name, image, tcp_port, replicas=1):
        body = {
                "apiVersion": "apps.openshift.io/v1",
                "kind": "DeploymentConfig",
                "metadata": {
                    "annotations": {
                        "openshift.io/generated-by": "health-check-script"},
                    "creationTimestamp": None,
                    "labels": {
                        "app": app_name},
                    "name": name},
                "spec": {
                    "replicas": replicas,
                    "selector": {
                        "app": app_name,
                        "deploymentconfig": name},
                    "strategy": {
                        "resources": {}},
                    "template": { 
                        "metadata": {
                            "annotations": {
                                "openshift.io/generated-by": "health-check-script"},
                            "creationTimestamp": None,
                            "labels": {
                                "app": app_name,
                                "deploymentconfig": name}},
                        "spec": {
                            "containers": [{
                                "image": 'image-registry.openshift-image-registry.svc:5000/' + self.namespace + '/' + image,
                                "name": name + "-pod",
                                "ports": [{
                                    "containerPort": tcp_port,
                                    "protocol": "TCP"}],
                                "resources": {}}]}},
                        "test": False,
                        "triggers": []},
                "status": {
                    "availableReplicas": 0,
                    "latestVersion": 0,
                    "observedGeneration": 0,
                    "replicas": 0,
                    "unavailableReplicas": 0,
                    "updatedReplicas": 0}}
        self.__do_post('/apis/apps.openshift.io/v1/namespaces/{}/deploymentconfigs'.format(
            self.namespace),
            body)

    def create_service(self, app_name, name, tcp_port, selector_dc):
        body = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "annotations": {
                        "openshift.io/generated-by": "health-check-script"},
                    "creationTimestamp": None,
                    "labels": {
                        "app": app_name},
                    "name": name},
                "spec": {
                    "ports": [{
                        "name": str(tcp_port) + '-tcp',
                        "port": tcp_port,
                        "protocol": "TCP",
                        "targetPort": tcp_port}],
                    "selector": {
                        "app": app_name,
                        "deploymentconfig": selector_dc}},
                    "status": {
                        "loadBalancer": {}}}
        self.__do_post('/api/v1/namespaces/{}/services'.format(
            self.namespace),
            body)

    def start_build(self, name):
        body = {
                "kind": "BuildRequest",
                "apiVersion": "build.openshift.io/v1",
                "metadata": {
                    "name": name,
                    "creationTimestamp": None},
                "triggeredBy": [{
                    "message": "Triggered by health-check-script."}],
                "dockerStrategyOptions": {},
                "sourceStrategyOptions": {}}
        self.__do_post('/apis/build.openshift.io/v1/namespaces/{}/buildconfigs/{}/instantiate'.format(
            self.namespace,
            name),
            body)

    def start_deployment(self, deploymentconfig):
        body = {
                "kind": "DeploymentRequest",
                "apiVersion": "apps.openshift.io/v1",
                "name": deploymentconfig,
                "latest": True,
                "force": True}
        self.__do_post('/apis/apps.openshift.io/v1/namespaces/{}/deploymentconfigs/{}/instantiate'.format(
            self.namespace,
            deploymentconfig),
            body)

    def create_route(self, app_name, name, svc_name, target_port, host):
        body = {
                "apiVersion": "route.openshift.io/v1",
                "kind": "Route",
                "metadata": {
                    "creationTimestamp": None,
                    "labels": {
                        "app": app_name},
                    "name": name},
                "spec": {
                    "host": host,
                    "port": {
                        "targetPort": target_port},
                    "to": {
                        "kind": "",
                        "name": svc_name,
                        "weight": None}},
                "status": {
                    "ingress": None}}
        self.__do_post('/apis/route.openshift.io/v1/namespaces/{}/routes'.format(
            self.namespace),
            body)

    def delete_deploymentconfig(self, name):
        return self.__do_delete('/apis/apps.openshift.io/v1/namespaces/{}/deploymentconfigs/{}'.format(
            self.namespace,
            name))

    def delete_imagestream(self, name):
        return self.__do_delete('/apis/image.openshift.io/v1/namespaces/{}/imagestreams/{}'.format(
            self.namespace,
            name))

    def delete_buildconfig(self, name):
        return self.__do_delete('/apis/build.openshift.io/v1/namespaces/{}/buildconfigs/{}'.format(
            self.namespace,
            name))

    def delete_secret(self, name):
        return self.__do_delete('/api/v1/namespaces/{}/secrets/{}'.format(
            self.namespace,
            name))

    def delete_service(self, name):
        return self.__do_delete('/api/v1/namespaces/{}/services/{}'.format(
            self.namespace,
            name))

    def delete_route(self, name):
        return self.__do_delete('/apis/route.openshift.io/v1/namespaces/{}/routes/{}'.format(
            self.namespace,
            name))

    def delete_self_project(self):
        return self.__do_delete('/apis/project.openshift.io/v1/projects/{}'.format(
            self.namespace))

    def get_pods(self):
        data = self.__do_get('/api/v1/namespaces/{}/pods'.format(self.namespace)).json()
        pods = {}
        for item in data['items']:
            if 'nodeName' in item['spec']:
                pods[item['metadata']['name']] = {
                   'status': item['status']['phase'],
                   'node': item['spec']['nodeName']}
        return pods
