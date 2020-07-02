import boto3
import stat
import socket


class ec2Operations():

    def __init__(self,awsprofile,runtype):
        if runtype == "local":
            self.session = boto3.Session(profile_name=awsprofile, region_name='us-east-1')
        else:
            self.session = boto3.Session()
        self.EC2 = self.session.client('ec2')

    def launchInstance(self, SubnetID, KeyName, BastianSecurityGroups, IamInstanceProfile):
        AMI = 'ami-0a887e401f7654935'
        INSTANCE_TYPE = 't2.micro'
        BastionHostName = KeyName
        init_script = """#!/bin/bash
#sudo yum -y update
echo "trap 'sudo init 0' 0" | sudo tee -a /etc/profile
"""
        instance = self.EC2.run_instances(

            SubnetId=SubnetID,
            ImageId=AMI,
            KeyName=KeyName,
            InstanceType=INSTANCE_TYPE,
            InstanceInitiatedShutdownBehavior='terminate',
            UserData=init_script,
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=BastianSecurityGroups,
            IamInstanceProfile={
                'Name': IamInstanceProfile
            },
            Monitoring={
                'Enabled': False
            },
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Department Name',
                            'Value': 'Internet Operations'
                        },
                        {
                            'Key': 'Department Number',
                            'Value': '5921'
                        },
                        {
                            'Key': 'Name',
                            'Value': BastionHostName
                        },
                    ]
                },
            ],
        )

        instance_id = instance['Instances'][0]['InstanceId']

        return instance_id

    def getInstanceInformation(self, InstanceId, instanceType):
        instance = self.EC2.describe_instances(
            InstanceIds=[
                InstanceId
            ]
        )
        if instanceType == 'public':
            instance_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
            instance_name = instance['Reservations'][0]['Instances'][0]['Tags'][2]['Value']
            instance_dns = instance['Reservations'][0]['Instances'][0]['PublicDnsName']
        else:
            instance_ip = instance['Reservations'][0]['Instances'][0]['PrivateIpAddress']
            instance_dns = instance['Reservations'][0]['Instances'][0]['PrivateDnsName']
            instance_name = instance['Reservations'][0]['Instances'][0]['Tags'][2]['Value']



        return instance_ip, instance_dns, instance_name

    def getAllInstance(self, PrivateSubnetIds):
        instances = self.EC2.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': [
                        'running',
                    ]
                },
                {
                    'Name': 'subnet-id',
                    'Values': PrivateSubnetIds
                },
            ]
        )
        return instances

    def GetInstanceState(self, InstanceId):
        waiter = self.EC2.get_waiter('instance_running')
        waiter.wait(
            InstanceIds=[InstanceId],
            DryRun=False,
            WaiterConfig={
                'Delay': 6,
                'MaxAttemps': 10
            }
        )

    def TerminateInstance(self, InstanceId):
        self.EC2.terminate_instances(
            InstanceIds=[
                InstanceId
            ]
        )
        waiter = self.EC2.get_waiter('instance_terminated')
        waiter.wait(
            InstanceIds=[InstanceId],
            DryRun=False,
            WaiterConfig={
                'Delay': 6,
                'MaxAttemps': 10
            }
        )

    def SendAppEC2SSHKey(self, keyfile, bastionhost, farhostkeyfile):
        import paramiko
        username = 'ec2-user'
        last = len(farhostkeyfile.split('/', 100)) - 1
        destination_farhostkeyfile = '/home/' + username + '/.ssh/' + farhostkeyfile.split('/', 100)[last]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(bastionhost, username=username, key_filename=keyfile, banner_timeout=30, auth_timeout=30,
                        timeout=30)
        except (paramiko.SSHException, socket.error) as sshException:
            print("Unable to establish SSH connection: %s" % sshException)
            pass
        if ssh._transport != None:
            sftp = ssh.open_sftp()
            sftp.sshclient = ssh
            sftp.put(farhostkeyfile, destination_farhostkeyfile)
            sftp.chmod(destination_farhostkeyfile, stat.S_IRUSR | stat.S_IWUSR)
            sftp.close()
            ssh.close()

    def LongRunningBastionHosts(self):
        bastions = self.EC2.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': [
                        'running',
                    ]
                },
                {
                    'Name': 'tag:Name',
                    'Values': [
                        'bastion*',
                    ]
                },
            ]
        )
        return bastions
