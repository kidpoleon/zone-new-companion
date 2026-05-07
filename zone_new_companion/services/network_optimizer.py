"""Network optimization utilities for faster credential testing."""

from __future__ import annotations

import socket
import ssl
import time
from urllib.parse import urlparse
from urllib3 import PoolManager, Retry, Timeout
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Adaptive timeout configurations
TIMEOUT_CONFIG = {
    'fast': {
        'connect': 3.0,
        'read': 5.0,
        'total': 10.0
    },
    'normal': {
        'connect': 5.0,
        'read': 10.0,
        'total': 20.0
    },
    'slow': {
        'connect': 8.0,
        'read': 15.0,
        'total': 30.0
    }
}

class AdaptiveTimeout:
    """Adaptive timeout management based on server response patterns."""
    
    def __init__(self):
        self.server_performance = {}
        
    def get_timeout_for_server(self, base_url: str) -> dict:
        """Get appropriate timeout configuration for a server."""
        domain = urlparse(base_url).netloc
        
        if domain not in self.server_performance:
            self.server_performance[domain] = {
                'avg_response_time': 0,
                'success_count': 0,
                'failure_count': 0
            }
        
        perf = self.server_performance[domain]
        
        # Determine timeout based on performance history
        if perf['failure_count'] > perf['success_count']:
            return TIMEOUT_CONFIG['fast']  # Fast timeout for failing servers
        elif perf['avg_response_time'] > 10:
            return TIMEOUT_CONFIG['slow']   # Slower timeout for slow servers
        else:
            return TIMEOUT_CONFIG['normal']  # Normal timeout for good servers
    
    def update_performance(self, base_url: str, response_time: float, success: bool):
        """Update server performance metrics."""
        domain = urlparse(base_url).netloc
        
        if domain not in self.server_performance:
            self.server_performance[domain] = {
                'avg_response_time': 0,
                'success_count': 0,
                'failure_count': 0
            }
        
        perf = self.server_performance[domain]
        
        if success:
            perf['success_count'] += 1
            # Update average response time
            total_requests = perf['success_count'] + perf['failure_count']
            perf['avg_response_time'] = (
                (perf['avg_response_time'] * (total_requests - 1) + response_time) / total_requests
            )
        else:
            perf['failure_count'] += 1

class SSLAdapter(HTTPAdapter):
    """Custom adapter with SSL configuration for IPTV servers."""
    
    def init_poolmanager(self, *args, **kwargs):
        """Initialize pool manager with custom SSL context."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        # Allow older cipher suites for compatibility
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        
        kwargs['ssl_context'] = context
        kwargs['block'] = False
        return super().init_poolmanager(*args, **kwargs)

class OptimizedSession:
    """Optimized HTTP session with connection pooling and retry logic."""
    
    def __init__(self, timeout_mode: str = 'normal'):
        self.timeout_mode = timeout_mode
        self.adaptive_timeout = AdaptiveTimeout()
        self.session = self._create_optimized_session()
        
    def _create_optimized_session(self) -> requests.Session:
        """Create an optimized requests session."""
        session = requests.Session()
        
        # Disable SSL warnings for IPTV servers
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Configure retry strategy with more aggressive retries for IPTV servers
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1.0,  # Exponential backoff
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524],  # More status codes
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],  # Allow POST for IPTV APIs
            raise_on_status=False  # Don't raise on retry status codes
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=15,  # Number of connection pools
            pool_maxsize=30,      # Maximum number of connections in each pool
            pool_block=False      # Don't block when pool is full
        )
        
        # Configure SSL adapter for HTTPS connections
        ssl_adapter = SSLAdapter(
            max_retries=retry_strategy,
            pool_connections=15,
            pool_maxsize=30,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", ssl_adapter)
        
        # Set default headers for IPTV compatibility
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        return session
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Optimized GET request with adaptive timeouts."""
        base_url = kwargs.get('base_url', url)
        timeout_config = self.adaptive_timeout.get_timeout_for_server(base_url)
        
        start_time = time.time()
        
        try:
            # Override timeout with adaptive configuration
            kwargs['timeout'] = Timeout(
                connect=timeout_config['connect'],
                read=timeout_config['read']
            )
            
            response = self.session.get(url, **kwargs)
            response_time = time.time() - start_time
            
            # Update performance metrics
            self.adaptive_timeout.update_performance(base_url, response_time, True)
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            # Update performance metrics for failure
            self.adaptive_timeout.update_performance(base_url, response_time, False)
            raise

def fast_dns_check(base_url: str) -> bool:
    """Fast DNS resolution check."""
    try:
        parsed = urlparse(base_url)
        socket.gethostbyname(parsed.netloc)
        return True
    except (socket.gaierror, UnicodeError):
        return False

def fast_connectivity_check(base_url: str, timeout: float = 5.0) -> bool:
    """Fast connectivity check using HEAD request."""
    try:
        parsed = urlparse(base_url)
        test_url = f"{parsed.scheme}://{parsed.netloc}/"
        
        response = requests.head(
            test_url,
            timeout=timeout,
            allow_redirects=True,
            headers={'User-Agent': 'zone-new-companion/1.0.9'}
        )
        return response.status_code < 500
    except Exception:
        return False

def credential_health_score(base_url: str, response_time: float, success: bool) -> float:
    """Calculate health score for a credential (0.0 to 1.0)."""
    if not success:
        return 0.0
    
    # Score based on response time (faster = better)
    if response_time < 2.0:
        return 1.0
    elif response_time < 5.0:
        return 0.8
    elif response_time < 10.0:
        return 0.6
    elif response_time < 20.0:
        return 0.4
    else:
        return 0.2
