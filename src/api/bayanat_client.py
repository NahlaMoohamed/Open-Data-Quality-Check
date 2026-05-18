"""Bayanat Portal API Client"""

import requests
import logging
import re
import json
from html import unescape
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BayanatClient:
    """Client for interacting with Bayanat open data portal API"""

    def __init__(
        self,
        base_url: str = "https://bayanat.ae/api/3",
        site_base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize Bayanat API client
        
        Args:
            base_url: Base URL for Bayanat API
            site_base_url: Public website base URL for scraping
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.site_base_url = site_base_url or "https://bayanat.ae"
        self.timeout = timeout
        self.session = requests.Session()

    def get_datasets(
        self,
        organization: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Fetch datasets from the Bayanat CKAN API.
        
        Args:
            organization: Filter by organization name (optional)
            limit: Number of datasets to fetch
            offset: Offset for pagination
            
        Returns:
            Dictionary containing datasets data
        """
        try:
            params = {
                "limit": limit,
                "offset": offset,
            }
            
            if organization:
                params["organization"] = organization

            response = self.session.get(
                f"{self.base_url}/package_search",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching datasets: {e}")
            raise

    def get_dataset_details(self, dataset_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information about a specific dataset via CKAN API.
        
        Args:
            dataset_id: ID of the dataset
            
        Returns:
            Dictionary containing dataset details
        """
        try:
            response = self.session.get(
                f"{self.base_url}/package_show",
                params={"id": dataset_id},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching dataset {dataset_id}: {e}")
            raise

    def get_dataset_page_html(self, dataset_identifier: str) -> str:
        """
        Load the public dataset page HTML for scraping.
        """
        if dataset_identifier.startswith("http"):
            page_url = dataset_identifier
        elif "Dataset-info" in dataset_identifier or "dataset?id=" in dataset_identifier:
            page_url = dataset_identifier if dataset_identifier.startswith("http") else f"{self.site_base_url}/{dataset_identifier.lstrip('/')}"
        else:
            page_url = f"{self.site_base_url}/en/Datasets/Dataset-info?id={dataset_identifier}"

        logger.info(f"Scraping dataset page: {page_url}")
        response = self.session.get(page_url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _normalize_url(self, url: str, base_url: Optional[str] = None) -> str:
        if not url:
            return ""
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("http"):
            return url
        base = base_url or self.site_base_url
        return f"{base.rstrip('/')}/{url.lstrip('/')}"

    def _strip_tags(self, html: str) -> str:
        if not html:
            return ""
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.I | re.S)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", "", text)
        return unescape(text).strip()

    def _extract_first_text(self, html: str, patterns: List[str]) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.I | re.S)
            if match:
                text = match.group(1)
                if text:
                    return self._strip_tags(text).strip()
        return None

    def get_resource_page_html(self, resource_url: str) -> str:
        page_url = self._normalize_url(resource_url)
        logger.info(f"Scraping resource page: {page_url}")
        response = self.session.get(page_url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def scrape_resource_page(self, resource_url: str) -> Dict[str, Any]:
        html = self.get_resource_page_html(resource_url)
        resource_data = {
            "name": None,
            "description": None,
            "resource_guid": None,
        }

        resource_data["name"] = self._extract_first_text(
            html,
            [r"<h1[^>]*>(.*?)</h1>", r"<title[^>]*>(.*?)</title>", r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"'](.*?)[\"']"],
        )
        resource_data["description"] = self._extract_first_text(
            html,
            [
                r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"'](.*?)[\"']",
                r"<meta[^>]+property=[\"']og:description[\"'][^>]+content=[\"'](.*?)[\"']",
                r"<div[^>]+class=[\"'][^\"']*(?:description|resource-description|summary)[^\"']*[\"'][^>]*>(.*?)</div>",
                r"<p[^>]+class=[\"'][^\"']*(?:description|summary|resource-summary)[^\"']*[\"'][^>]*>(.*?)</p>",
            ],
        )

        guid_match = re.search(r"(?:rid|resourceID)=([0-9A-Za-z_\-]+)", html)
        if guid_match:
            resource_data["resource_guid"] = guid_match.group(1)

        return resource_data

    def scrape_dataset_page(self, dataset_identifier: str) -> Dict[str, Any]:
        """
        Scrape dataset metadata and resource GUIDs from the public website.
        """
        html = self.get_dataset_page_html(dataset_identifier)
        dataset = {
            "id": dataset_identifier,
            "title": None,
            "name": dataset_identifier,
            "organization": None,
            "description": None,
            "resources": [],
            "resource_guids": [],
        }

        def add_resource(url: str, guid: Optional[str] = None, name: Optional[str] = None, description: Optional[str] = None, format: Optional[str] = None):
            if not url:
                return
            normalized_url = self._normalize_url(url)
            if not normalized_url:
                return

            if not name:
                name = f"resource_{len(dataset['resources']) + 1}"

            if guid and any(r.get('resource_guid') == guid for r in dataset['resources']):
                return

            resource = {
                "name": name.strip(),
                "description": description or None,
                "format": format,
                "url": normalized_url,
            }
            if guid:
                resource["resource_guid"] = guid
                if guid not in dataset["resource_guids"]:
                    dataset["resource_guids"].append(guid)

            dataset["resources"].append(resource)

        ld_json_matches = re.findall(
            r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
            html,
            flags=re.I | re.S,
        )
        for raw_json in ld_json_matches:
            try:
                data = json.loads(raw_json.strip())
                if isinstance(data, dict):
                    dataset["title"] = dataset["title"] or data.get("name")
                    dataset["description"] = dataset["description"] or data.get("description")
                    publisher = data.get("publisher")
                    if isinstance(publisher, dict):
                        dataset["organization"] = dataset["organization"] or publisher.get("name")
                    elif isinstance(publisher, str):
                        dataset["organization"] = dataset["organization"] or publisher

                    distributions = data.get("distribution") or data.get("offers")
                    if isinstance(distributions, list):
                        for dist in distributions:
                            identifier = dist.get("identifier") or dist.get("contentUrl") or dist.get("url")
                            guid = None
                            if isinstance(identifier, str):
                                guid_match = re.search(r"(?:rid|resourceID|ResourceGUID)=([0-9A-Za-z_\-]+)", identifier)
                                if guid_match:
                                    guid = guid_match.group(1)
                            add_resource(
                                url=dist.get("contentUrl") or dist.get("url"),
                                guid=guid,
                                name=dist.get("name") or dist.get("description") or None,
                                description=dist.get("description"),
                                format=dist.get("encodingFormat"),
                            )
            except json.JSONDecodeError:
                continue

        if not dataset["title"]:
            dataset["title"] = self._extract_first_text(
                html,
                [
                    r"<h1[^>]*>(.*?)</h1>",
                    r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"'](.*?)[\"']",
                ],
            )

        if not dataset["description"]:
            dataset["description"] = self._extract_first_text(
                html,
                [
                    r"<div[^>]+class=[\"'][^\"']*(?:dataset[-_ ]description|description|summary|about|detail[-_ ]description)[^\"']*[\"'][^>]*>(.*?)</div>",
                    r"<p[^>]+class=[\"'][^\"']*(?:dataset[-_ ]description|description|summary|about|detail[-_ ]description)[^\"']*[\"'][^>]*>(.*?)</p>",
                    r"<div[^>]+id=[\"']description[\"'][^>]*>(.*?)</div>",
                    r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"'](.*?)[\"']",
                    r"<meta[^>]+property=[\"']og:description[\"'][^>]+content=[\"'](.*?)[\"']",
                ],
            )

        if not dataset["organization"]:
            dataset["organization"] = self._extract_first_text(
                html,
                [
                    r"(?:Entity Name|Entity|Organization|Publisher|Owner|Owner Name|الجهة|المؤسسة|المنظمة)\s*[:\-]?\s*</?[^>]*>\s*(.*?)<",
                    r"<(?:span|div|p)[^>]+class=[\"'][^\"']*(?:entity|organization|publisher|org|owner|owner-name|entity-name)[^\"']*[\"'][^>]*>(.*?)</(?:span|div|p)>",
                    r"<div[^>]+id=[\"']entity-name[\"'][^>]*>(.*?)</div>",
                ],
            )

        for match in re.finditer(
            r"href=[\"']([^\"']*(?:rid|resourceID|ResourceGUID)=[^\"']*)[\"'][^>]*>(.*?)</a>",
            html,
            flags=re.I | re.S,
        ):
            url = match.group(1)
            label = self._strip_tags(match.group(2))
            guid_match = re.search(r"(?:rid|resourceID|ResourceGUID)=([0-9A-Za-z_\-]+)", url)
            guid = guid_match.group(1) if guid_match else None
            add_resource(url=url, guid=guid, name=label or None)

        if not dataset["resources"]:
            matches = re.findall(r"(?:rid|resourceID|ResourceGUID)=([0-9A-Za-z_\-]+)", html, flags=re.I)
            for guid in matches:
                if guid not in dataset["resource_guids"]:
                    add_resource(
                        url=f"{self.site_base_url}/api/DatasetResources/GetDatasetResource?resourceID={guid}",
                        guid=guid,
                    )

        if not dataset["resources"]:
            data_attrs = re.findall(
                r"(?:data-rid|data-resource-id|data-guid|data-resourceguid)[\"']?\s*[:=]\s*[\"']([0-9A-Za-z_\-]+)[\"']",
                html,
                flags=re.I,
            )
            for guid in data_attrs:
                if guid not in dataset["resource_guids"]:
                    add_resource(
                        url=f"{self.site_base_url}/api/DatasetResources/GetDatasetResource?resourceID={guid}",
                        guid=guid,
                    )

        for resource in dataset["resources"]:
            if resource.get("url") and "/visualization" in resource.get("url"):
                try:
                    details = self.scrape_resource_page(resource["url"])
                    if details.get("name"):
                        resource["name"] = resource["name"] or details["name"]
                    if details.get("description"):
                        resource["description"] = resource["description"] or details["description"]
                    if details.get("resource_guid") and not resource.get("resource_guid"):
                        resource["resource_guid"] = details["resource_guid"]
                        if details["resource_guid"] not in dataset["resource_guids"]:
                            dataset["resource_guids"].append(details["resource_guid"])
                except Exception as e:
                    logger.debug(f"Unable to scrape resource page {resource.get('url')}: {e}")

        dataset["resource_guids"] = list(dict.fromkeys(dataset["resource_guids"]))
        return dataset

    def get_dataset_resource_guids(self, dataset_name: str) -> List[str]:
        """
        Scrape the public dataset page for resource GUIDs.
        
        Args:
            dataset_name: Dataset slug or name used in the website URL
        
        Returns:
            List of discovered resource GUIDs
        """
        try:
            page_url = f"{self.site_base_url}/en/Datasets/Dataset-info?id={dataset_name}"
            logger.info(f"Scraping dataset page for resource GUIDs: {page_url}")
            response = self.session.get(page_url, timeout=self.timeout)
            response.raise_for_status()
            html = response.text

            guids = re.findall(r"resourceID=([0-9A-Za-z_\-]+)", html)
            if not guids:
                guids.extend(
                    re.findall(
                        r"ResourceGUID[\"']?\s*[:=]\s*[\"']?([0-9A-Za-z_\-]+)",
                        html,
                        flags=re.IGNORECASE,
                    )
                )
                guids.extend(
                    re.findall(
                        r"resource_guid[\"']?\s*[:=]\s*[\"']?([0-9A-Za-z_\-]+)",
                        html,
                        flags=re.IGNORECASE,
                    )
                )

            if not guids:
                page_url = f"{self.site_base_url}/dataset/{dataset_name}"
                logger.info(f"Scraping fallback dataset page for resource GUIDs: {page_url}")
                response = self.session.get(page_url, timeout=self.timeout)
                response.raise_for_status()
                html = response.text

                guids.extend(
                    re.findall(r"resourceID=([0-9A-Za-z_\-]+)", html)
                )
                guids.extend(
                    re.findall(
                        r"ResourceGUID[\"']?\s*[:=]\s*[\"']?([0-9A-Za-z_\-]+)",
                        html,
                        flags=re.IGNORECASE,
                    )
                )
                guids.extend(
                    re.findall(
                        r"resource_guid[\"']?\s*[:=]\s*[\"']?([0-9A-Za-z_\-]+)",
                        html,
                        flags=re.IGNORECASE,
                    )
                )

            unique_guids = list(dict.fromkeys(guids))
            logger.info(
                f"Found {len(unique_guids)} resource GUID(s) for dataset {dataset_name}"
            )
            return unique_guids
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping dataset page {dataset_name}: {e}")
            return []

    def attach_resource_guids_to_dataset(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich the dataset payload with resource GUIDs from the public website.
        
        Args:
            dataset: Dataset object from API
        
        Returns:
            Dataset object with added `resource_guids` and optional per-resource `resource_guid`
        """
        dataset_name = dataset.get("name") or dataset.get("id")
        if not dataset_name:
            return dataset

        guids = dataset.get("resource_guids") or self.scrape_dataset_page(dataset_name).get("resource_guids", [])
        resources = dataset.get("resources", [])

        if guids:
            dataset["resource_guids"] = guids
            if len(resources) == 0:
                for idx, guid in enumerate(guids, start=1):
                    resources.append({
                        "name": f"resource_{idx}",
                        "resource_guid": guid,
                    })
                dataset["resources"] = resources

            if len(guids) == len(resources):
                for resource, guid in zip(resources, guids):
                    resource["resource_guid"] = guid
            elif len(guids) == 1 and len(resources) == 1:
                resources[0]["resource_guid"] = guids[0]

        return dataset

    def download_resource_by_guid(self, resource_guid: str, save_path: str) -> bool:
        """
        Download a resource file using its GUID.
        
        Args:
            resource_guid: GUID from developer experience section
            save_path: Path to save the downloaded file
        
        Returns:
            True if the file was downloaded successfully
        """
        if not resource_guid:
            logger.error("Missing resource GUID for download")
            return False

        endpoint = f"{self.site_base_url}/api/DatasetResources/GetDatasetResource"
        try:
            response = self.session.get(
                endpoint,
                params={"resourceID": resource_guid},
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(
                f"Downloaded resource GUID {resource_guid} to {save_path}"
            )
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading resource {resource_guid}: {e}")
            return False

    def _read_response_preview(self, response: requests.Response, max_bytes: int = 200000) -> str:
        content = b""
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    break
                content += chunk
                if len(content) >= max_bytes:
                    break
        except requests.exceptions.RequestException as e:
            logger.error(f"Error reading response preview: {e}")
            return ""

        encoding = response.encoding or "utf-8"
        try:
            return content.decode(encoding, errors="replace")
        except Exception:
            return content.decode("utf-8", errors="replace")

    def fetch_resource_preview_by_guid(
        self, resource_guid: str, max_bytes: int = 200000
    ) -> str:
        endpoint = f"{self.site_base_url}/api/DatasetResources/GetDatasetResource"
        try:
            response = self.session.get(
                endpoint,
                params={"resourceID": resource_guid},
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()
            return self._read_response_preview(response, max_bytes=max_bytes)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error previewing resource {resource_guid}: {e}")
            return ""

    def fetch_resource_preview_by_url(
        self, resource_url: str, max_bytes: int = 200000
    ) -> str:
        try:
            response = self.session.get(resource_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            return self._read_response_preview(response, max_bytes=max_bytes)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error previewing resource URL {resource_url}: {e}")
            return ""

    def get_organizations(self) -> Dict[str, Any]:
        """
        Fetch list of organizations
        
        Returns:
            Dictionary containing organizations data
        """
        try:
            response = self.session.get(
                f"{self.base_url}/organization_list",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching organizations: {e}")
            raise

    def get_organization_datasets(self, org_id: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Fetch all datasets for a specific organization
        
        Args:
            org_id: Organization ID
            limit: Number of datasets to fetch
            
        Returns:
            Dictionary containing organization's datasets
        """
        try:
            response = self.session.get(
                f"{self.base_url}/organization_show",
                params={"id": org_id, "include_datasets": True},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching organization {org_id}: {e}")
            raise

    def download_resource(self, resource_url: str, save_path: str) -> bool:
        """
        Download a resource from the portal
        
        Args:
            resource_url: URL of the resource
            save_path: Path to save the downloaded file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(
                resource_url,
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()
            
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Successfully downloaded resource to {save_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading resource: {e}")
            return False

    def close(self):
        """Close the session"""
        self.session.close()
