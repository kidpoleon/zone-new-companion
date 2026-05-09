"""Network optimization utilities for faster credential testing."""

from __future__ import annotations

import ssl
import time
from urllib.parse import urlparse
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
    
    def __init__(self, ssl_profile='default', **kwargs):
        self.ssl_profile = ssl_profile
        super().__init__(**kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        """Initialize pool manager with custom SSL context."""
        context = self._create_ssl_context()
        kwargs['ssl_context'] = context
        kwargs['block'] = False
        return super().init_poolmanager(*args, **kwargs)
    
    def _create_ssl_context(self):
        """Create SSL context based on profile."""
        context = ssl.create_default_context()
        
        if self.ssl_profile == 'permissive':
            # Most permissive - for problematic servers
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.set_ciphers('ALL:@SECLEVEL=0')
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
        elif self.ssl_profile == 'legacy':
            # Legacy support - for older servers
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.set_ciphers('DEFAULT@SECLEVEL=1')
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
        elif self.ssl_profile == 'modern':
            # Modern but flexible
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        else:  # default
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.set_ciphers('DEFAULT@SECLEVEL=1')
            
        return context

class FallbackSession:
    """Session with multiple SSL configuration fallbacks."""
    
    def __init__(self):
        self.sessions = {}
        self.ssl_profiles = ['default', 'legacy', 'permissive', 'modern']
        self._create_sessions()
    
    def _create_sessions(self):
        """Create sessions with different SSL configurations."""
        for profile in self.ssl_profiles:
            session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=2,
                backoff_factor=1.0,
                status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524],
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
                raise_on_status=False
            )
            
            # Configure SSL adapter
            ssl_adapter = SSLAdapter(
                ssl_profile=profile,
                max_retries=retry_strategy,
                pool_connections=10,
                pool_maxsize=20,
                pool_block=False
            )
            
            # Configure HTTP adapter
            http_adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=10,
                pool_maxsize=20,
                pool_block=False
            )
            
            session.mount("http://", http_adapter)
            session.mount("https://", ssl_adapter)
            
            # Set headers
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            self.sessions[profile] = session
    
    def get(self, url, **kwargs):
        """Try GET request with SSL fallbacks."""
        return self._request_with_fallback('GET', url, **kwargs)
    
    def _request_with_fallback(self, method, url, **kwargs):
        """Try request with different SSL configurations."""
        last_error = None
        
        for profile in self.ssl_profiles:
            session = self.sessions[profile]
            try:
                response = session.request(method, url, **kwargs)
                # If we get a successful response, return it
                if response.status_code < 500:
                    return response
            except Exception as e:
                last_error = e
                continue
        
        # If all SSL profiles failed, raise the last error
        if last_error:
            raise last_error
        
        raise requests.RequestException(f"All SSL profiles failed for {url}")

class OptimizedSession:
    """Optimized HTTP session with connection pooling and retry logic."""
    
    def __init__(self, timeout_mode: str = 'normal'):
        self.timeout_mode = timeout_mode
        self.adaptive_timeout = AdaptiveTimeout()
        self.session = FallbackSession()
        self.protocol_cache = {}  # Cache successful protocols for servers
        
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
        """Optimized GET request with adaptive timeouts and protocol rotation."""
        base_url = kwargs.get('base_url', url)
        timeout_config = self.adaptive_timeout.get_timeout_for_server(base_url)
        
        start_time = time.time()
        
        try:
            # Override timeout with adaptive configuration
            kwargs['timeout'] = Timeout(
                connect=timeout_config['connect'],
                read=timeout_config['read']
            )
            
            # Try protocol rotation if needed
            response = self._get_with_protocol_rotation(url, **kwargs)
            response_time = time.time() - start_time
            
            # Update performance metrics
            self.adaptive_timeout.update_performance(base_url, response_time, True)
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            # Update performance metrics for failure
            self.adaptive_timeout.update_performance(base_url, response_time, False)
            raise
    
    def _get_with_protocol_rotation(self, url: str, **kwargs) -> requests.Response:
        """Try GET request with HTTP/HTTPS protocol rotation."""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Check if we have a cached successful protocol for this domain
        if domain in self.protocol_cache:
            cached_protocol = self.protocol_cache[domain]
            if cached_protocol != parsed.scheme:
                # Use cached protocol
                rotated_url = url.replace(f"{parsed.scheme}://", f"{cached_protocol}://")
                try:
                    response = self.session.get(rotated_url, **kwargs)
                    if response.status_code < 500:
                        return response
                except Exception:
                    pass  # Fall through to normal rotation
        
        # Try original URL first
        try:
            response = self.session.get(url, **kwargs)
            if response.status_code < 500:
                # Cache successful protocol
                self.protocol_cache[domain] = parsed.scheme
                return response
        except Exception:
            pass

        # Try protocol rotation
        if parsed.scheme == 'https':
            # Try HTTP
            http_url = url.replace("https://", "http://")
            try:
                response = self.session.get(http_url, **kwargs)
                if response.status_code < 500:
                    self.protocol_cache[domain] = 'http'
                    return response
            except Exception:
                pass
        elif parsed.scheme == 'http':
            # Try HTTPS
            https_url = url.replace("http://", "https://")
            try:
                response = self.session.get(https_url, **kwargs)
                if response.status_code < 500:
                    self.protocol_cache[domain] = 'https'
                    return response
            except Exception:
                pass

        # If all attempts failed, raise the last error
        raise requests.RequestException(f"All protocol attempts failed for {url}")

