#!/usr/bin/python

from __future__ import print_function

import httplib2
import os
import sys
import oauth2client
import datetime
import time
import urllib2
import json
import warnings

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from os.path import join

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/fitness.body.read', 
    'https://www.googleapis.com/auth/fitness.activity.read']
CLIENT_SECRET_FILE = 'client_secret.json'
HABITICA_SECRET_FILE = 'habitica_secret.json'
APPLICATION_NAME = 'fit-api-project'
DATA_SOURCE_ID = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
CWD = '/home/pi/Git/google-fit-sync'

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
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_fitness_data(timestamps):
    """Shows basic usage of the Fitness API.

    Creates a Fitness API service object and outputs a list of data points
    """
    credentials = get_credentials()    
    http = credentials.authorize(httplib2.Http())
     
    service = discovery.build('fitness', 'v1', http=http)
        
    # Data Source ID
    dataSetId = '{0}-{1}'.format(timestamps[0], timestamps[1])
    
    results = service.users().dataSources().datasets().get(userId='me', dataSourceId=DATA_SOURCE_ID, datasetId=dataSetId).execute()
       
    return results


def get_total_steps(data):
    totalSteps = 0

    for entry in data['point']:
        for value in entry['value']:
            totalSteps += value['intVal']
    
    return totalSteps

    
def get_start_and_end_timestamps():
    today = datetime.date.today()
    dayBeforeYesterday = today - datetime.timedelta(2)
    yesterday = today - datetime.timedelta(1)
    
    # Get the datetimes representing midnight
    ystDatetime = datetime.datetime.combine(dayBeforeYesterday, datetime.datetime.min.time())
    dBYDatetime = datetime.datetime.combine(yesterday, datetime.datetime.min.time())
    
    # Convert to nanoseconds since epoch
    startTime = datetime_to_nanoseconds(ystDatetime)
    endTime = datetime_to_nanoseconds(dBYDatetime)    
    
    print("Getting timestamps for {0:.0f} to {1:.0f}".format(startTime, endTime))
    
    # Remove the digits after the decimal and store as strings
    startTime = '{0:.0f}'.format(startTime)
    endTime = '{0:.0f}'.format(endTime)
    
    return [startTime, endTime]

   
def datetime_to_nanoseconds(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds() * 1000 * 1000 * 1000


def read_habitica_credentials(filePath, fileName):
    with open(join(filePath, fileName), 'r') as content_file:
        content = content_file.read()
    credentials = json.loads(content)
        
    return credentials

def get_habitica_task(taskName, habiticaCredentials):    
    h = httplib2.Http()
    url = 'https://habitica.com/api/v2/user/tasks'
    headers = {'x-api-key': habiticaCredentials['x-api-key'],
               'x-api-user': habiticaCredentials['x-api-user']}
    resp, content = h.request(url, "GET", None, headers=headers)    
    tasks = json.loads(content)
    taskId = None
    
    if(resp['status'] == '200'):
        for task in tasks:
            if(task['text'].lower() == taskName):
                taskId = task['id']
                break
    else:
        print("Server returned status of '{0}'".format(resp['status']))
    
    return taskId


def increment_step_task(taskId, incrementValue, habiticaCredentials):
    h = httplib2.Http()
    url = 'https://habitica.com/api/v2/user/tasks/{0}/up'.format(taskId)
    headers = habiticaCredentials
    
    for x in range(0, incrementValue):
        # Create and execute the HTTP POST request
        resp, content = h.request(url, "POST", None, headers=headers)
        
        # Check the response
        if(resp['status'] == '200'):
            print('Request {0}/{1}: Success'.format(x + 1, incrementValue))
        else:
            print('Request {0}/{1}: Failure'.format(x + 1, incrementValue))
            print("    Server returned status of '{0}'".format(resp['status']))
    
    return

def execute():
    taskName = '1000 steps'
    habiticaCredentials = read_habitica_credentials(CWD, HABITICA_SECRET_FILE)
    timestamps = get_start_and_end_timestamps()
    data = get_fitness_data(timestamps)
    totalSteps = get_total_steps(data)
    incrementValue = totalSteps // 1000    
    taskId = get_habitica_task(taskName, habiticaCredentials)     
     
    print('Total Steps: {0}'.format(totalSteps))
    print('Task will be incremented {0} times'.format(incrementValue))
    
    # If the task exists, increment it
    if(taskId == None):
        print("Task '{0}' does not exist.".format(taskName))
    else:
        print("Located '{0}' task.".format(taskName))
        increment_step_task(taskId, incrementValue, habiticaCredentials)
    
    return

if __name__ == '__main__':
    execute()

