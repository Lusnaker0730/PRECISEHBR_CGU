"""
Performance Tests for PRECISE-HBR SMART on FHIR Application.

Tests response times, throughput, and resource usage for critical operations.
Uses pytest-benchmark for accurate performance measurements.
"""

import pytest
import time
import json
import statistics
from unittest.mock import Mock, patch
from flask import Flask


class TestResponseTimePerformance:
    """Test response time performance for critical endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app."""
        from APP import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    def test_health_endpoint_response_time(self, client):
        """Test that /health endpoint responds within acceptable time."""
        start_time = time.perf_counter()
        response = client.get('/health')
        end_time = time.perf_counter()
        
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert response_time_ms < 100, f"Health endpoint too slow: {response_time_ms:.2f}ms"
    
    def test_cds_services_response_time(self, client):
        """Test that /cds-services endpoint responds within acceptable time."""
        start_time = time.perf_counter()
        response = client.get('/cds-services')
        end_time = time.perf_counter()
        
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert response_time_ms < 200, f"CDS services endpoint too slow: {response_time_ms:.2f}ms"
    
    def test_static_file_response_time(self, client):
        """Test that static files are served quickly."""
        start_time = time.perf_counter()
        response = client.get('/static/css/style.css')
        end_time = time.perf_counter()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Static files might not exist in test, but should fail fast
        assert response_time_ms < 100, f"Static file response too slow: {response_time_ms:.2f}ms"


class TestThroughputPerformance:
    """Test throughput for high-traffic scenarios."""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app."""
        from APP import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    def test_health_endpoint_throughput(self, client):
        """Test /health endpoint can handle multiple rapid requests."""
        num_requests = 100
        response_times = []
        
        for _ in range(num_requests):
            start_time = time.perf_counter()
            response = client.get('/health')
            end_time = time.perf_counter()
            
            assert response.status_code == 200
            response_times.append((end_time - start_time) * 1000)
        
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        p95_response_time = sorted(response_times)[int(num_requests * 0.95)]
        
        # Performance assertions
        assert avg_response_time < 50, f"Average response time too high: {avg_response_time:.2f}ms"
        assert p95_response_time < 100, f"P95 response time too high: {p95_response_time:.2f}ms"
        
        # Calculate requests per second
        total_time = sum(response_times) / 1000  # Convert to seconds
        requests_per_second = num_requests / total_time
        
        assert requests_per_second > 50, f"Throughput too low: {requests_per_second:.2f} req/s"
    
    def test_cds_services_throughput(self, client):
        """Test /cds-services endpoint throughput."""
        num_requests = 50
        response_times = []
        
        for _ in range(num_requests):
            start_time = time.perf_counter()
            response = client.get('/cds-services')
            end_time = time.perf_counter()
            
            assert response.status_code == 200
            response_times.append((end_time - start_time) * 1000)
        
        avg_response_time = statistics.mean(response_times)
        
        assert avg_response_time < 100, f"Average response time too high: {avg_response_time:.2f}ms"


class TestComputationPerformance:
    """Test performance of computation-heavy operations."""
    
    def test_egfr_calculation_performance(self):
        """Test eGFR calculation performance."""
        from fhir_data_service import calculate_egfr
        
        num_calculations = 1000
        start_time = time.perf_counter()
        
        for i in range(num_calculations):
            # Vary inputs slightly
            creatinine = 1.0 + (i % 10) * 0.1
            age = 50 + (i % 30)
            gender = 'male' if i % 2 == 0 else 'female'
            
            result = calculate_egfr(creatinine, age, gender)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_calc = total_time_ms / num_calculations
        
        assert avg_time_per_calc < 0.1, f"eGFR calculation too slow: {avg_time_per_calc:.4f}ms per calculation"
    
    def test_hash_calculation_performance(self):
        """Test audit log hash calculation performance."""
        from audit_logger import AuditLogger
        import tempfile
        import os
        
        temp_dir = tempfile.mkdtemp()
        audit_path = os.path.join(temp_dir, 'perf_test.jsonl')
        logger = AuditLogger(audit_file_path=audit_path)
        
        test_data = {
            'timestamp': '2024-01-01T00:00:00Z',
            'event_type': 'TEST',
            'action': 'test_action',
            'user_id': 'user123',
            'patient_id': 'patient456'
        }
        
        num_calculations = 1000
        start_time = time.perf_counter()
        
        for _ in range(num_calculations):
            logger._calculate_hash(test_data)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_calc = total_time_ms / num_calculations
        
        assert avg_time_per_calc < 0.5, f"Hash calculation too slow: {avg_time_per_calc:.4f}ms per calculation"
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_input_validation_performance(self):
        """Test input validation performance."""
        from input_validator import validate_url, validate_patient_id
        
        num_validations = 1000
        
        # Test URL validation
        start_time = time.perf_counter()
        for i in range(num_validations):
            validate_url(f'https://example{i}.com/fhir')
        end_time = time.perf_counter()
        
        url_validation_time = (end_time - start_time) * 1000 / num_validations
        assert url_validation_time < 0.1, f"URL validation too slow: {url_validation_time:.4f}ms"
        
        # Test patient ID validation
        start_time = time.perf_counter()
        for i in range(num_validations):
            validate_patient_id(f'patient-{i:06d}')
        end_time = time.perf_counter()
        
        patient_id_validation_time = (end_time - start_time) * 1000 / num_validations
        assert patient_id_validation_time < 0.05, f"Patient ID validation too slow: {patient_id_validation_time:.4f}ms"


class TestMemoryPerformance:
    """Test memory usage and leaks."""
    
    def test_no_memory_leak_on_repeated_requests(self):
        """Test that repeated requests don't cause memory leaks."""
        import gc
        import sys
        
        from APP import app
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Force garbage collection
        gc.collect()
        
        # Get initial memory usage (approximate)
        initial_objects = len(gc.get_objects())
        
        # Make many requests
        for _ in range(100):
            client.get('/health')
        
        # Force garbage collection
        gc.collect()
        
        # Get final memory usage
        final_objects = len(gc.get_objects())
        
        # Allow some growth, but not excessive
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Possible memory leak: {object_growth} new objects after 100 requests"
    
    def test_large_json_handling(self):
        """Test handling of large JSON payloads."""
        from APP import app
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Create a large but reasonable JSON payload
        large_payload = {
            'patientId': 'patient-123',
            'data': [{'id': i, 'value': f'item-{i}'} for i in range(100)]
        }
        
        start_time = time.perf_counter()
        response = client.post(
            '/api/calculate_risk',
            json=large_payload,
            content_type='application/json'
        )
        end_time = time.perf_counter()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Should handle large payload without timeout
        assert response_time_ms < 5000, f"Large payload handling too slow: {response_time_ms:.2f}ms"


