"""
Load Testing with Locust for PRECISE-HBR SMART on FHIR Application.

Usage:
    locust -f tests/load_tests/locustfile.py --host=http://localhost:8080

Web UI will be available at http://localhost:8089
"""

from locust import HttpUser, task, between, events
import json
import random
import time


class HealthCheckUser(HttpUser):
    """User that performs health checks."""
    
    wait_time = between(1, 3)
    weight = 3  # Higher weight = more common
    
    @task
    def health_check(self):
        """Perform health check."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")


class CDSHooksUser(HttpUser):
    """User that interacts with CDS Hooks endpoints."""
    
    wait_time = between(2, 5)
    weight = 2
    
    @task(3)
    def discover_services(self):
        """Discover CDS services."""
        with self.client.get("/cds-services", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'services' in data:
                        response.success()
                    else:
                        response.failure("Missing 'services' in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Discovery failed: {response.status_code}")
    
    @task(1)
    def call_bleeding_risk_hook(self):
        """Call PRECISE-HBR bleeding risk hook."""
        payload = {
            "hookInstance": f"hook-{random.randint(1000, 9999)}",
            "hook": "medication-prescribe",
            "context": {
                "patientId": f"patient-{random.randint(1, 100)}",
                "medications": [
                    {
                        "medicationCodeableConcept": {
                            "coding": [
                                {
                                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                    "code": "1191"
                                }
                            ],
                            "text": "Aspirin"
                        }
                    }
                ]
            }
        }
        
        with self.client.post(
            "/cds-services/precise_hbr_bleeding_risk_alert",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code in [200, 400]:
                response.success()
            else:
                response.failure(f"Hook call failed: {response.status_code}")


class APIUser(HttpUser):
    """User that interacts with API endpoints."""
    
    wait_time = between(3, 7)
    weight = 1
    
    @task
    def calculate_risk(self):
        """Call risk calculation API."""
        payload = {
            "patientId": f"patient-{random.randint(1, 100)}"
        }
        
        with self.client.post(
            "/api/calculate_risk",
            json=payload,
            catch_response=True
        ) as response:
            # May require authentication, so 401/302 is acceptable
            if response.status_code in [200, 302, 401, 400]:
                response.success()
            else:
                response.failure(f"API call failed: {response.status_code}")


class StandaloneUser(HttpUser):
    """User that accesses standalone mode."""
    
    wait_time = between(5, 10)
    weight = 1
    
    @task
    def access_standalone(self):
        """Access standalone page."""
        with self.client.get("/standalone", catch_response=True) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Standalone access failed: {response.status_code}")


class MixedWorkloadUser(HttpUser):
    """User that simulates realistic mixed workload."""
    
    wait_time = between(2, 6)
    weight = 5  # Most common user type
    
    @task(5)
    def health_check(self):
        """Frequent health checks."""
        self.client.get("/health")
    
    @task(3)
    def discover_services(self):
        """CDS service discovery."""
        self.client.get("/cds-services")
    
    @task(2)
    def access_static(self):
        """Access static resources."""
        static_files = [
            "/static/css/style.css",
            "/static/js/main.js",
            "/static/img/logo.png"
        ]
        self.client.get(random.choice(static_files))
    
    @task(1)
    def access_standalone(self):
        """Access standalone mode."""
        self.client.get("/standalone")


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Log custom metrics for each request."""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Actions when test starts."""
    print("=" * 50)
    print("PRECISE-HBR Load Test Starting")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Actions when test stops."""
    print("=" * 50)
    print("PRECISE-HBR Load Test Completed")
    print("=" * 50)
    
    # Print summary statistics
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.current_rps:.2f}")


# Configuration for different test scenarios
class QuickSmokeTest(HttpUser):
    """Quick smoke test for CI/CD pipelines."""
    
    wait_time = between(0.5, 1)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task
    def cds_discovery(self):
        self.client.get("/cds-services")


class StressTest(HttpUser):
    """Stress test with minimal wait time."""
    
    wait_time = between(0.1, 0.5)
    
    @task(10)
    def health_check(self):
        self.client.get("/health")
    
    @task(5)
    def cds_discovery(self):
        self.client.get("/cds-services")
    
    @task(2)
    def cds_hook(self):
        payload = {
            "hookInstance": f"stress-{random.randint(1, 10000)}",
            "hook": "medication-prescribe",
            "context": {"patientId": "stress-test"}
        }
        self.client.post("/cds-services/precise_hbr_bleeding_risk_alert", json=payload)


class SoakTest(HttpUser):
    """Soak test for long-running stability testing."""
    
    wait_time = between(5, 15)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task
    def mixed_operations(self):
        # Simulate realistic user session
        self.client.get("/cds-services")
        time.sleep(random.uniform(1, 3))
        self.client.get("/standalone")

