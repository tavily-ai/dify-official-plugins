from collections.abc import Generator, Mapping
from typing import Any

import requests
from dify_plugin.entities.datasource import (
    WebSiteInfo,
    WebSiteInfoDetail,
    WebsiteCrawlMessage,
)
from dify_plugin.interfaces.datasource.website import WebsiteCrawlDatasource

TAVILY_API_URL = "https://api.tavily.com"


class TavilyCrawlDatasource(WebsiteCrawlDatasource):
    def _get_website_crawl(
        self, datasource_parameters: Mapping[str, Any]
    ) -> Generator[WebsiteCrawlMessage, None, None]:
        """
        Crawl a website using Tavily Crawl API.
        """
        # Get API key from credentials
        api_key = self.runtime.credentials.get("tavily_api_key")
        if not api_key:
            raise ValueError("Tavily API key not found in credentials")

        # Get crawl parameters
        url = datasource_parameters.get("url", "").strip()
        if not url:
            raise ValueError("URL is required")

        instructions = datasource_parameters.get("instructions", "")
        max_depth = int(datasource_parameters.get("max_depth", 1))
        max_breadth = int(datasource_parameters.get("max_breadth", 20))
        limit = int(datasource_parameters.get("limit", 50))
        select_paths = datasource_parameters.get("select_paths", "")
        select_domains = datasource_parameters.get("select_domains", "")
        exclude_paths = datasource_parameters.get("exclude_paths", "")
        exclude_domains = datasource_parameters.get("exclude_domains", "")
        allow_external = datasource_parameters.get("allow_external", False)
        include_images = datasource_parameters.get("include_images", False)
        extract_depth = datasource_parameters.get("extract_depth", "basic")
        output_format = datasource_parameters.get("format", "markdown")
        include_favicon = datasource_parameters.get("include_favicon", False)
        timeout = int(datasource_parameters.get("timeout", 150))
        chunks_per_source = int(datasource_parameters.get("chunks_per_source", 3))

        try:
            # Initialize crawl result
            crawl_res = WebSiteInfo(web_info_list=[], status="", total=0, completed=0)

            # Start processing
            crawl_res.status = "processing"
            yield self.create_crawl_message(crawl_res)

            # Perform crawl using Tavily API
            crawl_results = self._perform_crawl(
                api_key=api_key,
                url=url,
                instructions=instructions,
                max_depth=max_depth,
                max_breadth=max_breadth,
                limit=limit,
                select_paths=select_paths,
                select_domains=select_domains,
                exclude_paths=exclude_paths,
                exclude_domains=exclude_domains,
                allow_external=allow_external,
                include_images=include_images,
                extract_depth=extract_depth,
                output_format=output_format,
                include_favicon=include_favicon,
                chunks_per_source=chunks_per_source,
                timeout=timeout,
            )

            if not crawl_results.get("results"):
                crawl_res.status = "completed"
                crawl_res.total = 0
                crawl_res.completed = 0
                yield self.create_crawl_message(crawl_res)
                return

            # Process crawl results
            web_info_list = []
            total_results = len(crawl_results["results"])
            crawl_res.total = total_results

            for idx, result in enumerate(crawl_results["results"]):
                try:
                    result_url = result.get("url", "")
                    content = result.get("raw_content", "")

                    web_info_detail = WebSiteInfoDetail(
                        source_url=result_url,
                        title="",
                        description="",
                        content=content,
                    )

                    web_info_list.append(web_info_detail)

                    # Update progress
                    crawl_res.completed = idx + 1
                    crawl_res.web_info_list = web_info_list
                    yield self.create_crawl_message(crawl_res)

                except Exception:
                    continue

            # Final result
            crawl_res.status = "completed"
            crawl_res.web_info_list = web_info_list
            crawl_res.total = len(web_info_list)
            crawl_res.completed = len(web_info_list)
            yield self.create_crawl_message(crawl_res)

        except Exception as e:
            raise ValueError(f"An error occurred: {str(e)}")

    def _perform_crawl(self, api_key: str, url: str, **kwargs) -> dict:
        """
        Perform crawl using Tavily Crawl API.
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Prepare crawl parameters
        crawl_params = {
            "url": url,
            "max_depth": kwargs.get("max_depth", 1),
            "max_breadth": kwargs.get("max_breadth", 20),
            "limit": kwargs.get("limit", 50),
            "extract_depth": kwargs.get("extract_depth", "basic"),
            "format": kwargs.get("output_format", "markdown"),
            "include_images": kwargs.get("include_images", False),
            "include_favicon": kwargs.get("include_favicon", False),
            "allow_external": kwargs.get("allow_external", False),
            "chunks_per_source": kwargs.get("chunks_per_source", 3),
        }

        # Add instructions if provided
        instructions = kwargs.get("instructions", "").strip()
        if instructions:
            crawl_params["instructions"] = instructions

        # Add path filters if provided
        select_paths = kwargs.get("select_paths", "").strip()
        if select_paths:
            crawl_params["select_paths"] = [
                path.strip() for path in select_paths.replace(",", " ").split() if path.strip()
            ]

        exclude_paths = kwargs.get("exclude_paths", "").strip()
        if exclude_paths:
            crawl_params["exclude_paths"] = [
                path.strip() for path in exclude_paths.replace(",", " ").split() if path.strip()
            ]

        # Add domain filters if provided
        select_domains = kwargs.get("select_domains", "").strip()
        if select_domains:
            crawl_params["select_domains"] = [
                domain.strip() for domain in select_domains.replace(",", " ").split() if domain.strip()
            ]

        exclude_domains = kwargs.get("exclude_domains", "").strip()
        if exclude_domains:
            crawl_params["exclude_domains"] = [
                domain.strip() for domain in exclude_domains.replace(",", " ").split() if domain.strip()
            ]

        timeout = kwargs.get("timeout", 150)
        # Ensure timeout is within valid range (10-150)
        timeout = max(10, min(150, timeout))

        response = requests.post(
            f"{TAVILY_API_URL}/crawl",
            json=crawl_params,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

