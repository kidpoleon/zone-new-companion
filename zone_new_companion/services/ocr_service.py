"""OCR service for video stream validation."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

import requests
from zone_new_companion.services.logger_service import logger_service


class OCRService:
    """OCR service for detecting video content and error screens."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "zone_new_companion_ocr"
        self.temp_dir.mkdir(exist_ok=True)
        self.ffmpeg_available = self._check_ffmpeg()
        self.tesseract_available = self._check_tesseract()
        
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger_service.warning("FFmpeg not found - OCR functionality will be limited")
            return False
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract OCR is available."""
        try:
            result = subprocess.run(
                ["tesseract", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger_service.warning("Tesseract not found - OCR functionality disabled")
            return False
    
    def analyze_stream_frame(self, stream_url: str, timeout: int = 10) -> Tuple[bool, str]:
        """
        Analyze a video stream frame to detect content vs error screens.
        
        Returns:
            Tuple[bool, str]: (is_valid_content, detected_text)
        """
        if not self.ffmpeg_available or not self.tesseract_available:
            return False, "OCR tools not available"
        
        try:
            # Extract frame from stream
            frame_path = self._extract_frame(stream_url, timeout)
            if not frame_path:
                return False, "Failed to extract frame"
            
            # Perform OCR on frame
            text = self._perform_ocr(frame_path)
            
            # Analyze text for error indicators
            is_valid = self._analyze_text_for_errors(text)
            
            # Cleanup
            try:
                frame_path.unlink()
            except:
                pass
                
            return is_valid, text
            
        except Exception as e:
            logger_service.error(f"OCR analysis failed: {e}")
            return False, f"OCR error: {e}"
    
    def _extract_frame(self, stream_url: str, timeout: int) -> Optional[Path]:
        """Extract a single frame from video stream using FFmpeg."""
        frame_path = self.temp_dir / f"frame_{int(time.time())}.jpg"
        
        try:
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-hide_banner",
                "-loglevel", "error",
                "-timeout", str(timeout),
                "-stimeout", str(timeout * 1000000),  # microseconds
                "-i", stream_url,
                "-ss", "00:00:02",  # Seek to 2 seconds
                "-vframes", "1",  # Extract 1 frame
                "-q:v", "2",  # Quality setting
                str(frame_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            
            if result.returncode == 0 and frame_path.exists():
                return frame_path
            else:
                logger_service.debug(f"FFmpeg failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger_service.warning(f"Frame extraction timeout for {stream_url}")
            return None
        except Exception as e:
            logger_service.error(f"Frame extraction error: {e}")
            return None
    
    def _perform_ocr(self, image_path: Path) -> str:
        """Perform OCR on an image using Tesseract."""
        try:
            cmd = [
                "tesseract",
                str(image_path),
                "stdout",  # Output to stdout
                "-l", "eng+por+spa+fra+deu+ita",  # Multiple languages for IPTV
                "--psm", "6",  # Assume uniform block of text
                "--oem", "3"  # Default OCR engine mode
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger_service.debug(f"Tesseract failed: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger_service.warning("OCR processing timeout")
            return ""
        except Exception as e:
            logger_service.error(f"OCR error: {e}")
            return ""
    
    def _analyze_text_for_errors(self, text: str) -> bool:
        """
        Analyze OCR text to determine if stream shows valid content or error.
        
        Returns:
            bool: True if content appears valid, False if error detected
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Error indicators
        error_patterns = [
            "error", "failed", "timeout", "connection", "offline",
            "unauthorized", "forbidden", "not found", "invalid",
            "login", "password", "authentication", "access denied",
            "codec", "unsupported", "buffering", "loading",
            "no signal", "service unavailable", "technical difficulties"
        ]
        
        # Content indicators (suggest valid stream)
        content_patterns = [
            "live", "hd", "fhd", "4k", "1080p", "720p", "480p",
            "stereo", "dolby", "ac3", "aac", "mp3",
            "fps", "bitrate", "kbps", "mbps"
        ]
        
        # Check for error patterns
        error_count = sum(1 for pattern in error_patterns if pattern in text_lower)
        content_count = sum(1 for pattern in content_patterns if pattern in text_lower)
        
        # If more error indicators than content indicators, likely an error
        if error_count > content_count:
            return False
        
        # If we found content indicators, likely valid
        if content_count > 0:
            return True
        
        # Default to False if unclear
        return False
    
    def quick_stream_check(self, stream_url: str) -> bool:
        """
        Quick check if stream is accessible without full OCR.
        Uses HTTP HEAD request and basic frame extraction.
        """
        try:
            # Try HTTP HEAD first
            if stream_url.startswith(('http://', 'https://')):
                response = requests.head(
                    stream_url,
                    timeout=5,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; IPTV-Checker)'}
                )
                if response.status_code == 200:
                    return True
        except:
            pass
        
        # Fall back to frame extraction check
        if not self.ffmpeg_available:
            return False
            
        frame_path = self._extract_frame(stream_url, timeout=5)
        if frame_path:
            try:
                frame_path.unlink()
            except:
                pass
            return True
            
        return False
    
    def cleanup(self):
        """Clean up temporary files."""
        try:
            for file in self.temp_dir.glob("*.jpg"):
                file.unlink()
        except Exception as e:
            logger_service.warning(f"Cleanup error: {e}")
