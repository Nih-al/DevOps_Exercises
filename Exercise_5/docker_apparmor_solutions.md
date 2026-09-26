# Docker Security with AppArmor and Python — Solutions and Q&A

## 1. Objective

Build and run a simple Flask web application in a Docker container, apply an AppArmor profile where supported, and use the Docker SDK for Python to manage and test the container.

> **Environment note:** These steps assume Ubuntu with Docker Engine and an active AppArmor-enabled Linux kernel. If Ubuntu is running under WSL2 while Docker is provided by Docker Desktop, a custom profile created inside the Ubuntu distribution may not be available to Docker Desktop's daemon. Verify AppArmor support before relying on security tests.

## 2. Flask application

Create a project directory:

```bash
mkdir -p ~/docker-lab
cd ~/docker-lab
```

Create `app.py`:

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, this is a secure Flask application running inside a Docker container!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash coreutils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir Flask

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
```

Build the image:

```bash
docker build -t flask-apparmor .
```

Run the container:

```bash
docker run -d --name flask-test -p 5000:5000 flask-apparmor
```

Open [http://localhost:5000](http://localhost:5000) in a browser. The expected page is shown below.

## 3. Browser result

![Flask application running in the browser](./Final.png)

Expected text:

> Hello, this is a secure Flask application running inside a Docker container!

The screenshot demonstrates that the Flask application responds on port 5000. By itself, it does **not** prove that an AppArmor profile is active or enforcing restrictions.

## 4. AppArmor setup and profile

Install AppArmor utilities on Ubuntu:

```bash
sudo apt update
sudo apt install apparmor apparmor-utils
```

Check whether AppArmor is active:

```bash
sudo aa-status
docker info | grep -i apparmor
```

If AppArmor is unavailable or inactive, resolve the Linux/kernel or Docker-engine configuration first. Installing the package alone does not enable kernel support.

Create the profile:

```bash
sudo nano /etc/apparmor.d/flask-apparmor
```

Paste this **starting lab profile**:

```text
#include <tunables/global>

