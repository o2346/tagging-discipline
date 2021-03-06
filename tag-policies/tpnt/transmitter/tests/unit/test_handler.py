import pytest
#https://docs.pytest.org/en/stable/assert.html
#https://alexharv074.github.io/2019/03/02/introduction-to-sam-part-i-using-the-sam-cli.html

from schema.aws.s3.awsapicallviacloudtrail import AWSEvent
from schema.aws.s3.awsapicallviacloudtrail import AWSAPICallViaCloudTrail
from schema.aws.s3.awsapicallviacloudtrail import Marshaller
from function import app

import os
import sys
import boto3
import json
import csv

@pytest.fixture()
def eventBridgeEvent():

    eventpath = os.path.join(os.path.abspath('events'),'event.json')
    with open(eventpath) as json_file:
        eventjson = json.load(json_file)
    return eventjson

    #return {
    #        "version":"0",
    #        "id":"7bf73129-1428-4cd3-a780-95db273d1602",
    #        "detail-type":"AWS API Call via CloudTrail",
    #        "source":"aws.s3",
    #        "account":"123456789012",
    #        "time":"2015-11-11T21:29:54Z",
    #        "region":"us-east-1",
    #        "resources":[
    #          "arn:aws:ec2:us-east-1:123456789012:instance/i-abcd1111"
    #        ],
    #        "detail":{
    #          "ADD-YOUR-FIELDS-HERE":""
    #        }
    #}


def test_lambda_handler(eventBridgeEvent, mocker):
    os.environ['SENDTO'] = 'Jone Due'
    os.environ['BUCKET1'] = 'dummybucket1'
    os.environ['BUCKET2'] = 'dummybucket2'
    os.environ['testing'] = 'True'
    ret = app.lambda_handler(eventBridgeEvent, "")

    awsEventRet:AWSEvent = Marshaller.unmarshall(ret, AWSEvent)
    detailRet:AWSAPICallViaCloudTrail = awsEventRet.detail

    assert awsEventRet.detail_type.startswith("Successful")
    #assert True

def test_filter_noncompliants(eventBridgeEvent, mocker):
#    for p in sys.path:
#        print(p)
    csvpath = os.path.join(os.environ['src'],'function','localmoc','report.csv')
    print(csvpath)
    with open(csvpath, newline='') as csvfile:
        #https://docs.python.org/3/library/csv.html#reader-objects
        reader = csv.DictReader(csvfile, delimiter=',')
        #print(len([dict(d) for d in reader]))
        #https://stackoverflow.com/questions/47115041/read-from-csv-into-a-list-with-dictreader
        ret = app.filter_noncompliants([dict(d) for d in reader])
#        for row in reader:
#            print(row['AccountId'])
    #https://alexharv074.github.io/2019/03/02/introduction-to-sam-part-i-using-the-sam-cli.html
    #https://docs.pytest.org/en/stable/assert.html
    assert len(ret) == 1

def test_get_dictdata(eventBridgeEvent, mocker):
    #print(eventBridgeEvent)
    ret = app.get_dictdata(eventBridgeEvent)
    #print(ret)
    assert ret[0]['AccountId'] == '111111111111'
