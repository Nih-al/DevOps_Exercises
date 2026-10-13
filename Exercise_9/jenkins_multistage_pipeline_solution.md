# Jenkins Multi-Stage Pipeline — Python Flask Application

## Objective

Create and execute a Jenkins Pipeline with multiple stages to build, test, and mock-deploy a Python Flask application.

The pipeline will:
1. Install the Python application dependencies.
2. Run unit tests.
3. Copy the application files to a mock deployment directory.
4. Report whether the pipeline succeeded or failed.

## Prerequisites

- Jenkins is running at `http://localhost:8080`.
- Docker is installed and can access the Jenkins container.
- Jenkins has the **Pipeline** and **Git** plugins installed.
- A GitHub repository is available for the project.
- The Jenkins container has Python 3, `python3-venv`, and Git installed.

## Step 1: Prepare the Jenkins container

Check the running containers from PowerShell or Ubuntu/WSL:

```bash
docker ps
```

Open a root shell in the Jenkins container (replace `jenkins` if your container has a different name):

```bash
docker exec -it -u root jenkins bash
```

Inside the container, install the required packages:

```bash
apt-get update
apt-get install -y python3 python3-pip python3-venv python3-flask git
exit
```

Verify Python and Git:

```bash
docker exec jenkins python3 --version
docker exec jenkins git --version
```

> **Note:** Packages installed inside a running container may be lost if the container is deleted and recreated. For a repeatable setup, build a custom Jenkins image with Python preinstalled.

## Step 2: Verify Jenkins plugins

1. Open `http://localhost:8080`.
2. Go to **Manage Jenkins → Plugins → Installed plugins**.
3. Search for **Pipeline** and **Git**.
4. If a required plugin is missing, install it through **Available plugins** and restart Jenkins if prompted.

## Step 3: Create the Python Flask application

Use Ubuntu/WSL or another local terminal:

```bash
mkdir -p ~/python-flask-app
cd ~/python-flask-app
git init -b main
```

Create `app.py`:

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, Jenkins Multi-Stage Pipeline!"

if __name__ == "__main__":
    app.run(debug=False)
```

Create `requirements.txt`:

```text
Flask==2.1.2
Werkzeug<3.0
```

The Werkzeug constraint avoids a compatibility issue that can occur when this older Flask release is installed with newer Werkzeug versions.

Create `test_app.py`:

```python
import unittest
from app import app


class TestApp(unittest.TestCase):
    def test_home(self):
        tester = app.test_client()
        response = tester.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data.decode("utf-8"),
            "Hello, Jenkins Multi-Stage Pipeline!"
        )


if __name__ == "__main__":
    unittest.main()
```

## Step 4: Create the Jenkinsfile

In the same project directory, create a file named exactly `Jenkinsfile` (no file extension):

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo 'Creating virtual environment and installing dependencies...'
                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Running unit tests...'
                sh '.venv/bin/python -m unittest discover -s . -p "test_*.py"'
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying application to a mock directory...'
                sh '''
                    mkdir -p "${WORKSPACE}/python-app-deploy"
                    cp app.py requirements.txt "${WORKSPACE}/python-app-deploy/"
                    test -f "${WORKSPACE}/python-app-deploy/app.py"
                    echo "Application copied successfully."
                '''
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check the stage logs.'
        }
    }
}
```

### What each stage does

- **Build:** Creates a virtual environment and installs dependencies from `requirements.txt`.
- **Test:** Runs the unit tests with Python's `unittest` framework.
- **Deploy:** Copies the application and requirements file into `${WORKSPACE}/python-app-deploy`.
- **Post actions:** Prints a success or failure message based on the pipeline result.

This version omits a long-running server stage. The unit test uses Flask's test client, so the app does not need to run as a background server for the test to pass.

## Step 5: Push the project to GitHub

Create an empty GitHub repository first. Replace `YOUR-USERNAME` with your GitHub username and use a repository you own or can write to.

```bash
cd ~/python-flask-app
git add app.py requirements.txt test_app.py Jenkinsfile
git commit -m "Add Python Flask multi-stage Jenkins pipeline"
git remote add origin https://github.com/YOUR-USERNAME/python-flask-app.git
git push -u origin main
```

If `origin` already exists, update it:

```bash
git remote set-url origin https://github.com/YOUR-USERNAME/python-flask-app.git
```

If the push is rejected because the remote contains commits that are not local, run:

```bash
git pull --rebase origin main
git push -u origin main
```

Resolve any reported conflicts before pushing. Confirm that all four files appear in the GitHub repository.

## Step 6: Create a Jenkins Pipeline job

1. Open `http://localhost:8080`.
2. Click **New Item**.
3. Enter `Python-MultiStage-Pipeline`.
4. Select **Pipeline**, then click **OK**.
5. Scroll to the **Pipeline** section.
6. Set **Definition** to `Pipeline script from SCM`.
7. Set **SCM** to `Git`.
8. Set **Repository URL** to your GitHub repository URL, for example:
   `https://github.com/YOUR-USERNAME/python-flask-app.git`
9. Set **Branch Specifier** to `*/main`.
10. Set **Script Path** to `Jenkinsfile`.
11. For a public repository, credentials can usually remain `- none -`. For a private repository, configure appropriate credentials.
12. Click **Save**.

If Git is not available in the SCM selector, verify that the Jenkins Git plugin is installed and enabled.

## Step 7: Run the pipeline

1. Open the `Python-MultiStage-Pipeline` job.
2. Click **Build Now**.
3. Open the build number.
4. Select **Console Output**.
5. Confirm that the Build, Test, and Deploy stages complete successfully.

Expected output will be similar to:

```text
Ran 1 test

OK
Application copied successfully.
Pipeline completed successfully!
Finished: SUCCESS
```

The exact logs vary by environment and package versions.

## Step 8: Verify the mock deployment

The deployment directory is inside the Jenkins job workspace:

```text
${WORKSPACE}/python-app-deploy/
├── app.py
└── requirements.txt
```

The Deploy stage checks that `app.py` exists in that directory. This is a mock deployment; it does not publish the application to an external server or make it accessible from the Windows browser.

## Troubleshooting

| Problem | Resolution |
|---|---|
| `python3: not found` | Install Python in the Jenkins container or use an agent/image that includes Python. |
| `No module named venv` | Install `python3-venv` in the Jenkins container. |
| Dependency installation fails | Review the console log for network or package-version errors. |
| Git is missing from Source Code Management | Install and enable the Jenkins Git plugin. |
| `Jenkinsfile` not found | Confirm its exact name, location, branch, and Script Path. |
| GitHub returns `403` during push | Check the account used by Git, repository ownership/write access, and token permissions. |
| Remote branch contains newer commits | Run `git pull --rebase origin main`, resolve conflicts, and push again. |
| Script cannot be found during build | Confirm the files are committed at the repository root or adjust paths in the Jenkinsfile. |

## Optional enhancement: Code Quality

Install `flake8` as part of the Build stage:

```groovy
.venv/bin/python -m pip install flake8
```

Then add this stage after **Test** and before **Deploy**:

```groovy
stage('Code Quality') {
    steps {
        echo 'Running code quality checks...'
        sh '.venv/bin/flake8 app.py test_app.py'
    }
}
```

If the code-quality stage fails, fix the reported lint issues or configure an appropriate project-specific lint policy.

## Result

The Jenkins Pipeline checks out the Python Flask project from GitHub, installs dependencies, runs a unit test, copies the application files into a mock deployment directory, and reports the final build status.
