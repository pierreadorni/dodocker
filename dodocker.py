import time

import paramiko
from yaspin import yaspin

import digitalocean

from digitalocean import (
    list_droplets as ls_droplets,
    create_droplet as cr_droplet,
    delete_droplet as dl_droplet,
    list_ssh_keys as ls_keys,
    add_ssh_key as add_key,
    delete_ssh_key as del_key,
)
from utils import check_if_key_exists, generate_key


def install_docker(droplet_ip, spinner=None):
    """installs docker on the host system"""
    cmd_list = [
        "sudo apt-get update",
        "sudo apt-get install -y ca-certificates curl gnupg",
        "sudo install -m 0755 -d /etc/apt/keyrings",
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/docker.gpg",
        "sudo chmod a+r /etc/apt/keyrings/docker.gpg",
        """echo   "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" |   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null""",
        "sudo apt-get update",
        "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
    ]
    ssh = paramiko.SSHClient()
    k = paramiko.RSAKey.from_private_key_file("keys/dodocker.pem")
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=droplet_ip, username="root", pkey=k)
    for i, cmd in enumerate(cmd_list):
        tries = 0
        if spinner is not None:
            spinner.text = f"Installing docker [{i + 1}/{len(cmd_list)}]"
        while tries < 3:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            if stdout.channel.recv_exit_status() != 0:
                tries += 1
                time.sleep(2)
            else:
                break



def check_if_docker_is_installed(droplet_ip):
    """checks if docker is installed on the host system"""
    ssh = paramiko.SSHClient()
    k = paramiko.RSAKey.from_private_key_file("keys/dodocker.pem")
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    tries = 0
    while tries < 5:
        try:
            ssh.connect(hostname=droplet_ip, username="root", pkey=k)
            break
        except paramiko.ssh_exception.NoValidConnectionsError:
            tries += 1
            time.sleep(2)
            continue
    if tries == 5:
        return False
    stdin, stdout, stderr = ssh.exec_command("docker --version")
    if stdout.channel.recv_exit_status() != 0:
        return False
    else:
        return True


def _create_droplet():
    with yaspin(text="Ensuring key exists") as spinner:
        # check if key exists upstream
        do_keys = ls_keys()
        if any(key["name"] == "dodocker" for key in do_keys) and check_if_key_exists("dodocker"):
            spinner.ok("✅ ")
        elif any(key["name"] == "dodocker" for key in do_keys) and not check_if_key_exists("dodocker"):
            spinner.write("Keys desynced, replacing key")
            del_key([key["id"] for key in do_keys if key["name"] == "dodocker"][0])

        if not check_if_key_exists("dodocker"):
            spinner.write("Key does not exist")
            spinner.write("Generating key")
            generate_key("dodocker")
            spinner.write("Adding key to DigitalOcean")
            with open("keys/dodocker.pub", "r") as f:
                add_key("dodocker", f.read())
            spinner.ok("✅ ")

    with yaspin(text="Getting key id") as spinner:
        do_keys = ls_keys()
        for key in do_keys:
            if key["name"] == "dodocker":
                key_id = key["id"]
                break
        spinner.ok("✅ ")

    with yaspin(text="Creating droplet") as spinner:
        cr_droplet(key_id)
        spinner.ok("✅ ")
