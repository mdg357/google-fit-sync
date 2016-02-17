#!/c/Users/User/Anaconda2/python

from __future__ import print_function
import httplib2
import os
import sys

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/fitness.body.read', 
    'https://www.googleapis.com/auth/fitness.activity.read']
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'fit-api-project'


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
            print('In the ELSE')
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_fitness_data():
    """Shows basic usage of the Fitness API.

    Creates a Fitness API service object and outputs a list of data points
    """
    credentials = get_credentials()    
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('fitness', 'v1', http=http)
        
    # Data Source ID
    dataSrcId = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
    dataSetId = '1455602400000000000-1455688800000000000'
        
    results = service.users().dataSources().datasets().get(userId='me', dataSourceId=dataSrcId, datasetId=dataSetId).execute()
       
    return results

def parse_data(data):
    for entry in data['point']:
        print(entry['value'][0]['intVal'])
    
    #print(data['point'][0]['value'][0]['intVal'])
    return

if __name__ == '__main__':
    data = get_fitness_data()
    parse_data(data)