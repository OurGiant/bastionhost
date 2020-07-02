import os
import stat
import uuid

import boto3


class keypairOperations():

    def __init__(self,awsprofile,runtype):
        if runtype == "local":
            self.session = boto3.Session(profile_name=awsprofile, region_name='us-east-1')
        else:
            self.session = boto3.Session()

        self.client = self.session.client('ec2')

    def CreateKeyPair(self, keyname):

        if (keyname == 'bastion'):
            keyname = keyname + '-' + str(uuid.uuid4()).lower()

        temp_key_dir = "../ssh-keys/"
        keyfile_name = temp_key_dir + keyname + '.pem'

        newKeyPair = self.client.create_key_pair(
            KeyName=keyname,
            TagSpecifications=[
                {
                    'ResourceType': 'key-pair',
                    'Tags': [
                        {
                            'Key': 'Type',
                            'Value': 'bastion'
                        },
                    ]
                },
            ]
        )

        KeyMaterial = newKeyPair['KeyMaterial']

        with open(keyfile_name, 'w') as keyfile:
            keyfile.write(KeyMaterial)

        keyfile.close()

        os.chmod(keyfile_name, stat.S_IRUSR | stat.S_IWUSR)

        return keyfile_name, keyname

    def DeleteKeyPair(self, keyname, keyfile):
        try:
            self.client.delete_key_pair(
                KeyName=keyname
            )
        except:
            pass
        try:
            os.remove(keyfile)
        except:
            pass

    def KeyPairInfo(self, keyname):
        keyInfo = self.client.describe_key_pairs(
            Filters=[
                {
                    'Name': 'key-name',
                    'Values': [
                        keyname,
                    ]
                },
            ]
        )
        if len(keyInfo['KeyPairs']) > 0:
            hasKey = 1
        else:
            hasKey = 0
        return hasKey
