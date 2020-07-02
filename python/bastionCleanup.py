import os
import sys
from datetime import datetime as dt
from datetime import timedelta

import ec2Operations
import snsOperations
import keypairOperations
from dateutil import tz


def main(event,context):

    if os.environ["ENV"] == "AWS":
        monitorARN = os.environ["MONITORARN"]
        MaxBastionRuntime = os.environ["MaxBastionRuntime"]
        runtype = "aws"
        awsApplicationProfile = "IAMRole"
    else:
        runtype = "local"
        import yaml
        import argparse
        # get running instances in a running state longer than 4 hours
        # stop instances in a running state longer than 4 hours
        # delete instances in a running state longer than 4 hours
        # delete ec2 keypairs associated with instance in a running state longer than 4 hours

        parser = argparse.ArgumentParser()
        parser.add_argument("--env", help="environment specific stack tag")
        parser.add_argument("--config", help="Config file with extra parameters")

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


    kp = keypairOperations.keypairOperations(awsApplicationProfile,runtype)
    ec2 = ec2Operations.ec2Operations(awsApplicationProfile,runtype)
    sns = snsOperations.snsOperations(awsApplicationProfile,runtype)


    launchExpiration = dt.now().astimezone(tz.UTC) - timedelta(hours=int(MaxBastionRuntime))
    print(f'Clean up bastion hosts launched prior to {launchExpiration}')

    bastions = ec2.LongRunningBastionHosts()

    if len(bastions['Reservations']) > 0:
        for bastion in bastions['Reservations']:
            launchTime = bastion['Instances'][0]['LaunchTime']
            if launchTime <= launchExpiration:
                InstanceId = bastion['Instances'][0]['InstanceId']
                keyName = bastion['Instances'][0]['KeyName']
                ec2.TerminateInstance(InstanceId)
                try:
                    kp.DeleteKeyPair(keyName,"dummy")
                except:
                    pass
                notificationSubject = "Terminating expired EC2 bastion instance and key"
                notificationMessage = "Terminating Instance "+InstanceId+" and Key "+keyName
                print(notificationMessage)
                sns.publishSNS(monitorARN,notificationSubject, notificationMessage)

if __name__ == '__main__':
    main("foo","bar")