def fast_dns_check(base_url: str) -> bool:
    """Fast DNS resolution check with multiple DNS servers."""
    import dns.resolver
    
    try:
        parsed = urlparse(base_url)
        domain = parsed.netloc.split(':')[0]  # Remove port if present
        
        # Try multiple DNS servers for better reliability
        dns_servers = ['8.8.8.8', '1.1.1.1', '208.67.222.222', '9.9.9.9']
        
        for dns_server in dns_servers:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [dns_server]
                resolver.timeout = 2
                resolver.lifetime = 2
                result = resolver.resolve(domain, 'A')
                return True
            except:
                continue
                
        # Fallback to system DNS
        socket.gethostbyname(domain)
        return True
        
    except (socket.gaierror, UnicodeError, ImportError):
        # Fallback to basic DNS check
        try:
            parsed = urlparse(base_url)
            socket.gethostbyname(parsed.netloc)
            return True
        except (socket.gaierror, UnicodeError):
            return False

def fast_connectivity_check(base_url: str, timeout: float = 5.0) -> bool:
    """Enhanced connectivity check with multiple endpoints."""
    try:
        parsed = urlparse(base_url)
        
        # Try multiple test endpoints for better reliability
        test_endpoints = [
            f"{parsed.scheme}://{parsed.netloc}/",
            f"{parsed.scheme}://{parsed.netloc}/player_api.php",
            f"{parsed.scheme}://{parsed.netloc}/panel_api.php",
            f"{parsed.scheme}://{parsed.netloc}/xtream",
            f"{parsed.scheme}://{parsed.netloc}/portal.php"
        ]
        
        for endpoint in test_endpoints:
            try:
                response = requests.head(
                    endpoint,
                    timeout=timeout,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; IPTV-Checker)',
                        'Accept': 'application/json, text/plain, */*',
                        'Connection': 'keep-alive'
                    },
                    allow_redirects=True
                )
                if response.status_code < 500:
                    return True
            except:
                continue
                
        return False
        
    except Exception:
        return False

def advanced_connection_test(base_url: str, timeout: float = 10.0) -> dict:
    """Advanced connection test with detailed diagnostics."""
    results = {
        'dns_ok': False,
        'http_ok': False,
        'https_ok': False,
        'port_open': False,
        'response_time': None,
        'working_protocol': None,
        'working_endpoint': None
    }
    
    try:
        parsed = urlparse(base_url)
        host = parsed.netloc.split(':')[0]
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        start_time = time.time()
        
        # DNS check
        results['dns_ok'] = fast_dns_check(base_url)
        
        # Port check
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            results['port_open'] = result == 0
            sock.close()
        except:
            results['port_open'] = False
        
        # HTTP/HTTPS tests
        if results['dns_ok'] and results['port_open']:
            for protocol in ['http', 'https']:
                try:
                    test_url = f"{protocol}://{parsed.netloc}/player_api.php"
                    response = requests.head(
                        test_url,
                        timeout=timeout,
                        headers={'User-Agent': 'Mozilla/5.0 (compatible; IPTV-Checker)'}
                    )
                    
                    if response.status_code < 500:
                        if protocol == 'http':
                            results['http_ok'] = True
                        else:
                            results['https_ok'] = True
                        
                        if results['working_protocol'] is None:
                            results['working_protocol'] = protocol
                            results['working_endpoint'] = test_url
                            results['response_time'] = time.time() - start_time
                            
                except:
                    continue
        
        return results
        
    except Exception as e:
        results['error'] = str(e)
        return results

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
