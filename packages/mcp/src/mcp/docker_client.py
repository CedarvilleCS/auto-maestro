"""docker_client.py

This module provides a low-level Docker SDK wrapper for container operations.

Key Features:
- List running containers with their IDs, names, statuses, and IPs.
- Execute commands inside containers and return decoded output.
- Ping targets and resolve container IP addresses.

"""

import docker

client = docker.DockerClient(base_url="unix:///var/run/docker.sock")


def list_containers():
    containers = client.containers.list()
    result = []

    for c in containers:
        networks = c.attrs["NetworkSettings"]["Networks"]
        ip_map = {net: networks[net]["IPAddress"] for net in networks}
        result.append(
            {
                "id": c.short_id,
                "name": c.name,
                "status": c.status,
                "ips": ip_map,
            }
        )

    return result


def exec_command(container: str, cmd: list[str]) -> str:
    c = client.containers.get(container)
    exec_result = c.exec_run(cmd)
    return exec_result.output.decode("utf-8")


def ping(container: str, target: str) -> str:
    c = client.containers.get(container)
    exec_result = c.exec_run(["ping", "-c", "3", target])
    return exec_result.output.decode("utf-8")


def resolve_container_ip(container: str) -> str:
    c = client.containers.get(container)
    networks = c.attrs["NetworkSettings"]["Networks"]
    return list(networks.values())[0]["IPAddress"]
