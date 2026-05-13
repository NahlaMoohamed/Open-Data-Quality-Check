"""Bayanat Portal API Client"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BayanatClient:
    """Client for interacting with Bayanat open data portal API"""

    def __init__(self, base_url: str = "https://bayanat.ae/api/3", timeout: int = 30):
        """
        Initialize Bayanat API client
        
        Args:
            base_url: Base URL for Bayanat API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def get_datasets(
        self,
        organization: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Fetch datasets from Bayanat portal
        
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
        Fetch detailed information about a specific dataset
        
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
