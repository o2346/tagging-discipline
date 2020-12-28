#configservice aggregated violation transmitter - main function

from schema.aws.events.scheduledjson import Marshaller
from schema.aws.events.scheduledjson import AWSEvent
from schema.aws.events.scheduledjson import ScheduledEvent

import json
import os

#https://aws.amazon.com/premiumsupport/knowledge-center/sns-lambda-webhooks-chime-slack-teams/
#https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents.html
import urllib3
import json
http = urllib3.PoolManager()

import boto3
client = boto3.client('config')

import glob

import functools
import re

import sys

#handle NextToken, or you would have incomplete results
def select_aggregate_resource_config(Expression, ConfigurationAggregatorName, NextToken=None, current=None):

    #https://www.toptal.com/python/top-10-mistakes-that-python-programmers-make
    if current is None:
        current = {'Results': []}
    #print('current')
    #print(len(current['Results']))

    kwargs = {'NextToken': NextToken} if NextToken else {}

    try:
        page = client.select_aggregate_resource_config(
            Expression=Expression,
            ConfigurationAggregatorName=ConfigurationAggregatorName,
            **kwargs
            #Limit=2
        )
        current.get('Results').extend(page.get('Results'))
    except:
        print(sys.exc_info())
        print('Error: something is wrong. Result may possibly be incomplete')
        return current

    if page.get('NextToken') is None:
        return current
    else:
        return select_aggregate_resource_config(Expression, ConfigurationAggregatorName, page.get('NextToken'), current)

def audit(context):
    violations = []
    with open(context, 'r') as json_file:
        json_text = json.dumps(json.load(json_file))
        #https://api.slack.com/messaging/webhooks
        #https://developers.mattermost.com/integrate/incoming-webhooks/
        #http://ykng0.hatenablog.com/entry/2016/12/25/225424
        #https://gist.github.com/rantav/c096294f6f35c45155b4
        #https://slack.dev/python-slackclient/basic_usage.html

    contextObject = json.loads(json_text)
    configRuleName = contextObject['attachments'][0]['props']['rvt']['configservice']['rule']['configRuleName']
    print(configRuleName)

    #
    #Generate Summary
    #
    summary_template_location = str(os.environ['LAMBDA_TASK_ROOT'] + "/cavt/summarytemplates/" + configRuleName + '.json')
    with open(summary_template_location, 'r') as summary_template_file:
        summary_template = json.dumps(json.load(summary_template_file))

    summaryResponse = select_aggregate_resource_config(
        Expression=f'''
            SELECT
              accountId,
              COUNT(*)
            WHERE
              configuration.complianceType = 'NON_COMPLIANT'
              AND configuration.configRuleList.configRuleName = '{configRuleName}'
            GROUP BY
              accountId
        ''',
        ConfigurationAggregatorName='ConfigurationAggregator'
    )

    #for testing
    #summaryResponse['Results'] = []

    if len(summaryResponse['Results']) == 0:
        print('Excellent. There isn no Violation. Abort')
        return violations

    #for testing
    summaryResponse['Results'].extend({'{"COUNT(*)":16,"accountId":"888888888888"}'})
    summaryResponse['Results'].extend({'{"COUNT(*)":20,"accountId":"999999999999"}'})

    total = functools.reduce(lambda a,b:a+b, [ json.loads(o)['COUNT(*)'] for o in summaryResponse['Results'] ])
    #total = functools.reduce(lambda a,b :a+b, map(lambda s: s['COUNT(*)'],summaryResponse['Results']))

    print(os.environ['MaxViolationDetailsSendTo'])

    if total > int(os.environ['MaxViolationDetailsSendTo']):
        toomanyMsg = ' - **[Warning] TOO MANY violations. Ommited to report for each ones**'
    else:
        toomanyMsg = ''

    print(total)
    sumList = '\\\\n'.join( [ str(json.loads(o)['accountId'])+' '+str(json.loads(o)['COUNT(*)']) for o in summaryResponse['Results'] ] )
    #print(sumList)
    #print('\n'.join(summaryResponse['Results']))

    #print(json.dumps(result,indent=2))
    # prepare template
    summaryReportMapping = [
        summary_template,
        [ 'value.ViolationCountsByAccount', sumList ],
        [ 'value.Totalling', total ],
        [ 'value.toomanyMsg', toomanyMsg ],
    ]
    summaryItem = json.loads(functools.reduce(lambda a,b :re.sub(b[0], str(b[1]), a) ,summaryReportMapping))
    #print(json.dumps(summaryItem, indent=2))
    if total > int(os.environ['MaxViolationDetailsSendTo']):
        print('[Warning] Number of Violations has exceeded threshold. Summary only')
        violations.append(summaryItem)
        return violations

    #
    #Generate Details
    #
    #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/config.html#ConfigService.Client.select_aggregate_resource_config
    #Note: you may want to limit length for the response since enormous number of violations would have returned
    #An idea to restrict the length is here. Absent from handling NextToken and provide argument "Limit=N"
    #response = client.select_aggregate_resource_config(
    response = select_aggregate_resource_config(
        #https://github.com/awslabs/aws-config-resource-schema/blob/master/config/properties/AWS.properties.json
        #https://stackoverflow.com/a/50550283
        Expression=f'''
            SELECT
              accountId,
              awsRegion,
              configuration.targetResourceId,
              configuration.targetResourceType,
              configuration.complianceType,
              configuration.configRuleList
            WHERE
              configuration.complianceType = 'NON_COMPLIANT'
              AND configuration.configRuleList.configRuleName = '{configRuleName}'
        ''',
        ConfigurationAggregatorName='ConfigurationAggregator'
    )

    #print(response['Results'])

    for resultText in response['Results']:
        result = json.loads(resultText)
        #print('result=' + str(result))
        # prepare template
        contextTemplateObject = [
            json_text,
            [ 'accountId', result['accountId'] ],
            [ 'awsRegion', result['awsRegion'] ],
            [ 'configuration.targetResourceId', result['configuration']['targetResourceId'] ],
            [ 'configuration.targetResourceType', result['configuration']['targetResourceType'] ],
            [ 'configuration.complianceType', result['configuration']['complianceType'] ]
            #[ 'configuration.configRuleList', result['configuration']['configRuleList'] ]
        ]
        item = json.loads(functools.reduce(lambda a,b :re.sub(b[0], b[1], a) ,contextTemplateObject))
        violations.append(item)
    #https://stackoverflow.com/a/39550486

    violations.append(summaryItem)
    return violations


def lambda_handler(event, context):
    """Lambda function reacting to Scheduled events

    Parameters
    ----------
    event: dict

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
        The same input event file
    """

    #Deserialize event into strongly typed object
    awsEvent:AWSEvent = Marshaller.unmarshall(event, AWSEvent)
    detail:ScheduledEvent = awsEvent.detail

    #Execute business logic
    url = os.environ['SENDTO']
    violations = {}
    for (filename) in glob.glob(str(os.environ['LAMBDA_TASK_ROOT'] + "/cavt/rules/*.json")):
        audited = audit(filename)
        if len(audited) == 0:
            continue

        rule_context_name = os.path.splitext(os.path.basename(filename))[0]
        violations[rule_context_name]=audited
        for idx, val in enumerate(violations[rule_context_name]):
            encoded_msg = json.dumps(val).encode('utf-8')
            response = http.request('POST',url, body=encoded_msg)
            val['http_send_response'] = str(response)

    #print(json.dumps(violations, indent=2))
    #awsEvent.detail_type = violations
    awsEvent.detail_type = ''

    #Return event for further processing
    return Marshaller.marshall(awsEvent)
