# Multi-Node Kubernetes Cluster with Multiple Applications and Replicasets

## Objective

Deploy two Flask applications on a three-node Minikube cluster:

- **Product Catalog (AppA):** 2 replicas.
- **Shopping Cart (AppB):** 3 replicas.
- Expose both applications through Kubernetes Services.
- Use pod anti-affinity so replicas of each application run on separate nodes.

## Prerequisites

- Docker is installed and running.
- Minikube and `kubectl` are installed.
- Commands are run from Ubuntu/WSL or a Linux terminal with access to Docker.
- Do not run Minikube's Docker driver as root unless your environment specifically requires it.

## Step 1: Clean up an existing Minikube cluster (optional)

Only do this if you are sure you do not need the existing cluster or its workloads:

```bash
minikube stop
minikube delete
```

## Step 2: Create a three-node Minikube cluster

```bash
minikube start --nodes 3 -p devops-multinode --driver=docker
```

Check the nodes:

```bash
kubectl --context=devops-multinode get nodes
```

All three nodes should reach `Ready`. If needed, set the active context:

```bash
kubectl config use-context devops-multinode
```

> The exercise source mentions `--force` for root-run Minikube. Prefer running the Docker driver as a normal user; use `--force` only if your setup specifically requires it.

## Step 3: Enable the registry add-on

```bash
minikube -p devops-multinode addons enable registry
minikube -p devops-multinode addons list
```

For this solution, images are loaded directly into Minikube using `minikube image load`; pushing to the registry is not required.

## Step 4: Create the project directory

```bash
mkdir -p ~/k8s-multinode
cd ~/k8s-multinode
```

Create these files:

```text
k8s-multinode/
├── product_catalog.py
├── shopping_cart.py
├── Dockerfile.product
├── Dockerfile.shopping
├── product_catalog_deployment.yaml
├── shopping_cart_deployment.yaml
├── product_catalog_service.yaml
└── shopping_cart_service.yaml
```

### 4.1 Product Catalog application

Create `product_catalog.py`:

```python
from flask import Flask, jsonify

app = Flask(__name__)

products = [
    {"id": 1, "name": "Laptop", "price": 1200},
    {"id": 2, "name": "Phone", "price": 800},
    {"id": 3, "name": "Headphones", "price": 150},
]

@app.route("/products", methods=["GET"])
def get_products():
    return jsonify(products)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
```

### 4.2 Shopping Cart application

Create `shopping_cart.py`:

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

cart = []

@app.route("/cart", methods=["GET"])
def get_cart():
    return jsonify(cart)

