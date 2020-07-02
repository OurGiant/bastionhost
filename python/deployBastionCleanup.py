import argparse
import os
import sys
from io import BytesIO
from zipfile import ZipFile

import boto3
import yaml
from baseOperations import baseOperations

# get running instances in a running state longer than 4 hours
parser = argparse.ArgumentParser()
parser.add_argument("--env", help="environment specific stack tag")
parser.add_argument("--config", help="Config file with extra parameters")

runtype = "local"

if len(sys.argv) == 1:
    print("Arguments required")
    parser.print_help()
    exit(1)
else:
    args = parser.parse_args()

if args.env is not None:
    runTimeEnv = args.env
else:
    runTimeEnv = "leach"

if args.config is None:
    print("Config File required")
    parser.print_help()
    exit(1)
else:
    configfile = args.config
    with open(configfile, 'r') as bastionconfig:
        config = yaml.load(bastionconfig, Loader=yaml.FullLoader)
    bastionconfig.close()
    monitorARN = config['config'][runTimeEnv]['monitorARN']
    awsApplicationProfile = config['config'][runTimeEnv]['ApplicationProfile']
    MaxBastionRuntime = config['config'][runTimeEnv]['MaxBastionRuntime']
    stackTags = config['config']['Tags']


base = baseOperations(awsApplicationProfile,runtype)

session = boto3.Session(profile_name=awsApplicationProfile, region_name='us-east-1')

def createLambdaStack(session, StackName, templateName, MonitoringArn, MaxBastionRuntime, stackTags):
    cf = session.client('cloudformation')
    TemplateBody = base.readTemplate(templateName)
    create_stack = cf.create_stack(
        StackName=StackName,
        TemplateBody=TemplateBody,
        Parameters=[
            {
                'ParameterKey': 'MaxBastionRuntime',
                'ParameterValue': str(MaxBastionRuntime),
                'UsePreviousValue': True
            },
            {
                'ParameterKey': 'MonitoringArn',
                'ParameterValue': MonitoringArn,
                'UsePreviousValue': True
            },
        ],
        TimeoutInMinutes=20,
        NotificationARNs=[
            MonitoringArn
        ],
        Capabilities=[
            'CAPABILITY_IAM',
            'CAPABILITY_NAMED_IAM'
        ],
        OnFailure='ROLLBACK',
        Tags=stackTags,
        ClientRequestToken='string',
        EnableTerminationProtection=False
    )

    return create_stack.get("StackId")

def createLambdaZip():
    lamdaSource = [ '../python/bastionCleanup.py', '../python/ec2Operations.py', '../python/snsOperations.py', '../python/keypairOperations.py','../python/baseOperations.py']
    zipIO = BytesIO()
    with ZipFile(zipIO, 'a') as lambdaZip:
        for file in lamdaSource:
            print(f'Adding {file}')
            lambdaZip.write(file,os.path.basename(file))
    zipIO.seek(0)
    return zipIO.read()

def deployLamdba(session):
    lmbclnt = session.client('lambda')
    lmbclnt.update_function_code(
        FunctionName='BastionCleanupHostsAndKeys',
        ZipFile=createLambdaZip(),
        Publish=True
    )

templateName = '../templates/bastionCleanup.yaml'
StackName = "BastionCleanup-"+runTimeEnv
stack_status, stackId = base.getStacks(StackName)
if stack_status == "NEW":
    stackId = createLambdaStack(session, StackName,  templateName, monitorARN, MaxBastionRuntime, stackTags)
base.checkDeployStatus(StackName)
if stackId is not None:
    deployLamdba(session)
