"""
This script allow you to deploy a long-running docker container automatically on a DO droplet.
DO already has a service that allows you to deploy a docker container on a droplet, but it is costly for long-running applications.
This script allows you to deploy a docker container on any small droplet for a fraction of the cost.
"""
import click
from digitalocean import (
    list_droplets as ls_droplets,
    create_droplet as cr_droplet,
    delete_droplet as dl_droplet,
    list_ssh_keys as ls_keys,
    add_ssh_key as add_key,
)
from utils import check_if_key_exists, generate_key
from yaspin import yaspin
import os

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
    with yaspin(text="Ensuring key exists") as spinner:
        if not check_if_key_exists("dodocker"):
            spinner.write("Key does not exist")
            spinner.write("Generating key")
            generate_key("dodocker")
            with open("keys/dodocker.pub", "r") as f:
                add_key("dodocker", f.read())
            spinner.ok("✅ ")
        else:
            spinner.ok("✅ ")
    # TODO: list ssh keys, find one we have the private key for, use that to create the droplet
    with yaspin(text="Creating droplet") as spinner:
        cr_droplet()
        spinner.ok("✅ ")


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
    os.system(f"ssh root@{droplet_ip}")


# CLI GROUPS #


@click.group("delete")
def delete():
    pass


delete.add_command(delete_droplet)


@click.group("create")
def create():
    pass


create.add_command(create_droplet)


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

if __name__ == "__main__":
    cli()
