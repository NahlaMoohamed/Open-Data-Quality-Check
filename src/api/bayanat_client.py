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
                            resource = {
                                "name": dist.get("name") or dist.get("description") or "resource",
                                "description": dist.get("description") or None,
                                "format": dist.get("encodingFormat"),
                                "url": dist.get("contentUrl") or dist.get("url"),
                            }
                            identifier = dist.get("identifier") or resource["url"]
                            if isinstance(identifier, str):
                                guid_match = re.search(r"([0-9a-fA-F\-]{36})", identifier)
                                if guid_match:
                                    resource["resource_guid"] = guid_match.group(1)
                            dataset["resources"].append(resource)
            except json.JSONDecodeError:
                continue

        if not dataset["title"]:
            title_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.I | re.S)
            if title_match:
                dataset["title"] = unescape(title_match.group(1).strip())

        if not dataset["description"]:
            desc_match = re.search(
                r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"'](.*?)[\"']",
                html,
                flags=re.I | re.S,
            )
            if desc_match:
                dataset["description"] = unescape(desc_match.group(1).strip())

        if not dataset["organization"]:
            org_match = re.search(
                r"(?:Organization|Publisher)\s*[:\-]\s*</?strong>?\s*(.*?)<",
                html,
                flags=re.I | re.S,
            )
            if org_match:
                dataset["organization"] = unescape(org_match.group(1).strip())

        resource_guids = []
        for match in re.finditer(
            r"href=[\"']([^\"']*resourceID=([0-9a-fA-F\-]{36})[^\"']*)[\"'][^>]*>(.*?)</a>",
            html,
            flags=re.I | re.S,
        ):
            url = match.group(1)
            guid = match.group(2)
            label = unescape(re.sub(r"<.*?>", "", match.group(3)).strip())
            if guid not in resource_guids:
                resource_guids.append(guid)
            dataset["resources"].append({
                "name": label or f"resource_{len(dataset['resources']) + 1}",
                "resource_guid": guid,
                "url": url,
            })

        if not resource_guids:
            raw_guids = re.findall(r"resourceID=([0-9a-fA-F\-]{36})", html)
            raw_guids += re.findall(
                r"ResourceGUID[\"']?\s*[:=]\s*[\"']?([0-9a-fA-F\-]{36})",
                html,
                flags=re.I,
            )
            raw_guids += re.findall(
                r"resource_guid[\"']?\s*[:=]\s*[\"']?([0-9a-fA-F\-]{36})",
                html,
                flags=re.I,
            )
            for guid in raw_guids:
                if guid not in resource_guids:
                    resource_guids.append(guid)
                    dataset["resources"].append({
                        "name": f"resource_{len(dataset['resources']) + 1}",
                        "resource_guid": guid,
                    })

        dataset["resource_guids"] = resource_guids
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