@app.route("/cart", methods=["POST"])
def add_to_cart():
    item = request.get_json(silent=True)

    if not isinstance(item, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    cart.append(item)
    return jsonify(cart), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
```

The cart is stored in memory for demonstration. Each replica has its own cart list, so replicas do not share cart state.

## Step 5: Create Dockerfiles

### 5.1 Product Catalog Dockerfile

Create `Dockerfile.product`:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY product_catalog.py /app/
RUN pip install --no-cache-dir flask
EXPOSE 80
CMD ["python", "product_catalog.py"]
```

### 5.2 Shopping Cart Dockerfile

Create `Dockerfile.shopping`:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY shopping_cart.py /app/
RUN pip install --no-cache-dir flask
EXPOSE 80
CMD ["python", "shopping_cart.py"]
```

## Step 6: Build and load the images

Run from `~/k8s-multinode`:

```bash
docker build -t product-catalog:latest -f Dockerfile.product .
docker build -t shopping-cart:latest -f Dockerfile.shopping .
docker images
```

Load both images into Minikube:

```bash
minikube -p devops-multinode image load product-catalog:latest
minikube -p devops-multinode image load shopping-cart:latest
```

Verify image availability:

```bash
minikube -p devops-multinode ssh -- docker images
```

## Step 7: Create the Product Catalog Deployment

Create `product_catalog_deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: product-catalog
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: product-catalog
  template:
    metadata:
      labels:
        app: product-catalog
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: product-catalog
              topologyKey: kubernetes.io/hostname
      containers:
        - name: product-catalog-container
          image: product-catalog:latest
          imagePullPolicy: Never
          ports:
            - containerPort: 80
```

## Step 8: Create the Shopping Cart Deployment

Create `shopping_cart_deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shopping-cart
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: shopping-cart
  template:
    metadata:
      labels:
        app: shopping-cart
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: shopping-cart
              topologyKey: kubernetes.io/hostname
      containers:
        - name: shopping-cart-container
          image: shopping-cart:latest
          imagePullPolicy: Never
          ports:
            - containerPort: 80
```

> Both Deployments use the `default` namespace for consistency. If you use a separate namespace, create it first and put both the Deployment and Service resources for that application in that namespace.

Apply the Deployments:

```bash
kubectl apply -f product_catalog_deployment.yaml
kubectl apply -f shopping_cart_deployment.yaml
```

## Step 9: Create the Product Catalog Service

Create `product_catalog_service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: product-catalog-service
  namespace: default
spec:
  selector:
    app: product-catalog
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: NodePort
```

## Step 10: Create the Shopping Cart Service

Create `shopping_cart_service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: shopping-cart-service
  namespace: default
spec:
  selector:
    app: shopping-cart
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: NodePort
```

Apply the Services:

```bash
kubectl apply -f product_catalog_service.yaml
kubectl apply -f shopping_cart_service.yaml
```

## Step 11: Verify Deployments, pods, and Services

```bash
kubectl get deployments
kubectl get pods -o wide
kubectl get services
kubectl get endpoints
```

Expected state:

- `product-catalog`: 2 available replicas.
- `shopping-cart`: 3 available replicas.
- Five pods total, all `Running` and ready.
- Replicas of each application are placed on different nodes.
- Both Services have endpoints.

The exact pod names and node assignments will differ. A possible distribution is:

| Node | Product Catalog pods | Shopping Cart pods |
|---|---:|---:|
| `devops-multinode` | 0 | 1 |
| `devops-multinode-m02` | 1 | 1 |
| `devops-multinode-m03` | 1 | 1 |
| **Total** | **2** | **3** |

If a pod stays `Pending`, inspect it:

```bash
kubectl describe pod <pod-name>
```

Required pod anti-affinity needs one eligible node per replica of the same application.

## Step 12: Access the applications

### Option A: Minikube service command

Run each command in a separate terminal and keep the terminal open:

```bash
minikube -p devops-multinode service product-catalog-service
```

```bash
minikube -p devops-multinode service shopping-cart-service
```

Use the URLs printed by Minikube; dynamically assigned ports can differ from examples.

### Option B: Port forwarding

In one terminal:

```bash
kubectl port-forward service/product-catalog-service 8081:80
```

In another terminal:

```bash
kubectl port-forward service/shopping-cart-service 8082:80
```

Keep both commands running while testing.

## Step 13: Test the Product Catalog

Run:

```bash
curl http://127.0.0.1:8081/products
```

Expected response:

```json
[
  {"id": 1, "name": "Laptop", "price": 1200},
  {"id": 2, "name": "Phone", "price": 800},
  {"id": 3, "name": "Headphones", "price": 150}
]
```

## Step 14: Test the Shopping Cart

Retrieve the cart:

```bash
curl http://127.0.0.1:8082/cart
```

An initially empty cart returns:

```json
[]
```

Add an item:

```bash
curl -X POST http://127.0.0.1:8082/cart \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "name": "Laptop", "quantity": 1}'
```

Expected response from the replica that handles the request:

```json
[
  {"id": 1, "name": "Laptop", "quantity": 1}
]
```

Because the cart is stored in memory separately in each replica, a later request may reach a different replica and return a different cart. A shared database would be needed for consistent cart state in a real application.

## Troubleshooting

| Problem | What to check |
|---|---|
| Minikube nodes are not Ready | Run `minikube -p devops-multinode status` and inspect Docker resources. |
| Image pull errors | Confirm both images were built and loaded into the correct Minikube profile. Keep `imagePullPolicy: Never` for locally loaded images. |
| Pods remain Pending | Run `kubectl describe pod <pod-name>` and check anti-affinity scheduling events and node readiness. |
| Pods crash | Run `kubectl logs <pod-name>`. |
| Service has no endpoints | Check `kubectl get pods --show-labels` and ensure Service selectors match pod labels. |
| `curl` cannot connect | Confirm port-forward is still running and use the correct local port. |
| `kubectl` shows the wrong cluster | Run `kubectl config use-context devops-multinode`. |
| Docker permission denied | Check Docker Desktop is running and WSL integration or Docker socket permissions are configured. |

## Final Checklist

- [ ] Three Minikube nodes are Ready.
- [ ] Product Catalog has 2 available replicas.
- [ ] Shopping Cart has 3 available replicas.
- [ ] Replicas of each application are distributed across different nodes.
- [ ] Both Services have endpoints.
- [ ] `GET /products` returns the product list.
- [ ] `GET /cart` responds successfully.
- [ ] `POST /cart` accepts an item.

## Result

Two Flask applications were containerized and deployed on a three-node Minikube cluster. Kubernetes Deployments maintain two Product Catalog replicas and three Shopping Cart replicas, pod anti-affinity spreads replicas across nodes, and Services expose the applications for testing.

## Cleanup (optional)

Stop the cluster but preserve it:

```bash
minikube -p devops-multinode stop
```

Delete the cluster and its resources:

```bash
minikube -p devops-multinode delete
```
