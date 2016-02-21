#!/usr/bin/python

""" Retrieve the total number of steps from the Google Fitness API.

Then increment a Hahitica task a number of times based on the step count.
"""

from __future__ import print_function

import httplib2
import os
import oauth2client
import datetime
import json
import warnings
import logging

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from os.path import join

try:
    import argparse
    FLAGS = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    FLAGS = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/fitness.body.read', \
    'https://www.googleapis.com/auth/fitness.activity.read']
CLIENT_SECRET_FILE = 'client_secret.json'
HABITICA_SECRET_FILE = 'habitica_secret.json'
APPLICATION_NAME = 'fit-api-project'
DATA_SOURCE_ID = 'derived:com.google.step_count.' + \
                 'delta:com.google.android.gms:estimated_steps'
CWD = '/home/pi/Git/google-fit-sync'
LOG_FILENAME = '{0}/{1}'.format(CWD, 'log.log')
TASK_NAME = '1000 steps'
STEP_DIVISOR = 1000

# Setup log file
logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO)

# Suppress the warning about the locked_file module
warnings.filterwarnings('ignore', '.*locked_file.*')

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')

    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)

    credential_path = os.path.join(credential_dir, 'fit-sync-python.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if FLAGS:
            credentials = tools.run_flow(flow, store, FLAGS)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        log_and_print('Storing credentials to ' + credential_path)
    return credentials


def get_fitness_data(timestamps):
    """Shows basic usage of the Fitness API.

    Creates a Fitness API service object and outputs a list of data points.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('fitness', 'v1', http=http)

    # Data Source ID
    data_set_id = '{0}-{1}'.format(timestamps[0], timestamps[1])
    results = service.users().dataSources().datasets().get(userId='me', \
        dataSourceId=DATA_SOURCE_ID, datasetId=data_set_id).execute()

    return results


def get_total_steps(data):
    """Count the total number of steps in the data.
    """
    total_steps = 0

    for entry in data['point']:
        for value in entry['value']:
            total_steps += value['intVal']

    return total_steps


def get_start_and_end_timestamps():
    """Get yesterday and the day before yesterday's timestamp values.
    """
    today = datetime.date.today()
    day_before_yest = today - datetime.timedelta(2)
    yesterday = today - datetime.timedelta(1)

    # Get the datetimes representing midnight
    yest_datetime = datetime.datetime.combine(day_before_yest, \
            datetime.datetime.min.time())
    day_before_yest_datetime = datetime.datetime.combine(yesterday, \
            datetime.datetime.min.time())

    # Convert to nanoseconds since epoch
    start_time = datetime_to_nanoseconds(yest_datetime)
    end_time = datetime_to_nanoseconds(day_before_yest_datetime)

    log_and_print("Getting timestamps for {0:.0f} to {1:.0f}"\
            .format(start_time, end_time))

    # Remove the digits after the decimal and store as strings
    start_time = '{0:.0f}'.format(start_time)
    end_time = '{0:.0f}'.format(end_time)

    return [start_time, end_time]


def datetime_to_nanoseconds(date_time):
    """Given a datetime convert it to nanoseconds since epoch.
    """
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (date_time - epoch).total_seconds() * 1000 * 1000 * 1000


def read_habitica_credentials(file_path, file_name):
    """Read the Habitica credentials from the supplied file.
    """
    with open(join(file_path, file_name), 'r') as content_file:
        content = content_file.read()
    credentials = json.loads(content)

    return credentials


def get_habitica_task(task_name, habitica_credentials):
    """Make a call to the Habitica API to get the appropriate task ID.
    """
    http_obj = httplib2.Http()
    url = 'https://habitica.com/api/v2/user/tasks'
    headers = {'x-api-key': habitica_credentials['x-api-key'],
               'x-api-user': habitica_credentials['x-api-user']}
    resp, content = http_obj.request(url, "GET", None, headers=headers)
    task_id = None

    if resp['status'] == '200':
        tasks = json.loads(content)
        log_and_print("Server returned status of '200'")

        for task in tasks:
            if task['text'].lower() == task_name:
                task_id = task['id']
                break
    else:
        log_and_print("Server returned status of '{0}'".format(resp['status']))

    return task_id


def increment_step_task(task_id, increment_value, habitica_credentials):
    """Increment the value of the supplied task the given number of times.
    """
    http_obj = httplib2.Http()
    url = 'https://habitica.com/api/v2/user/tasks/{0}/up'.format(task_id)
    headers = habitica_credentials

    for index in range(0, increment_value):
        # Create and execute the HTTP POST request
        resp, content = http_obj.request(url, "POST", None, headers=headers)

        # Check the response
        if resp['status'] == '200':
            log_and_print('Request {0}/{1}: Success'.\
                    format(index + 1, increment_value))
        else:
            log_and_print('Request {0}/{1}: Failure'.\
                    format(index + 1, increment_value))
            log_and_print("    Server returned status of '{0}'".\
                    format(resp['status']))

    return

def log_and_print(message):
    """Print the message to both the console and the log file.
    """
    print(message)
    logging.info(message)
    return


def execute():
    """Execute the steps to get the data and increment Hahitica task.
    """
    habitica_credentials = read_habitica_credentials(CWD, HABITICA_SECRET_FILE)
    timestamps = get_start_and_end_timestamps()
    data = get_fitness_data(timestamps)
    total_steps = get_total_steps(data)
    increment_value = total_steps // STEP_DIVISOR
    task_id = get_habitica_task(TASK_NAME, habitica_credentials)

    log_and_print('Total Steps: {0}'.format(total_steps))
    log_and_print('Task will be incremented {0} times'.format(increment_value))

    # If the task exists, increment it
    if task_id == None:
        log_and_print("Task '{0}' does not exist.".format(TASK_NAME))
    else:
        log_and_print("Located '{0}' task.".format(TASK_NAME))
        increment_step_task(task_id, increment_value, habitica_credentials)

    return

if __name__ == '__main__':
    execute()