class TestConcurrencyPerformance:
    """Test performance under concurrent load."""
    
    def test_concurrent_health_checks(self):
        """Test concurrent health check requests."""
        import concurrent.futures
        
        from APP import app
        app.config['TESTING'] = True
        
        def make_request():
            with app.test_client() as client:
                start_time = time.perf_counter()
                response = client.get('/health')
                end_time = time.perf_counter()
                return response.status_code, (end_time - start_time) * 1000
        
        num_concurrent = 10
        num_requests_per_thread = 10
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(make_request)
                for _ in range(num_concurrent * num_requests_per_thread)
            ]
            
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Check all requests succeeded
        status_codes = [r[0] for r in results]
        response_times = [r[1] for r in results]
        
        success_rate = sum(1 for s in status_codes if s == 200) / len(status_codes)
        avg_response_time = statistics.mean(response_times)
        
        assert success_rate >= 0.95, f"Success rate too low under concurrency: {success_rate:.2%}"
        assert avg_response_time < 200, f"Average response time too high under concurrency: {avg_response_time:.2f}ms"


class TestDatabasePerformance:
    """Test database/file operation performance."""
    
    def test_audit_log_write_performance(self):
        """Test audit log write performance."""
        from audit_logger import AuditLogger
        import tempfile
        import os
        
        temp_dir = tempfile.mkdtemp()
        audit_path = os.path.join(temp_dir, 'perf_test.jsonl')
        logger = AuditLogger(audit_file_path=audit_path)
        
        num_writes = 100
        start_time = time.perf_counter()
        
        for i in range(num_writes):
            logger.log_event(
                event_type='PERFORMANCE_TEST',
                action=f'test_action_{i}',
                user_id=f'user_{i}',
                patient_id=f'patient_{i}'
            )
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_write = total_time_ms / num_writes
        
        assert avg_time_per_write < 10, f"Audit log write too slow: {avg_time_per_write:.2f}ms per write"
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_config_loading_performance(self):
        """Test configuration loading performance."""
        num_loads = 100
        start_time = time.perf_counter()
        
        for _ in range(num_loads):
            # Reload config module
            from importlib import reload
            import config
            reload(config)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_load = total_time_ms / num_loads
        
        assert avg_time_per_load < 50, f"Config loading too slow: {avg_time_per_load:.2f}ms per load"


class TestStartupPerformance:
    """Test application startup performance."""
    
    def test_app_import_time(self):
        """Test Flask app import time."""
        import sys
        
        # Remove APP from cache if present
        modules_to_remove = [k for k in sys.modules.keys() if k.startswith('APP') or k == 'APP']
        for mod in modules_to_remove:
            del sys.modules[mod]
        
        start_time = time.perf_counter()
        import APP
        end_time = time.perf_counter()
        
        import_time_ms = (end_time - start_time) * 1000
        
        # App should import within reasonable time
        assert import_time_ms < 5000, f"App import too slow: {import_time_ms:.2f}ms"
    
    def test_first_request_time(self):
        """Test time for first request after startup."""
        from APP import app
        app.config['TESTING'] = True
        client = app.test_client()
        
        start_time = time.perf_counter()
        response = client.get('/health')
        end_time = time.perf_counter()
        
        first_request_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert first_request_time_ms < 500, f"First request too slow: {first_request_time_ms:.2f}ms"


class TestPerformanceBenchmarks:
    """Performance benchmarks for tracking over time."""
    
    def test_benchmark_health_endpoint(self):
        """Benchmark health endpoint for baseline tracking."""
        from APP import app
        app.config['TESTING'] = True
        client = app.test_client()
        
        iterations = 50
        response_times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            response = client.get('/health')
            end = time.perf_counter()
            
            if response.status_code == 200:
                response_times.append((end - start) * 1000)
        
        if response_times:
            benchmark_results = {
                'min': min(response_times),
                'max': max(response_times),
                'avg': statistics.mean(response_times),
                'median': statistics.median(response_times),
                'stdev': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'p95': sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
            }
            
            print(f"\n=== Health Endpoint Benchmark ===")
            print(f"Min: {benchmark_results['min']:.2f}ms")
            print(f"Max: {benchmark_results['max']:.2f}ms")
            print(f"Avg: {benchmark_results['avg']:.2f}ms")
            print(f"Median: {benchmark_results['median']:.2f}ms")
            print(f"StdDev: {benchmark_results['stdev']:.2f}ms")
            print(f"P95: {benchmark_results['p95']:.2f}ms")
            
            # Assert reasonable performance
            assert benchmark_results['avg'] < 100
            assert benchmark_results['p95'] < 200


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

