#!/usr/bin/env python3
"""
Comprehensive credential testing script for zone-new-companion.
Tests all Xtream and Stalker credentials from example files.
"""

import asyncio
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from urllib.parse import urlparse

import requests

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from zone_new_companion.models import Credentials, PortalType
from zone_new_companion.services.logger_service import LoggerService
from zone_new_companion.services.stalker_service import StalkerService
from zone_new_companion.services.xtream_service import XtreamService
from zone_new_companion.services.network import DEFAULT_TIMEOUT


class CredentialTester:
    """Efficient credential testing system."""
    
    def __init__(self):
        self.logger = LoggerService()
        self.results = {
            'xtream': {'total': 0, 'connected': 0, 'streams': 0, 'failed': 0, 'details': []},
            'stalker': {'total': 0, 'connected': 0, 'streams': 0, 'failed': 0, 'details': []}
        }
        self.start_time = time.time()
        
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
        """Parse Stalker credentials from example file."""
        credentials = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Split by entry separators
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
                        
                # When we have both portal and MAC, create credentials
                if portal and mac and portal.startswith('http'):
                    creds = Credentials(
                        name=f"Stalker-{mac}",
                        base_url=portal,
                        portal_type=PortalType.STALKER,
                        mac_address=mac,
                    )
                    credentials.append(creds)
                    
        except Exception as e:
            self.logger.error(f"Failed to read Stalker file {file_path}: {e}")
            
        return credentials
    
    def test_xtream_connection(self, creds: Credentials) -> Dict[str, Any]:
        """Test Xtream credential connection and stream availability."""
        result = {
            'url': creds.base_url,
            'username': creds.username,
            'connected': False,
            'streams_available': False,
            'categories': 0,
            'channels': 0,
            'error': None,
            'response_time': 0
        }
        
        try:
            start_time = time.time()
            service = XtreamService()
            
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
                        
            result['response_time'] = time.time() - start_time
            
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def test_stalker_connection(self, creds: Credentials) -> Dict[str, Any]:
        """Test Stalker credential connection and stream availability."""
        result = {
            'url': creds.base_url,
            'mac': creds.mac_address,
            'connected': False,
            'streams_available': False,
            'categories': 0,
            'channels': 0,
            'error': None,
            'response_time': 0
        }
        
        try:
            start_time = time.time()
            service = StalkerService()
            
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
                        
            result['response_time'] = time.time() - start_time
            
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def test_credentials_batch(self, credentials: List[Credentials], cred_type: str, max_workers: int = 5) -> None:
        """Test a batch of credentials with thread pool."""
        self.logger.info(f"Testing {len(credentials)} {cred_type} credentials...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_creds = {}
            for creds in credentials:
                if cred_type == 'xtream':
                    future = executor.submit(self.test_xtream_connection, creds)
                else:
                    future = executor.submit(self.test_stalker_connection, creds)
                future_to_creds[future] = creds
            
            # Process results as they complete
            for future in as_completed(future_to_creds):
                creds = future_to_creds[future]
                try:
                    result = future.result(timeout=60)  # 60 second timeout per credential
                    
                    # Update statistics
                    self.results[cred_type]['total'] += 1
                    if result['connected']:
                        self.results[cred_type]['connected'] += 1
                    if result['streams_available']:
                        self.results[cred_type]['streams'] += 1
                    if result['error']:
                        self.results[cred_type]['failed'] += 1
                        
                    self.results[cred_type]['details'].append(result)
                    
                    # Log progress
                    total_tested = len(self.results[cred_type]['details'])
                    if total_tested % 10 == 0 or total_tested == len(credentials):
                        self.logger.info(f"{cred_type.title()}: {total_tested}/{len(credentials)} tested")
                        
                except Exception as e:
                    self.logger.error(f"Failed to test {creds.base_url}: {e}")
                    self.results[cred_type]['total'] += 1
                    self.results[cred_type]['failed'] += 1
    
    def run_comprehensive_test(self) -> None:
        """Run comprehensive test on all credentials."""
        self.logger.info("Starting comprehensive credential testing...")
        
        # Parse credentials from files
        xtream_creds = self.parse_xtream_credentials('/home/administrator/Downloads/example_xtream.txt')
        stalker_creds = self.parse_stalker_credentials('/home/administrator/Downloads/example_stalker.txt')
        
        self.logger.info(f"Found {len(xtream_creds)} Xtream credentials")
        self.logger.info(f"Found {len(stalker_creds)} Stalker credentials")
        
        # Test Xtream credentials
        if xtream_creds:
            self.test_credentials_batch(xtream_creds, 'xtream', max_workers=3)
        
        # Test Stalker credentials  
        if stalker_creds:
            self.test_credentials_batch(stalker_creds, 'stalker', max_workers=3)
        
        # Generate final report
        self.generate_report()
    
    def generate_report(self) -> None:
        """Generate comprehensive test report."""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("COMPREHENSIVE CREDENTIAL TEST REPORT")
        print("="*80)
        print(f"Test Duration: {total_time:.2f} seconds")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Xtream Results
        xtream = self.results['xtream']
        print("XTREAM RESULTS:")
        print("-" * 40)
        print(f"Total Credentials: {xtream['total']}")
        print(f"Successfully Connected: {xtream['connected']} ({xtream['connected']/max(xtream['total'],1)*100:.1f}%)")
        print(f"Streams Available: {xtream['streams']} ({xtream['streams']/max(xtream['total'],1)*100:.1f}%)")
        print(f"Failed: {xtream['failed']} ({xtream['failed']/max(xtream['total'],1)*100:.1f}%)")
        print()
        
        # Stalker Results
        stalker = self.results['stalker']
        print("STALKER RESULTS:")
        print("-" * 40)
        print(f"Total Credentials: {stalker['total']}")
        print(f"Successfully Connected: {stalker['connected']} ({stalker['connected']/max(stalker['total'],1)*100:.1f}%)")
        print(f"Streams Available: {stalker['streams']} ({stalker['streams']/max(stalker['total'],1)*100:.1f}%)")
        print(f"Failed: {stalker['failed']} ({stalker['failed']/max(stalker['total'],1)*100:.1f}%)")
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
        print()
        
        # Save detailed report to file
        report_file = f"credential_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Detailed report saved to: {report_file}")
        
        # Show successful connections
        print("\nSUCCESSFUL CONNECTIONS:")
        print("="*80)
        
        print("\nWorking Xtream Credentials:")
        for detail in xtream['details']:
            if detail['connected']:
                status = "✓ Streams" if detail['streams_available'] else "✓ Connected"
                print(f"  {status} | {detail['username']}@{detail['url']} | {detail['categories']} cats, {detail['channels']} chans | {detail['response_time']:.2f}s")
        
        print("\nWorking Stalker Credentials:")
        for detail in stalker['details']:
            if detail['connected']:
                status = "✓ Streams" if detail['streams_available'] else "✓ Connected"
                print(f"  {status} | MAC:{detail['mac']}@{detail['url']} | {detail['categories']} cats, {detail['channels']} chans | {detail['response_time']:.2f}s")


if __name__ == "__main__":
    tester = CredentialTester()
    tester.run_comprehensive_test()
