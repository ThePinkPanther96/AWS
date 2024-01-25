from time import sleep
import boto3
import json
from colorama import Fore
import sys


with open('config.json', 'r') as f:
    config = json.load(f)

access_key = config["access_key"]
secret_access_key = config["secret_access_key"]
region = config["region"]
name_list = config["id_list"]

ec2 = boto3.client('ec2',
                   aws_access_key_id=access_key,
                   aws_secret_access_key=secret_access_key, 
                   region_name=region)


def ec2_status(names) -> list:
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': names}
        ]
    )
    if 'Reservations' in response:
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                state = instance['State']['Name']
                if state == 'running':
                    return True 
        return False


def start_ec2(names) -> list:
    try:
        for name in names:
            response = ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [name]}
                ]
            )
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    result = ec2_status([name])

                    if result is False:
                        print(Fore.YELLOW + f"Attempting to start {name}")
                        response = ec2.start_instances(InstanceIds=[instance['InstanceId']])
                        print(Fore.GREEN + f"{name} was started")
                    else:
                        print(Fore.LIGHTWHITE_EX + f"{name} is already working")
    
    except Exception as Error: 
        print(Fore.RED + f"Unexpected {Error=}, {type(Error)=}")
        raise


def stop_ec2(names) -> list:
    try:
        for name in names:
            response = ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [name]}
                ]
            )
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    result = ec2_status([name])
                    
                    if result is True:
                        print(Fore.YELLOW + f"Attempting to stop {name}")
                        response = ec2.stop_instances(InstanceIds=[instance['InstanceId']])
                        print(Fore.GREEN + f"{name} stoped")
                    else:
                        print(Fore.LIGHTWHITE_EX + f"{name} is already off")
    
    except Exception as Error: 
        print(Fore.RED + f"Unexpected {Error=}, {type(Error)=}")
        raise


def main():
    main_menu = (
    f"""{Fore.BLUE}Welcome!
    {Fore.WHITE}Please choose an option:
    {Fore.WHITE}1. Turn on EC2
    {Fore.WHITE}2. Turn off EC2

    {Fore.WHITE}4. Quit
    """ )
    while True:
        try:
            user_input = int(input(f"{main_menu}"))
        except (ValueError, TypeError):
            print(Fore.RED + f"Invalid Input! Please Enter a Valid Option From The Menu!")
            sleep(1.5)
            continue
        if user_input not in [1, 2, 3, 4]:
            print(Fore.RED + f"Invalid Input! Please Enter a Valid Option From The Menu!")
            sleep(1.5)
            continue

        if user_input == 1:
            while True:
                try:
                    print(Fore.CYAN + f"\n{name_list}\n")
                    selected_values_str = input(Fore.WHITE + "Enter values to select (comma-separated): ")
                    selected_values_list = [str(value.strip()) for value in selected_values_str.split(',')]
                    selected_values = [x for x in name_list if x in selected_values_list]
                    start_ec2(selected_values)
                    if selected_values_str not in name_list:
                        print(Fore.RED + f"Invalid Input! Please Enter a Valid Option From The List")
                        continue
                    else:
                        sleep(1.5)
                        user_input = int(input(f"{main_menu}"))
                        break
                except Exception as Error:
                    print(Fore.RED + f"Unexpected {Error=}, {type(Error)=}")
        
        if user_input == 2:
            while True:
                try:
                    print(Fore.CYAN + f"\n{name_list}\n")
                    selected_values_str = input(Fore.WHITE + "Enter values to select (comma-separated): ")
                    selected_values_list = [str(value.strip()) for value in selected_values_str.split(',')]
                    selected_values = [x for x in name_list if x in selected_values_list]
                    stop_ec2(selected_values)
                    if selected_values_str not in name_list:
                        print(Fore.RED + f"Invalid Input! Please Enter a Valid Option From The List")
                        continue
                    else:
                        sleep(1.5)
                        user_input = int(input(f"{main_menu}"))
                        break
                except Exception as Error:
                    print(Fore.RED + f"Unexpected {Error=}, {type(Error)=}")
           
        if user_input == 4:
            print("Logging out...")
            sleep(1)
            sys.exit(0)


if __name__ == "__main__":
    main()
