from time import sleep
import ec2Operations
import snsOperations
import sys
import argparse
import yaml
from prettytable import PrettyTable

runtype  = "local"

import keypairOperations

parser = argparse.ArgumentParser()
parser.add_argument("--bastionttl", help="TTL for bastion host in minutes")
parser.add_argument("--config", help="Config file with extra parameters")
parser.add_argument("--env", help="environment specific stack tag")

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
    SubnetID = config['config'][runTimeEnv]['SubnetID']
    IamInstanceProfile = config['config'][runTimeEnv]['IamInstanceProfile']
    BastianSecurityGroups = config['config'][runTimeEnv]['BastianSecurityGroups']
    awsApplicationProfile = config['config'][runTimeEnv]['ApplicationProfile']
    farhostkeyfile = config['config'][runTimeEnv]['SSHKey']
    PrivateSubnetIds = config['config'][runTimeEnv]['PrivateSubnetIds']

    try:
        bastionttl = config['config'][runTimeEnv]['BastionTTL']
    except:
        bastionttl = args.bastionttl

if int(bastionttl) > 120:
    print("The max TTL for bastion hosts is 2 hours (120 minutes)\nYour bastion host will expire in 2 hours")
    bastionttl = "120"

bastionttlSleep = int(bastionttl) * 60

kp = keypairOperations.keypairOperations(awsApplicationProfile,runtype)
ec2 = ec2Operations.ec2Operations(awsApplicationProfile,runtype)
sns = snsOperations.snsOperations(awsApplicationProfile,runtype)

# try:
print("Create temporary bastion host ssh keypair")
keynamePrefix = 'bastion'
newKeyFile, newKey = kp.CreateKeyPair(keynamePrefix)
print("Create bastion host")
instance_id = ec2.launchInstance(SubnetID, newKey, BastianSecurityGroups, IamInstanceProfile)
ec2.GetInstanceState(instance_id)
instance_ip, instance_dns, BastionHostName = ec2.getInstanceInformation(instance_id,'public')
Subject = "New Instance Notification"
Message = "New instance created with Instance ID:" + instance_id + "\nDNS Name: " + instance_dns + "\nSSH Key: " + newKeyFile + "\nInstance Name: " + BastionHostName + "\nThis instance will expire in " + str(
    bastionttl) + " minutes"
sns.publishSNS(monitorARN, Message, Subject)
print(f"Send EC2 ssh keys to bastion host {instance_ip}")
sleep(20)
ec2.SendAppEC2SSHKey(newKeyFile, instance_ip, farhostkeyfile)
print(
    f'Your new instance {BastionHostName} is ready.\n Connect to it use it like: ssh -o StrictHostKeyChecking=no -i {newKeyFile} ec2-user@{instance_dns}\n This instance has a lifetime of {str(bastionttl)} minutes after which time the instance will be terminated and the key will be deleted.')
# except:
#     print("Unable to create the instance")
#     kp.DeleteKeyPair(newKey,newKeyFile)
#     sys.exit
instancesAvailableTable = PrettyTable(['IP', 'DNS', 'Name'])
instances = ec2.getAllInstance(PrivateSubnetIds)
for instance in instances['Reservations']:
        ec2IP, ec2DNS, ec2Name = ec2.getInstanceInformation(instance['Instances'][0]['InstanceId'],'private')
        instancesAvailableTable.add_row([ec2IP, ec2DNS, ec2Name])

print(instancesAvailableTable.get_string(title="Available Instances"))
sleep(bastionttlSleep)

print("terminate bastion host")
ec2.TerminateInstance(instance_id)
print("delete temporary ssh keys")
kp.DeleteKeyPair(newKey, newKeyFile)
exit(0)
