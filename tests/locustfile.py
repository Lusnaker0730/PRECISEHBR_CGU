"""
Locust Load Testing Configuration for PRECISE-HBR SMART on FHIR Application.

This file defines user behavior for load testing the application.
Run with: locust -f tests/locustfile.py --host http://localhost:8080
"""

from locust import HttpUser, task, between, tag
import json


class HealthCheckUser(HttpUser):
    """User that only performs health checks."""
    
    weight = 3  # More common than authenticated users
    wait_time = between(1, 3)
    
    @task(10)
    @tag('health')
    def health_check(self):
        """Check health endpoint."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    response.success()
                else:
                    response.failure(f"Unhealthy status: {data.get('status')}")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(5)
    @tag('cds')
    def cds_services_discovery(self):
        """Check CDS services discovery endpoint."""
        with self.client.get("/cds-services", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if 'services' in data:
                    response.success()
                else:
                    response.failure("No services in response")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(3)
    @tag('static')
    def load_index(self):
        """Load the index page."""
        self.client.get("/", name="Index Page")
    
    @task(2)
    @tag('static')
    def load_standalone(self):
        """Load the standalone page."""
        self.client.get("/standalone", name="Standalone Page")


class CDSHooksUser(HttpUser):
    """User that simulates CDS Hooks requests."""
    
    weight = 2
    wait_time = between(2, 5)
    
    def on_start(self):
        """Setup before tests."""
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    @task(5)
    @tag('cds', 'hooks')
    def cds_services(self):
        """Get CDS services list."""
        self.client.get("/cds-services", headers=self.headers)
    
    @task(3)
    @tag('cds', 'hooks')
    def precise_hbr_hook(self):
        """Call the PRECISE-HBR hook with sample data."""
        hook_request = {
            "hookInstance": "test-instance-123",
            "hook": "patient-view",
            "context": {
                "userId": "Practitioner/test-practitioner",
                "patientId": "Patient/test-patient"
            },
            "prefetch": {
                "patient": {
                    "resourceType": "Patient",
                    "id": "test-patient",
                    "name": [{"text": "Test Patient"}],
                    "gender": "male",
                    "birthDate": "1960-01-01"
                }
            }
        }
        
        with self.client.post(
            "/cds-services/precise-hbr",
            json=hook_request,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 400, 404]:
                # These are all acceptable responses
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class APIUser(HttpUser):
    """User that simulates API requests (without full authentication)."""
    
    weight = 1
    wait_time = between(3, 8)
    
    def on_start(self):
        """Setup before tests."""
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    @task(5)
    @tag('api')
    def api_calculate_risk_unauthenticated(self):
        """Test calculate risk API without auth (should fail gracefully)."""
        with self.client.post(
            "/api/calculate_risk",
            json={"patientId": "test-patient"},
            headers=self.headers,
            catch_response=True
        ) as response:
            # Should return 401 or 302 (redirect to login)
            if response.status_code in [401, 302]:
                response.success()
            else:
                response.failure(f"Expected 401/302, got {response.status_code}")
    
    @task(3)
    @tag('api')
    def api_export_ccd_unauthenticated(self):
        """Test CCD export API without auth (should fail gracefully)."""
        with self.client.post(
            "/api/export-ccd",
            json={"risk_data": {"total_score": 3}},
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [401, 302]:
                response.success()
            else:
                response.failure(f"Expected 401/302, got {response.status_code}")
    
    @task(2)
    @tag('api', 'launch')
    def launch_without_iss(self):
        """Test launch endpoint without ISS parameter."""
        with self.client.get("/launch", catch_response=True) as response:
            # Should return error page or redirect
            if response.status_code in [200, 302, 400, 500]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class StaticContentUser(HttpUser):
    """User that loads static content."""
    
    weight = 2
    wait_time = between(1, 2)
    
    @task(5)
    @tag('static')
    def load_css(self):
        """Load CSS files."""
        self.client.get("/static/css/style.css", name="CSS Files")
    
    @task(3)
    @tag('static')
    def load_js(self):
        """Load JavaScript files."""
        self.client.get("/static/js/main.js", name="JS Files")
    
    @task(2)
    @tag('static')
    def load_favicon(self):
        """Load favicon."""
        self.client.get("/static/favicon.ico", name="Favicon")


class MixedUser(HttpUser):
    """User that performs a mix of all operations."""
    
    weight = 5  # Most common user type
    wait_time = between(2, 5)
    
    def on_start(self):
        """Setup before tests."""
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    @task(10)
    @tag('health')
    def health_check(self):
        """Check health endpoint."""
        self.client.get("/health")
    
    @task(5)
    @tag('static')
    def load_pages(self):
        """Load various pages."""
        self.client.get("/")
        self.client.get("/standalone")
    
    @task(3)
    @tag('cds')
    def cds_services(self):
        """Check CDS services."""
        self.client.get("/cds-services", headers=self.headers)
    
    @task(2)
    @tag('api')
    def api_requests(self):
        """Make API requests."""
        self.client.post(
            "/api/calculate_risk",
            json={"patientId": "test"},
            headers=self.headers
        )
    
    @task(1)
    @tag('error')
    def trigger_404(self):
        """Test 404 handling."""
        with self.client.get("/nonexistent-page", catch_response=True) as response:
            if response.status_code == 404:
                response.success()
            else:
                response.failure(f"Expected 404, got {response.status_code}")


# Custom event handlers for reporting
from locust import events
import time

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests."""
    if response_time > 1000:  # More than 1 second
        print(f"SLOW REQUEST: {request_type} {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("=" * 60)
    print("PRECISE-HBR Load Test Starting")
    print(f"Target Host: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("=" * 60)
    print("PRECISE-HBR Load Test Complete")
    print("=" * 60)

