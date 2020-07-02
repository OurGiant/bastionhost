import boto3
from botocore.client import ClientError
import time
import json
import uuid


class baseOperations():

    def __init__(self,awsprofile,runtype):
        if runtype == "local":
            self.session = boto3.Session(profile_name=awsprofile, region_name='us-east-1')
        else:
            self.session = boto3.Session()

    def readTemplate(self, templateName):
        cf = self.session.client('cloudformation')
        with open(templateName, mode='r') as TemplateBody:
            TemplateBodyText = TemplateBody.read()
        TemplateBody.close()
        try:
            cf.validate_template(
                TemplateBody=TemplateBodyText,
            )
        except ClientError as e:
            print(
                f'There is a problem with your template {templateName}. Please check it for errors.\n\nError Message:\n{str(e)}')
            exit(1)
        return TemplateBodyText

    def getStackOutput(self, StackName,readmefile):
        cf = self.session.client('cloudformation')
        readme = open(readmefile, "a")
        readme.write("\n## stack:" + StackName + "\n")
        readme.write('### EXPORTS' + "\n")
        try:
            response = cf.describe_stacks(StackName=StackName)
            stack_info = response['Stacks']
            stack_outputs = stack_info[0]['Outputs']
            sc = 0
            while sc < len(stack_outputs):
                OutputKey = stack_outputs[sc]['OutputKey']
                OutputValue = stack_outputs[sc]['OutputValue']
                ExportName = stack_outputs[sc]['ExportName']
                readme.write(
                    "\n#### " + OutputKey + "\n- OutputValue is " + OutputValue + "\n- ExportName is " + ExportName)
                sc += 1
        except :
            pass
        readme.write("\n")
        readme.close()

    def getStacks(self, StackName):
        cf = self.session.client('cloudformation')
        try:
            response = cf.describe_stacks(StackName=StackName)
            stack_info = response['Stacks']
            stack_status = stack_info[0]['StackStatus']
            stack_id = stack_info[0]['StackId']
        except:
            stack_id = 0
            stack_status = 'NEW'
            pass
        return str(stack_status), str(stack_id)

    def checkDeployStatus(self, StackName):
        cf = self.session.client('cloudformation')
        stack_status = 'NEW'
        while stack_status != 'CREATE_COMPLETE':
            stack_status, stack_id = self.getStacks(StackName)
            print(f'Stack: {StackName} Status: {stack_status}')
            time.sleep(5)
            if stack_status == 'ROLLBACK_COMPLETE':
                events = cf.describe_stack_events(StackName=StackName)
                StackEvents = events['StackEvents']
                events_txt = json.dumps(StackEvents)
                rollbackfile = 'rollback_messages-' + StackName + '.json'
                with open(rollbackfile, 'w') as output:
                    output.write(events_txt)
                output.close()
                cf.delete_stack(StackName=StackName)
                stack_status = self.getStacks(StackName)
                while stack_status == 'DELETE_IN_PROGRESS':
                    time.sleep(5)
                stack_status = 'STACK_DELETE'
        return stack_status, stack_id

    def checkDeleteStatus(self, StackName):
        cf = self.session.client('cloudformation')
        stack_status = 'CREATE_COMPLETE'
        while stack_status == 'DELETE_IN_PROGRESS':
            stack_status, stack_id = self.getStacks(StackName)
            print(f'Stack: {StackName} Status: {stack_status}')
            time.sleep(5)

    def deleteStacks(self, StackName):
        ClientRequestToken = str(uuid.uuid4()).lower()
        print(f'Deleting stack {StackName}')
        cf = self.session.client('cloudformation')
        cf.delete_stack(
            StackName=StackName,
            ClientRequestToken=ClientRequestToken
        )
        self.checkDeleteStatus(StackName)