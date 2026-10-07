
from prometheus_client import start_http_server, Gauge, Summary
import random
import time

total_deliveries = Gauge(
    "total_deliveries", "Total number of deliveries"
)
pending_deliveries = Gauge(
    "pending_deliveries", "Number of pending deliveries"
)
on_the_way_deliveries = Gauge(
    "on_the_way_deliveries", "Number of deliveries on the way"
)
average_delivery_time = Summary(
    "average_delivery_time", "Delivery time in seconds"
)

def simulate_delivery():
    pending = random.randint(50, 100)
    on_the_way = random.randint(5, 20)
    delivered = random.randint(30, 70)
    avg_time = random.uniform(15, 45)

    total = pending + on_the_way + delivered

    total_deliveries.set(total)
    pending_deliveries.set(pending)
    on_the_way_deliveries.set(on_the_way)
    average_delivery_time.observe(avg_time)

    print(
        f"Total: {total} | Pending: {pending} | "
        f"On the way: {on_the_way} | "
        f"Delivery time: {avg_time:.2f}s",
        flush=True
    )

if __name__ == "__main__":
    start_http_server(8000, addr="0.0.0.0")
    print("Metrics available on port 8000", flush=True)

    while True:
        simulate_delivery()
        time.sleep(1)
