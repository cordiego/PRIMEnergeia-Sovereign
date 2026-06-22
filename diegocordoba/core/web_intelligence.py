"""
Web Intelligence Core for Dr. Prime
Provides universal and microscopic tools for web extraction and interaction.
"""

import re
import ast
import json
import logging
from typing import Dict, Any, List, Optional, Union

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class WebIntelligenceTools:
    @staticmethod
    def execute_raw_http(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, 
                         payload: Optional[Union[Dict, str]] = None, cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Universal HTTP client wrapper to bypass standard UI and talk directly to endpoints.
        """
        try:
            default_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            if headers:
                default_headers.update(headers)
                
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=default_headers,
                json=payload if isinstance(payload, dict) else None,
                data=payload if isinstance(payload, str) else None,
                cookies=cookies,
                timeout=15
            )
            
            return {
                "status_code": response.status_code,
                "url": response.url,
                "headers": dict(response.headers),
                "text": response.text,
                "json": response.json() if "application/json" in response.headers.get("Content-Type", "") else None
            }
        except Exception as e:
            logger.error(f"HTTP Request failed: {e}")
            return {"error": str(e), "status_code": 500}

    @staticmethod
    def evaluate_xpath_or_css(html_content: str, selector: str, is_xpath: bool = False) -> List[str]:
        """
        Surgical extraction using CSS selectors (or basic emulation).
        Note: BeautifulSoup primarily supports CSS selectors.
        """
        try:
            # We use lxml backend for speed and better parsing
            soup = BeautifulSoup(html_content, 'lxml')
            
            if is_xpath:
                # To support true XPath we would need lxml directly.
                # For this microscopic tool, we'll parse using lxml html.
                from lxml import html
                tree = html.fromstring(html_content)
                elements = tree.xpath(selector)
                # Convert lxml elements to string
                results = []
                for el in elements:
                    if isinstance(el, str):
                        results.append(el)
                    else:
                        from lxml import etree
                        results.append(etree.tostring(el, encoding='unicode', pretty_print=False))
                return results
            else:
                elements = soup.select(selector)
                return [str(el) for el in elements]
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return []

    @staticmethod
    def regex_extractor(text: str, pattern: str) -> List[str]:
        """
        Instantly pull structured data (emails, IDs, JSON fragments) from raw text.
        """
        try:
            return re.findall(pattern, text)
        except Exception as e:
            logger.error(f"Regex matching failed: {e}")
            return []

    @staticmethod
    def dom_skeleton_viewer(html_content: str) -> str:
        """
        Strips all text and scripts to return only the HTML tag structure.
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove all text nodes and script/style tags
            for script in soup(["script", "style", "meta", "link", "noscript", "svg"]):
                script.decompose()
                
            def strip_text(element):
                if hasattr(element, 'string') and element.string:
                    element.string.replace_with('')
                if hasattr(element, 'children'):
                    for child in element.children:
                        strip_text(child)
            
            strip_text(soup)
            
            return soup.prettify()
        except Exception as e:
            logger.error(f"Skeleton generation failed: {e}")
            return str(e)

    @staticmethod
    def ast_javascript_parser(js_code: str) -> Dict[str, Any]:
        """
        Extract variables, dictionary structures or JSON hidden in JS files.
        """
        try:
            obj_pattern = r'\{[\s\S]*\}'
            matches = re.findall(obj_pattern, js_code)
            
            extracted_objects = []
            for match in matches:
                try:
                    parsed = json.loads(match)
                    extracted_objects.append(parsed)
                except json.JSONDecodeError:
                    try:
                        fixed_str = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)(\s*:)', r'\1"\2"\3', match)
                        fixed_str = fixed_str.replace("'", '"')
                        parsed = json.loads(fixed_str)
                        extracted_objects.append(parsed)
                    except Exception:
                        pass
            
            return {
                "raw_js_length": len(js_code),
                "extracted_objects": extracted_objects
            }
        except Exception as e:
            logger.error(f"JS parsing failed: {e}")
            return {"error": str(e)}
