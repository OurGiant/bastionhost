import boto3

class snsOperations():

    def __init__(self,awsprofile,runtype):
        if runtype == "local":
            self.session = boto3.Session(profile_name=awsprofile, region_name='us-east-1')
        else:
            self.session = boto3.Session()
        self.sns = self.session.client('sns')



    def publishSNS(self,monitorARN,Message,Subject):
        self.sns.publish(
            TopicArn=monitorARN,
            Message=Message,
            Subject=Subject
        )