profile flask-apparmor flags=(attach_disconnected,mediate_deleted) {
    #include <abstractions/base>

    network inet stream,

    # Allow file access needed by the application and runtime.
    file,

    # Deny reading sensitive account files.
    deny /etc/shadow r,
    deny /etc/gshadow r,

    # Deny writes to selected system locations.
    deny /etc/** w,
    deny /var/** w,

    # Deny system administration capability.
    deny capability sys_admin,
}
```

Save in Nano with **Ctrl+O**, press **Enter**, then **Ctrl+X**.

Load the profile:

```bash
sudo apparmor_parser -r -W /etc/apparmor.d/flask-apparmor
```

Check that the profile is loaded:

```bash
sudo aa-status
```

Run the container with the profile:

```bash
docker rm -f flask-test 2>/dev/null || true
docker run -d --name flask-test \
  --security-opt apparmor=flask-apparmor \
  -p 5000:5000 flask-apparmor
```

Verify:

```bash
docker ps
docker logs flask-test
```

Then revisit [http://localhost:5000](http://localhost:5000).

**Important:** This is a lab example, not a production-ready security policy. The broad `file,` rule allows general file access before explicit deny rules are applied. AppArmor deny rules take precedence, but effects must be tested in the actual Linux environment. Do not claim that restrictions worked unless the tests confirm it.

## 5. Troubleshooting: container name already in use

Error:

```text
Conflict. The container name "/flask-test" is already in use
```

Docker already has a container with that name. Start it:

```bash
docker start flask-test
```

Or remove and recreate it:

```bash
docker rm -f flask-test
docker run -d --name flask-test -p 5000:5000 flask-apparmor
```

Removing a container does not remove the image. To apply the custom profile, include `--security-opt apparmor=flask-apparmor` in the new `docker run` command.

## 6. Use the Docker SDK for Python

Install dependencies in a virtual environment:

```bash
sudo apt update
sudo apt install python3-pip python3-venv -y

mkdir -p ~/docker-lab
cd ~/docker-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install docker
```

Verify the SDK is available in the active environment:

```bash
python -c "import docker; print(docker.__version__)"
```

If `ModuleNotFoundError: No module named 'docker'` occurs, activate `.venv` and install the package using the same interpreter that runs the script:

```bash
source ~/docker-lab/.venv/bin/activate
python -m pip install docker
python -c "import docker; print(docker.__version__)"
```

Create `test_docker.py`:

```python
import docker

client = docker.from_env()
client.ping()

image, build_logs = client.images.build(path=".", tag="flask-apparmor")
print(f"Built image: {image.tags}")

# Remove an old container with the same name, if present.
try:
    client.containers.get("flask-sdk-test").remove(force=True)
except docker.errors.NotFound:
    pass

# The custom profile must already be loaded on the Docker host.
container = client.containers.run(
    "flask-apparmor",
    name="flask-sdk-test",
    detach=True,
    ports={"5000/tcp": 5001},
    security_opt=["apparmor=flask-apparmor"],
)

print(f"Started container: {container.name}")
print("Open http://localhost:5001 to test the application.")

container.reload()
print("Configured security options:",
      container.attrs["HostConfig"].get("SecurityOpt"))

# Try to read a file explicitly denied by the profile.
exit_code, output = container.exec_run(["cat", "/etc/shadow"])
print("Sensitive-file test exit code:", exit_code)
print(output.decode(errors="replace"))

# The container remains available for browser testing and inspection.
```

Run it from `~/docker-lab` while the virtual environment is active:

```bash
python test_docker.py
```

This script maps container port 5000 to host port 5001 so it can run alongside a container already using port 5000. If the Docker host cannot find or use the custom AppArmor profile, container creation will fail. Fix the environment rather than removing the security option and claiming AppArmor was tested.

When finished, stop and remove the SDK-created container:

```bash
docker rm -f flask-sdk-test
```

## 7. Useful verification commands

```bash
# Running containers
docker ps

# All containers, including stopped ones
docker ps -a

# Application logs
docker logs flask-test

# Inspect the selected AppArmor security option
docker inspect flask-test --format '{{json .HostConfig.SecurityOpt}}'

# AppArmor status on the Linux host
sudo aa-status
```

## 8. Questions and answers (Q&A)

### Q1. What is Docker?

Docker is a platform for building and running applications in containers. Containers package an application and its dependencies while sharing the host operating-system kernel.

### Q2. What is AppArmor?

AppArmor is a Linux security module that restricts what programs can access or do using per-program security profiles.

### Q3. Why use AppArmor with Docker?

It adds an access-control layer to help limit a container process's actions if the application is compromised. It complements, rather than replaces, other container security measures.

### Q4. What does `--security-opt apparmor=flask-apparmor` do?

It asks Docker to run the container under the loaded AppArmor profile named `flask-apparmor`. The Docker host must support AppArmor and have that profile loaded.

### Q5. What does `deny /etc/shadow r,` mean?

It denies read access to `/etc/shadow` for processes confined by that profile. The rule must be loaded and enforced for the denial to take effect.

### Q6. What does `deny capability sys_admin,` do?

It denies the Linux `sys_admin` capability to the confined process. This capability is powerful, and denying it is one part of reducing privilege.

### Q7. Why did Docker report that `/flask-test` was already in use?

Container names must be unique. Start the existing container or remove it before creating another container with the same name.

### Q8. Why did Python report `No module named pip`?

The Python environment did not have pip installed. Installing Ubuntu's `python3-pip` package provides pip for the system Python; a virtual environment can then isolate project dependencies.

### Q9. Why did `import docker` fail?

The Docker SDK package was not installed in the Python environment executing the script, or the script was run without activating the virtual environment. Use `python -m pip install docker` with the same `python` interpreter used to run the script.

### Q10. Does seeing the Flask page prove AppArmor is working?

No. It proves that the web application is reachable. Check the Docker security options and host AppArmor status, then run a test for a resource explicitly denied by the profile.

### Q11. Does installing Ubuntu through WSL dual-boot the PC?

No. WSL runs a Linux environment within Windows. However, custom AppArmor profiles created inside a WSL distribution may not be available to a Docker daemon running inside Docker Desktop's separate Linux environment.

### Q12. What does the Docker SDK do?

The Docker SDK for Python lets Python programs communicate with the Docker daemon to build images, create and manage containers, inspect configuration, and execute commands inside containers.

## 9. Conclusion

The Flask app was successfully opened in a browser at `localhost:5000`, as shown in the screenshot. The remaining security objective is to verify that Docker actually applies the intended AppArmor profile and that denied operations fail. Record the output of the AppArmor status and restriction tests as evidence; do not infer enforcement from the successful web page alone.
