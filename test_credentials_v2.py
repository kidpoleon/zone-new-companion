#!/usr/bin/env python3
"""
Improved comprehensive credential testing script for zone-new-companion v1.0.9.
Features adaptive timeouts, connection pooling, and better error handling.
"""

import asyncio
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeout
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urlparse

import requests

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from zone_new_companion.models import Credentials, PortalType
from zone_new_companion.services.logger_service import LoggerService
from zone_new_companion.services.stalker_service import StalkerService
from zone_new_companion.services.xtream_service import XtreamService
from zone_new_companion.services.network_optimizer import (
    OptimizedSession, AdaptiveTimeout, fast_dns_check, 
    fast_connectivity_check, credential_health_score, TIMEOUT_CONFIG
)


class ImprovedCredentialTester:
    """Improved credential testing system with optimizations."""
    
    def __init__(self):
        self.logger = LoggerService()
        self.results = {
            'xtream': {'total': 0, 'connected': 0, 'streams': 0, 'failed': 0, 'details': []},
            'stalker': {'total': 0, 'connected': 0, 'streams': 0, 'failed': 0, 'details': []}
        }
        self.start_time = time.time()
        self.adaptive_timeout = AdaptiveTimeout()
        self.session = OptimizedSession()
        
        # Performance tracking
        self.performance_stats = {
            'dns_checks': 0,
            'connectivity_checks': 0,
            'fast_failures': 0,
            'total_time_saved': 0.0
        }
        
    def parse_xtream_credentials(self, file_path: str) -> List[Credentials]:
        """Parse Xtream credentials from example file."""
        credentials = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Parse format: timestamp|url|username=...|password=...|...
                parts = line.split('|')
                if len(parts) >= 2:
                    url_part = parts[1]
                    try:
                        parsed = urlparse(url_part)
                        if parsed.query:
                            # Extract username and password from query parameters
                            params = dict(pair.split('=') for pair in parsed.query.split('&') if '=' in pair)
                            username = params.get('username')
                            password = params.get('password')
                            
                            if username and password:
                                creds = Credentials(
                                    name=f"Xtream-{username}",
                                    base_url=f"{parsed.scheme}://{parsed.netloc}",
                                    portal_type=PortalType.XTREAM,
                                    username=username,
                                    password=password,
                                )
                                credentials.append(creds)
                    except Exception as e:
                        self.logger.error(f"Failed to parse Xtream line: {line[:50]}... - {e}")
                        
        except Exception as e:
            self.logger.error(f"Failed to read Xtream file {file_path}: {e}")
            
        return credentials
    
    def parse_stalker_credentials(self, file_path: str) -> List[Credentials]:
        """Parse Stalker credentials from example file with improved parsing."""
        credentials = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Try multiple parsing strategies
            strategies = [
                self._parse_stalker_by_separator,
                self._parse_stalker_by_lines,
                self._parse_stalker_by_regex
            ]
            
            for strategy in strategies:
                try:
                    parsed_creds = strategy(content)
                    if parsed_creds:
                        credentials.extend(parsed_creds)
                        break
                except Exception as e:
                    self.logger.debug(f"Stalker parsing strategy failed: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Failed to read Stalker file {file_path}: {e}")
            
        return credentials
    
    def _parse_stalker_by_separator(self, content: str) -> List[Credentials]:
        """Parse Stalker credentials by separator."""
        credentials = []
        entries = content.split('------------------------------------------------------------')
        
        for entry in entries:
            portal = None
            mac = None
            
            lines = entry.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Portal'):
                    portal = line.split(':')[-1].strip()
                elif line.startswith('MAC'):
                    mac = line.split(':')[-1].strip()
                    
            if portal and mac and portal.startswith('http'):
                creds = Credentials(
                    name=f"Stalker-{mac}",
                    base_url=portal,
                    portal_type=PortalType.STALKER,
                    mac_address=mac,
                )
                credentials.append(creds)
                
        return credentials
    
    def _parse_stalker_by_lines(self, content: str) -> List[Credentials]:
        """Parse Stalker credentials by line-by-line analysis."""
        credentials = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for portal URL
            if line.startswith('Portal') and ':' in line:
                portal = line.split(':', 1)[1].strip()
                
                # Look for MAC in next few lines
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith('MAC') and ':' in next_line:
                        mac = next_line.split(':', 1)[1].strip()
                        
                        if portal.startswith('http') and mac:
                            creds = Credentials(
                                name=f"Stalker-{mac}",
                                base_url=portal,
                                portal_type=PortalType.STALKER,
                                mac_address=mac,
                            )
                            credentials.append(creds)
                            i = j  # Skip to after MAC line
                            break
            i += 1
            
        return credentials
    
    def _parse_stalker_by_regex(self, content: str) -> List[Credentials]:
        """Parse Stalker credentials using regex patterns."""
        credentials = []
        
        # Pattern to find portal URLs
        portal_pattern = r'Portal:\s*(https?://[^\s\n]+)'
        # Pattern to find MAC addresses
        mac_pattern = r'MAC:\s*([0-9A-Fa-f:]{17})'
        
        portals = re.findall(portal_pattern, content)
        macs = re.findall(mac_pattern, content)
        
        # Pair portals with MACs (assuming order)
        for i, (portal, mac) in enumerate(zip(portals, macs)):
            if portal.startswith('http'):
                creds = Credentials(
                    name=f"Stalker-{mac}",
                    base_url=portal,
                    portal_type=PortalType.STALKER,
                    mac_address=mac,
                )
                credentials.append(creds)
                
        return credentials
    
    def pre_validate_credential(self, creds: Credentials) -> Tuple[bool, str]:
        """Fast pre-validation of credentials before full testing."""
        start_time = time.time()
        
        # DNS check
        if not fast_dns_check(creds.base_url):
            self.performance_stats['dns_checks'] += 1
            return False, "DNS resolution failed"
        
        # Fast connectivity check
        if not fast_connectivity_check(creds.base_url, timeout=3.0):
            self.performance_stats['connectivity_checks'] += 1
            return False, "Connectivity check failed"
        
        validation_time = time.time() - start_time
        self.performance_stats['total_time_saved'] += (10.0 - validation_time)  # Assume 10s would be normal test time
        
        return True, "Pre-validation passed"
    
    def test_xtream_connection_optimized(self, creds: Credentials) -> Dict[str, Any]:
        """Optimized Xtream credential testing."""
        result = {
            'url': creds.base_url,
            'username': creds.username,
            'connected': False,
            'streams_available': False,
            'categories': 0,
            'channels': 0,
            'error': None,
            'response_time': 0,
            'health_score': 0.0,
            'pre_validation': ''
        }
        
        start_time = time.time()
        
        try:
            # Pre-validation
            is_valid, validation_msg = self.pre_validate_credential(creds)
            result['pre_validation'] = validation_msg
            
            if not is_valid:
                result['error'] = f"Pre-validation failed: {validation_msg}"
                self.performance_stats['fast_failures'] += 1
                return result
            
            # Use optimized session
            service = XtreamService()
            service._session = self.session.session  # Replace with optimized session
            
            # Test authentication and get categories
            categories = service.fetch_categories(creds)
            result['connected'] = True
            result['categories'] = len(categories.get('Live', [])) + len(categories.get('Movies', [])) + len(categories.get('Series', []))
            
            # Test getting some channels to check stream availability
            if categories.get('Live'):
                live_category = categories['Live'][0]
                channels = service.fetch_items(creds, live_category)
                result['channels'] = len(channels)
                
                # Test stream URL resolution for first channel
                if channels:
                    try:
                        stream_url = service.resolve_stream_url(creds, channels[0])
                        result['streams_available'] = bool(stream_url)
                    except Exception as e:
                        result['streams_available'] = False
                        result['error'] = f"Stream resolution failed: {e}"
                        
        except Exception as e:
            result['error'] = str(e)
            
        result['response_time'] = time.time() - start_time
        result['health_score'] = credential_health_score(
            creds.base_url, 
            result['response_time'], 
            result['connected']
        )
        
        return result
    
    def test_stalker_connection_optimized(self, creds: Credentials) -> Dict[str, Any]:
        """Optimized Stalker credential testing."""
        result = {
            'url': creds.base_url,
            'mac': creds.mac_address,
            'connected': False,
            'streams_available': False,
            'categories': 0,
            'channels': 0,
            'error': None,
            'response_time': 0,
            'health_score': 0.0,
            'pre_validation': ''
        }
        
        start_time = time.time()
        
        try:
            # Pre-validation
            is_valid, validation_msg = self.pre_validate_credential(creds)
            result['pre_validation'] = validation_msg
            
            if not is_valid:
                result['error'] = f"Pre-validation failed: {validation_msg}"
                self.performance_stats['fast_failures'] += 1
                return result
            
            # Use optimized session
            service = StalkerService()
            service._session = self.session.session  # Replace with optimized session
            
            # Test authentication and get categories
            categories = service.fetch_categories(creds)
            result['connected'] = True
            result['categories'] = len(categories.get('Live', [])) + len(categories.get('Movies', [])) + len(categories.get('Series', []))
            
            # Test getting some channels to check stream availability
            if categories.get('Live'):
                live_category = categories['Live'][0]
                channels = service.fetch_items(creds, live_category)
                result['channels'] = len(channels)
                
                # Test stream URL resolution for first channel
                if channels:
                    try:
                        stream_url = service.resolve_stream_url(creds, channels[0])
                        result['streams_available'] = bool(stream_url)
                    except Exception as e:
                        result['streams_available'] = False
                        result['error'] = f"Stream resolution failed: {e}"
                        
        except Exception as e:
            result['error'] = str(e)
            
        result['response_time'] = time.time() - start_time
        result['health_score'] = credential_health_score(
            creds.base_url, 
            result['response_time'], 
            result['connected']
        )
        
        return result
    
    def test_credentials_batch_optimized(self, credentials: List[Credentials], cred_type: str, max_workers: int = 5) -> None:
        """Optimized batch testing with better error handling and progress reporting."""
        self.logger.info(f"Testing {len(credentials)} {cred_type} credentials with optimizations...")
        
        completed = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_creds = {}
            for creds in credentials:
                if cred_type == 'xtream':
                    future = executor.submit(self.test_xtream_connection_optimized, creds)
                else:
                    future = executor.submit(self.test_stalker_connection_optimized, creds)
                future_to_creds[future] = creds
            
            # Process results as they complete with timeout
            for future in as_completed(future_to_creds, timeout=300):  # 5 minute total timeout
                creds = future_to_creds[future]
                try:
                    result = future.result(timeout=30)  # 30 second timeout per credential
                    
                    # Update statistics
                    self.results[cred_type]['total'] += 1
                    if result['connected']:
                        self.results[cred_type]['connected'] += 1
                    if result['streams_available']:
                        self.results[cred_type]['streams'] += 1
                    if result['error']:
                        self.results[cred_type]['failed'] += 1
                        
                    self.results[cred_type]['details'].append(result)
                    
                    completed += 1
                    
                    # Real-time progress reporting
                    if completed % 5 == 0 or completed == len(credentials):
                        elapsed = time.time() - start_time
                        avg_time = elapsed / completed
                        remaining = (len(credentials) - completed) * avg_time
                        self.logger.info(
                            f"{cred_type.title()}: {completed}/{len(credentials)} tested | "
                            f"Avg: {avg_time:.1f}s | ETA: {remaining:.0f}s | "
                            f"Success: {self.results[cred_type]['connected']}/{completed}"
                        )
                        
                except FutureTimeout:
                    self.logger.warning(f"Timeout testing {creds.base_url}")
                    self.results[cred_type]['total'] += 1
                    self.results[cred_type]['failed'] += 1
                    completed += 1
                except Exception as e:
                    self.logger.error(f"Failed to test {creds.base_url}: {e}")
                    self.results[cred_type]['total'] += 1
                    self.results[cred_type]['failed'] += 1
                    completed += 1
    
    def run_optimized_test(self) -> None:
        """Run optimized comprehensive test."""
        self.logger.info("Starting OPTIMIZED comprehensive credential testing...")
        
        # Parse credentials from files
        xtream_creds = self.parse_xtream_credentials('/home/administrator/Downloads/example_xtream.txt')
        stalker_creds = self.parse_stalker_credentials('/home/administrator/Downloads/example_stalker.txt')
        
        self.logger.info(f"Found {len(xtream_creds)} Xtream credentials")
        self.logger.info(f"Found {len(stalker_creds)} Stalker credentials")
        
        # Test Xtream credentials
        if xtream_creds:
            self.test_credentials_batch_optimized(xtream_creds, 'xtream', max_workers=5)
        
        # Test Stalker credentials  
        if stalker_creds:
            self.test_credentials_batch_optimized(stalker_creds, 'stalker', max_workers=5)
        
        # Generate final report
        self.generate_optimized_report()
    
    def generate_optimized_report(self) -> None:
        """Generate comprehensive test report with performance metrics."""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("OPTIMIZED COMPREHENSIVE CREDENTIAL TEST REPORT v1.0.9")
        print("="*80)
        print(f"Test Duration: {total_time:.2f} seconds")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Performance metrics
        print("PERFORMANCE OPTIMIZATIONS:")
        print("-" * 40)
        print(f"DNS Checks Saved: {self.performance_stats['dns_checks']} failures")
        print(f"Connectivity Checks Saved: {self.performance_stats['connectivity_checks']} failures")
        print(f"Fast Failures: {self.performance_stats['fast_failures']} credentials")
        print(f"Estimated Time Saved: {self.performance_stats['total_time_saved']:.1f} seconds")
        print()
        
        # Xtream Results
        xtream = self.results['xtream']
        print("XTREAM RESULTS:")
        print("-" * 40)
        print(f"Total Credentials: {xtream['total']}")
        print(f"Successfully Connected: {xtream['connected']} ({xtream['connected']/max(xtream['total'],1)*100:.1f}%)")
        print(f"Streams Available: {xtream['streams']} ({xtream['streams']/max(xtream['total'],1)*100:.1f}%)")
        print(f"Failed: {xtream['failed']} ({xtream['failed']/max(xtream['total'],1)*100:.1f}%)")
        
        # Show top performing credentials
        working_xtream = [d for d in xtream['details'] if d['connected']]
        if working_xtream:
            working_xtream.sort(key=lambda x: x['health_score'], reverse=True)
            print(f"\nTop {min(5, len(working_xtream))} Performing Xtream Credentials:")
            for detail in working_xtream[:5]:
                print(f"  ★ Score:{detail['health_score']:.2f} | {detail['username']}@{detail['url']} | "
                      f"{detail['categories']} cats, {detail['channels']} chans | {detail['response_time']:.2f}s")
        print()
        
        # Stalker Results
        stalker = self.results['stalker']
        print("STALKER RESULTS:")
        print("-" * 40)
        print(f"Total Credentials: {stalker['total']}")
        print(f"Successfully Connected: {stalker['connected']} ({stalker['connected']/max(stalker['total'],1)*100:.1f}%)")
        print(f"Streams Available: {stalker['streams']} ({stalker['streams']/max(stalker['total'],1)*100:.1f}%)")
        print(f"Failed: {stalker['failed']} ({stalker['failed']/max(stalker['total'],1)*100:.1f}%)")
        
        # Show top performing credentials
        working_stalker = [d for d in stalker['details'] if d['connected']]
        if working_stalker:
            working_stalker.sort(key=lambda x: x['health_score'], reverse=True)
            print(f"\nTop {min(5, len(working_stalker))} Performing Stalker Credentials:")
            for detail in working_stalker[:5]:
                print(f"  ★ Score:{detail['health_score']:.2f} | MAC:{detail['mac']}@{detail['url']} | "
                      f"{detail['categories']} cats, {detail['channels']} chans | {detail['response_time']:.2f}s")
        print()
        
        # Overall Summary
        total_creds = xtream['total'] + stalker['total']
        total_connected = xtream['connected'] + stalker['connected']
        total_streams = xtream['streams'] + stalker['streams']
        total_failed = xtream['failed'] + stalker['failed']
        
        print("OVERALL SUMMARY:")
        print("-" * 40)
        print(f"Total Credentials Tested: {total_creds}")
        print(f"Successfully Connected: {total_connected} ({total_connected/max(total_creds,1)*100:.1f}%)")
        print(f"Streams Available: {total_streams} ({total_streams/max(total_creds,1)*100:.1f}%)")
        print(f"Failed: {total_failed} ({total_failed/max(total_creds,1)*100:.1f}%)")
        print(f"Average Test Time: {total_time/max(total_creds,1):.2f}s per credential")
        print()
        
        # Save detailed report to file
        report_file = f"optimized_credential_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Add performance stats to results
        full_results = {
            'results': self.results,
            'performance_stats': self.performance_stats,
            'test_duration': total_time,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(report_file, 'w') as f:
            json.dump(full_results, f, indent=2)
        print(f"Detailed report saved to: {report_file}")


if __name__ == "__main__":
    tester = ImprovedCredentialTester()
    tester.run_optimized_test()
