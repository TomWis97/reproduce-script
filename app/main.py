#!/usr/bin/env python3
import ApiConnector
import getpass
import os
import time
import requests
import configparser
from datetime import datetime

def print_output(text, level="INFO"):
    """Function for logging information. Adds timestamp."""
    global starttime
    now = datetime.now()
    timestamp = now.strftime('%H:%M.%S')
    duration = str((now - starttime).seconds) + "," + str(round((now - starttime).microseconds / 1000)).zfill(3)
    output = "[{duration} - {time}] {level} - {text}".format(duration=duration, time=timestamp, level=level, text=text)
    print(output)

def raise_error(text):
    print_output(text, level="ERROR")
    # Print so we get the timestamp. Then actually raise a RuntimeError to stop execution.
    raise RuntimeError(text)

def main():
    global starttime

    # Read configuration and check parameters.
    config = configparser.ConfigParser()
    with open('config.ini', 'rt') as f:
        config.read_file(f)
    if not (config.has_option('connection', 'api_url') or config.get('connection', 'api_url') == ''):
        raise ValueError("No API URL given.")
    if not (config.has_option('connection', 'app_url') or config.get('connection', 'app_url') == ''):
        raise ValueError("No app URL given.")
    if not (config.has_option('connection', 'namespace') or config.get('connection', 'namespace') == ''):
        raise ValueError("No namespace given.")
    if config.has_option('authentication', 'token'):
        print_output("Using token for authentication.");
        token = config.get('authentication', 'token')
        c = ApiConnector.ApiConnector(config.get('connection', 'api_url'), config.get('connection', 'namespace'), token=token);
    elif (config.has_option('authentication', 'username') and config.has_option('authentication', 'password')):
        print_output("Using username and password for authentication.");
        username = config.get('authentication', 'username')
        password = config.get('authentication', 'password')
        c = ApiConnector.ApiConnector(config.get('connection', 'api_url'), config.get('connection', 'namespace'), username=username, password=password);
    else:
        raise ValueError('No authentication specified in config.')
    if not config.has_option('behaviour', 'delete_ns'):
        raise ValueError("Option delete_ns missing.")
    else:
        delete_namespace = config.getboolean('behaviour', 'delete_ns')
    if not config.has_option('behaviour', 'max_attempts_between_deletes'):
        raise ValueError("Option max_attempts_between_delete smissing.")
    else:
        max_attempts = config.getint('behaviour', 'max_attempts_between_deletes')

    # Check if namespace has to be deleted.
    if c.check_if_namespace_exists() == True:
        try:
            attempts_count = c.get_status_attempts()
            attempts_error = False
        except:
            print_output("Getting attempts failed! Assuming attempts is 1000 and recreating CM.")
            c.delete_status_cm()
            c.create_status_cm()
            attempts_count = 1000
            attempts_error = True
        print_output("Attempts count: " + str(attempts_count))
        if attempts_count >= max_attempts and max_attempts != 0:
            # Delete namespace
            print_output("Removing namespace and waiting for it to be removed.")
            c.delete_self_project()
            checks = 0
            while c.check_if_namespace_exists():
                # Wait until namespace is deleted
                time.sleep(1)
                checks += 1
                if checks > 300:
                    raise_error("Deleting namespace failed.")
            time.sleep(5)

    # Preparing namespace
    print_output("Checking if namespace exists")
    if c.check_if_namespace_exists() == False:
        print_output("Creating namespace...")
        c.create_namespace()
        c.create_status_cm()
    else:
        print_output("Namespace already exists")
        print_output("Cleaning up!")
        cleanup(c)
        if attempts_error == True:
            c.set_status_attempts(1)
        else:
            c.add_status_attempts()

    # Create deployment secret with SSH key
    with open('health-check-deploy', 'rt') as f:
        ssh_key = f.read()
    print_output("Creating secret...")
    c.create_secret(ssh_key, 'deploy-key')
    # We have to wait for a few seconds because it may not be created already.
    time.sleep(5)
    print_output("Linking secret to builder service account...")
    c.link_secret('builder', 'deploy-key')

    # Creating Imagestream
    print_output("Creating ImageStream...")
    c.create_imagestream('check-website-is', 'check-website')

    # Creating BuildConfig
    print_output("Creating BuildConfig...")
    c.create_buildconfig(
        name='check-website-bc',
        app_name='check-website',
        imagestreamtag='check-website-is:latest',
        source_git='https://github.com/tomwis97/phpinfo-test',
        source_context_dir='',
        source_secret='deploy-key',
        source_image='php:7.4-ubi8')

    # Creating DeploymentConfig
    print_output("Creating DeploymentConfig...")
    c.create_deploymentconfig(
        name='check-website-dc',
        app_name='check-website',
        image='check-website-is:latest',
        tcp_port=8080)

    # Creating service
    print_output("Creating Service...")
    c.create_service(
        name='check-website-svc',
        app_name='check-website',
        tcp_port=8080,
        selector_dc='check-website-dc')

    # Initiating build and wait for completion
    print_output("Starting build...")
    c.start_build('check-website-bc')
    loops = 0
    time.sleep(1)
    notified = False
    while True:
        # Wait until build pod is done.
        # Assumes this is the first build.
        time.sleep(1)
        loops += 1
        if loops > 180:
            raise_error("Build took too long!")
        pods = c.get_pods()
        if 'check-website-bc-1-build' not in pods:
            continue
        if 'check-website-bc-1-build' in pods and notified == False:
            notified = True
            print_output("Build running on node {}".format(pods['check-website-bc-1-build']['node']))
        if pods['check-website-bc-1-build']['status'] == "Succeeded":
            break
        if 'Error' in pods['check-website-bc-1-build']['status']:
            raise_error("Error while building image.")

    # Creating route
    print_output("Creating Route...")
    c.create_route(
        app_name='check-website',
        name='check-website-route',
        svc_name='check-website-svc',
        target_port='8080-tcp',
        host=config.get('connection', 'app_url'))

    # Deploy image and wait for completion
    print_output("Starting deployment...")
    c.start_deployment('check-website-dc')

    loops = 0
    app_pod = None
    while True:
        # Wait until the application is deployed
        time.sleep(1)
        loops += 1
        for pod in c.get_pods():
            if ("check-website-dc" in pod and not pod.endswith('deploy')):
                app_pod = pod
                print_output("Application pod found with name: {}, running on node {}".format(
                    app_pod, c.get_pods()[app_pod]['node']))
                break
        if app_pod != None:
            break
        if loops > 40:
            # We're now waiting for a little more than 40 seconds.
            raise_error("Can't find application pod!")
        
    # Do a request if application is running.
    print_output("Waiting for deployment to complete.")
    loops = 0
    while True:
        # Wait until pod is running.
        # Assumes this is the first deployment.
        pods = c.get_pods()
        if pods[app_pod]['status'] == "Running":
            break
        if 'Error' in pods['check-website-bc-1-build']['status']:
            raise_error("Error while building image.")
        if loops > 180:
            raise_error("Build took too long!")
        time.sleep(1)
    time.sleep(2) # Let the router pod update its config with the new pod.

    # Do a request if application is running.
    attempts = 0
    while attempts < 3:
        attempts += 1
        r = requests.get('http://' + config.get('connection', 'app_url'))
        if r.status_code == 200:
            print_output("Status code 200 received. Everything is working correctly!")
            if delete_namespace == True:
                print_output("Delete own project.")
                c.delete_self_project()
            break
        else:
            print_output("Wrong status code received: {}, attempts: {}".format(r.status_code, attempts), "WARNING")
            time.sleep(3)
    else:
        raise_error("Webpage request failed after 3 tries!")

    if (datetime.now() - starttime).seconds > 300:
        # Everything is working, but it takes longer than it should.
        # If this error occures frequently, raise the value above.
        raise_error("This run was succesful, but took way longer than it should!")

def cleanup(connector):
    connector.delete_deploymentconfig('check-website-dc')
    connector.delete_imagestream('check-website-is')
    connector.delete_buildconfig('check-website-bc')
    connector.delete_secret('deploy-key')
    connector.delete_service('check-website-svc')
    connector.delete_route('check-website-route')
    connector.unlink_secret('builder', 'deploy-key')

if __name__ == "__main__":
    global starttime
    starttime = datetime.now()
    main()
