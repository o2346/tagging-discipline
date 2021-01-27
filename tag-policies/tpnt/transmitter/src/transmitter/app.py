from schema.aws.s3.awsapicallviacloudtrail import Marshaller
from schema.aws.s3.awsapicallviacloudtrail import AWSEvent
from schema.aws.s3.awsapicallviacloudtrail import AWSAPICallViaCloudTrail

import os
import sys
import boto3
import json
import csv

def filter_noncompliants(csv):
    #https://www.geeksforgeeks.org/filter-in-python/
    result = filter(lambda x: x['ComplianceStatus'] == 'false', csv)
    #print(len(list(result)))
    return list(result)

def get_dictdata(event):
    parent = event['Records'][0]['s3']['bucket']['name']
    if hasattr(os.environ, 'LAMBDA_TASK_ROOT'):
        local_csvpath = os.path.join(os.environ['LAMBDA_TASK_ROOT'],'localmoc','report.csv')
    else:
        local_csvpath = os.path.join(os.environ['src'],'transmitter','localmoc','report.csv')

    if parent == 'localmoc':
        local_csvpath = os.path.join(os.environ['src'],'transmitter','localmoc','report.csv')
        print(local_csvpath)
        with open(local_csvpath, newline='') as csvfile:
            #https://docs.python.org/3/library/csv.html#reader-objects
            reader = csv.DictReader(csvfile, delimiter=',')
            ret = [dict(d) for d in reader]
            #print(len([dict(d) for d in reader]))

            #https://stackoverflow.com/questions/47115041/read-from-csv-into-a-list-with-dictreader
    else:
        #str(os.environ['LAMBDA_TASK_ROOT'] + "/function/summarytemplates/" + configRuleName + '.json')
        #https://github.com/amazon-archives/serverless-app-examples/blob/master/python/s3-get-object-python/lambda_function.py
        ret = []
    return ret

def lambda_handler(event, context):
    """Sample Lambda function reacting to EventBridge events

    Parameters
    ----------
    event: dict, required
        Event Bridge Events Format

        Event doc: https://docs.aws.amazon.com/eventbridge/latest/userguide/event-types.html

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
        The same input event file
    """

    #Deserialize event into strongly typed object
    awsEvent:AWSEvent = Marshaller.unmarshall(event, AWSEvent)
    detail:AWSAPICallViaCloudTrail = awsEvent.detail

    #Execute business logic

    #https://stackoverflow.com/questions/42312196/how-do-i-read-a-csv-stored-in-s3-with-csv-dictreader

    #Make updates to event payload, if desired
    #awsEvent.detail_type = "HelloWorldFunction updated event of " + awsEvent.detail_type;
    print(json.dumps(event))
    print(os.environ['SENDTO'])
    #Return event for further processing
    return Marshaller.marshall(awsEvent)
