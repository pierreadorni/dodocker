"""
This script allow you to deploy a long-running docker container automatically on a DO droplet.
DO already has a service that allows you to deploy a docker container on a droplet, but it is costly for long-running applications.
This script allows you to deploy a docker container on any small droplet for a fraction of the cost.
"""
import time

import click
import paramiko

from digitalocean import (
    list_droplets as ls_droplets,
    create_droplet as cr_droplet,
    delete_droplet as dl_droplet,
    list_ssh_keys as ls_keys,
    add_ssh_key as add_key,
    delete_ssh_key as del_key,
)
from utils import check_if_key_exists, generate_key
from yaspin import yaspin
import os
from dodocker import check_if_docker_is_installed, install_docker, _create_droplet


# CLI COMMANDS #


@click.command()
@click.argument("image_name")
def deploy(image_name):
    print(f"Deploying {image_name} on a droplet")


@click.command("droplets")
def list_droplets():
    droplets = ls_droplets()
    if len(droplets) == 0:
        print("No droplets found")
        return
    for droplet in droplets:
        if droplet["status"] == "active":
            print(f"🟢 {droplet['name']} ({droplet['networks']['v4'][0]['ip_address']})")
        elif droplet["status"] == "off":
            print(f"🔴 {droplet['name']} (off)")
        elif droplet["status"] == "new":
            print(f"🟡 {droplet['name']} (starting up)")


@click.command("deployments")
def list_deployments():
    print("Listing all deployments")


@click.command("keys")
def list_keys():
    keys = ls_keys()
    if len(keys) == 0:
        print("No keys found")
        return
    for key in keys:
        print(f"{key['name']} ({key['fingerprint']})")


@click.command("droplet")
def create_droplet():
    _create_droplet()


@click.command("droplet")
@click.argument("name")
def delete_droplet(name):
    with yaspin(text="Deleting droplet") as spinner:
        dl_droplet(name)
        spinner.ok("✅ ")


@click.command("ssh")
@click.argument("name")
def ssh_into_droplet(name):
    droplets = ls_droplets()
    droplet_ip = None
    for droplet in droplets:
        if droplet["name"] == name and droplet["status"] == "active":
            droplet_ip = droplet["networks"]["v4"][0]["ip_address"]
            break
    if droplet_ip is None:
        print("Droplet not found")
        return
    os.system(f"ssh root@{droplet_ip} -i keys/dodocker.pem")


@click.command("deployment")
@click.argument("image")
@click.option("--ports", "-p", multiple=True)
def create_deployment(image, ports):
    """Deploy a docker image on a droplet"""
    with yaspin(text="Searching for a host droplet") as spinner:
        # search for a ready droplet
        droplet_ip = None
        droplet_is_booting = False
        while droplet_ip is None:
            droplets = ls_droplets()
            for droplet in droplets:
                if droplet["status"] == "active":
                    droplet_ip = droplet["networks"]["v4"][0]["ip_address"]
                    break
                elif droplet["status"] == "new":
                    droplet_is_booting = True
                    break
            if droplet_ip is None and droplet_is_booting:
                spinner.text = "Waiting for droplet to boot"
                time.sleep(5)
                continue
            elif droplet_ip is None and not droplet_is_booting:
                spinner.text = "No droplets found, creating one"
                _create_droplet()
                droplet_is_booting = True

        # check if docker is installed
        spinner.text = "Checking if docker is installed"
        if not check_if_docker_is_installed(droplet_ip):
            spinner.text = "Installing docker"
            install_docker(droplet_ip, spinner=spinner)

        spinner.text = f"Deploying docker image {image}"
        # run docker image on droplet
        ssh = paramiko.SSHClient()
        k = paramiko.RSAKey.from_private_key_file("keys/dodocker.pem")
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=droplet_ip, username="root", pkey=k)
        cmd = f"docker run -d"
        for port in ports:
            cmd += f" -p {port}:{port}"
        cmd += f" {image}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        if stdout.channel.recv_exit_status() != 0:
            spinner.fail("❌ ")
            print("Failed to deploy docker image")
            print(stderr.read().decode())
        else:
            spinner.ok("✅ ")
            print(f"Successfully deployed docker image on {droplet_ip}")


# CLI GROUPS #


@click.group("delete")
def delete():
    pass


delete.add_command(delete_droplet)


@click.group("create")
def create():
    pass


create.add_command(create_droplet)
create.add_command(create_deployment)


@click.group("list")
def list_():
    pass


list_.add_command(list_droplets)
list_.add_command(list_deployments)
list_.add_command(list_keys)


@click.group()
def cli():
    pass


cli.add_command(deploy)
cli.add_command(list_)
cli.add_command(create)
cli.add_command(delete)
cli.add_command(ssh_into_droplet)

if __name__ == "__main__":
    cli()
