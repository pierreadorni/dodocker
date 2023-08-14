import requests
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("DIGITALOCEAN_TOKEN")

ApiError = type("ApiError", (Exception,), {})


def list_droplets():
    res = requests.get(
        "https://api.digitalocean.com/v2/droplets",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    if res.status_code != 200:
        raise ApiError(res.json())
    return res.json()["droplets"]


def create_droplet(ssh_key="dodocker"):
    with open(f"keys/{ssh_key}.pub", "r") as f:
        ssh_key = f.read()
    res = requests.post(
        "https://api.digitalocean.com/v2/droplets",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "name": f"dodocker-{uuid.uuid4()}",
            "region": "fra1",
            "size": "s-1vcpu-1gb",
            "image": "ubuntu-20-04-x64",
            "ssh_keys": [ssh_key],
        },
    )
    if res.status_code != 202:
        raise ApiError(res.json())
    return res.json()["droplet"]


def delete_droplet(droplet_name):
    droplets = list_droplets()
    droplet_id = None
    for droplet in droplets:
        if droplet["name"] == droplet_name:
            droplet_id = droplet["id"]
            break
    if droplet_id is None:
        raise ApiError(f"Droplet {droplet_name} not found")
    res = requests.delete(
        f"https://api.digitalocean.com/v2/droplets/{droplet_id}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    if res.status_code != 204:
        raise ApiError(res.json())
    return 0


def add_ssh_key(name, pem_string):
    res = requests.post(
        "https://api.digitalocean.com/v2/account/keys",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
        json={"name": name, "public_key": pem_string},
    )
    if res.status_code != 201:
        raise ApiError(res.json())
    return 0


def list_ssh_keys():
    res = requests.get(
        "https://api.digitalocean.com/v2/account/keys",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    if res.status_code != 200:
        raise ApiError(res.json())
    return res.json()["ssh_keys"]
