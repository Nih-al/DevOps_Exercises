import docker

client = docker.from_env()

container = client.containers.run(
    "flask-apparmor",
    name="flask-security-test",
    security_opt=["apparmor=flask-apparmor"],
    detach=True,
)

try:
    for command in [
        ["cat", "/etc/shadow"],
        ["sh", "-c", "echo test >> /etc/test-apparmor"],
    ]:
        result = container.exec_run(command)
        print("Command:", command)
        print("Exit code:", result.exit_code)
        print(result.output.decode(errors="replace"))
finally:
    container.stop()
    container.remove()