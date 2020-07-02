import boto3
import os

def main(event,context):
    awsprofile = 'drr-qa'
    monitorARN = os.environ['monitorARN']
    env = os.environ['ENV']
    if env is not 'AWS':
        session = boto3.Session(profile_name=awsprofile, region_name='us-east-1')
    else:
        session = boto3.Session()

    client_ec2 = session.client('ec2')
    client_sns = session.client('sns')

    bastionKeys = client_ec2.describe_key_pairs(
        Filters=[
            {
                'Name': 'key-name',
                'Values': [
                    'bastion*'
                ]
            }
        ]
    )
    if len(bastionKeys['KeyPairs']) > 0:
        for key in bastionKeys['KeyPairs']:
            keyName = key['KeyName']
            print(f'Delete Key {keyName}')
            client_ec2.delete_key_pair(
                KeyName=keyName,
                DryRun=False
            )
            notificationSubject = "Delete Bastion Key "+keyName
            notificationMessage = "Delete Bastion Key "+keyName
            client_sns.publish(
                TopicArn=monitorARN,
                Message=notificationMessage,
                Subject=notificationSubject
            )
    else:
        print('No keys to delete')


if __name__ == '__main__':
    main("foo","bar")