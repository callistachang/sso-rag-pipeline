from pathlib import Path
import scrapy
from scrapy.http.response.html import HtmlResponse
from urllib.parse import urlparse, urlunparse, urlencode
import requests
import json
import logging
from bs4 import BeautifulSoup
from sso_scraper.cleaner import clean_data

# TODO: this class does everything (scraping and data cleaning) at the moment, but it's
# probably better to separate it out at some point
# TODO: multithread this
class SsoSpider(scrapy.Spider):
    """
    Scrapes the HTML files of all current acts of the Parliament of Singapore from the
    Singapore Statutes Online (SSO) website at https://sso.agc.gov.sg.

    Scraped HTML files are saved into a specified data folder.
    """

    name = "sso"
    start_urls = [
        "https://sso.agc.gov.sg/Browse/Act/Current/All?PageSize=500&SortBy=Title&SortOrder=ASC",
        "https://sso.agc.gov.sg/Browse/Act/Current/1?PageSize=500&SortBy=Title&SortOrder=ASC",
    ]
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    raw_html_folder = "./out_html"  # TODO: parametrize this
    cleaned_text_folder = "./cleaned_text"  # TODO: parametrize this

    def __init__(self, *args, **kwargs):
        super(SsoSpider, self).__init__(*args, **kwargs)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    def parse(self, response: HtmlResponse):
        """
        Retrieves from the page all links to acts, and parses each act.
        """

        def has_query_params(url: str) -> bool:
            parsed_url = urlparse(url)
            return bool(parsed_url.query)

        links = response.xpath("//table[@class='table browse-list']//tr/td/a/@href").getall()
        unique_links = set()
        for link in links:
            if not has_query_params(link) and (link not in unique_links):
                unique_links.add(link)
                yield response.follow(link, callback=self.parse_act)
        # TODO: write code to dynamically find the next page to parse instead of
        # hardcoding `self.start_urls`, but this should be fine for now

    def parse_act(self, response: HtmlResponse):
        html_content = self._retrieve_full_act_html(response)

        shorthand = response.url.split("/")[-1]
        human_readable_title = (
            response.xpath("//div[@class='legis-title']/div/text()").get().replace(" ", "-")
        )
        filestem = f"{shorthand}-{human_readable_title}"

        self._write_to_file(self.raw_html_folder, html_content, f"{filestem}.html")
        cleaned_text_content = clean_data(html_content)
        self._write_to_file(self.cleaned_text_folder, cleaned_text_content, f"{filestem}.txt")

        self.log(f"saved to file {filestem}")

    def _retrieve_full_act_html(self, response: HtmlResponse) -> str:
        """
        Scrapes the full content in the link of the act.

        Most later parts of the act are lazy loaded, which means we need to visit each lazy loaded part
        and concatenate their contents into one HTML page.

        The links to lazy loaded parts can be constructed from a hidden component found in the
        act's 'home' link.
        """
        first_part = "".join(response.xpath("//div[@class='prov1']").getall())
        for fragment_details in response.xpath("//div[@class='global-vars']/@data-json"):
            data = json.loads(fragment_details.get())
            if "tocSysId" in data and "fragments" in data:
                break  # found details about lazy loaded parts
        else:
            # no details on lazy loaded parts, return just the first part
            return first_part

        series_ids = response.xpath("//div[@data-field='seriesId']/@data-term").getall()
        assert (
            len(series_ids) > 0
        ), "if fragment details are available, there should be at least one series ID to parse"

        parts = [first_part]
        for series_id in series_ids:
            lazy_loaded_part_url = self._generate_lazy_loaded_part_link(
                toc_sys_id=data["tocSysId"],
                series_id=series_id,
                frag_sys_id=data["fragments"][series_id]["Item1"],
                datetime_id=data["fragments"][series_id]["Item2"],
            )
            part_html = self._retrieve_lazy_loaded_part_html(lazy_loaded_part_url)
            parts.append(part_html)

        # the contents of the page use an unorthodox character to represent spaces, we replace it
        return self._combine_parts(parts).replace("\xa0", " ")

    def _generate_lazy_loaded_part_link(self, toc_sys_id, series_id, frag_sys_id, datetime_id):
        params = {
            "TocSysId": toc_sys_id,
            "SeriesId": series_id,
            "ValidTime": "",
            "TransactionTime": "",
            "ViewType": "",
            "V": 25,
            "Phrase": "",
            "Exact": "",
            "Any": "",
            "Without": "",
            "WiAl": "",
            "WiPr": "",
            "WiLT": "",
            "WiSc": "",
            "WiDT": "",
            "WiDH": "",
            "WiES": "",
            "WiPH": "",
            "RefinePhrase": "",
            "RefineWithin": "",
            "CustomSearchId": "",
            "FragSysId": frag_sys_id,
            "_": datetime_id,
        }
        base_url = urlparse("https://sso.agc.gov.sg/Details/GetLazyLoadContent")
        url_with_params = urlunparse(base_url._replace(query=urlencode(params)))
        return url_with_params

    def _write_to_file(self, folder: str, content: str, filename: str):
        full_path = Path(self.raw_html_folder) / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)  # ensure dir `self.data_folder` exists
        full_path.write_text(content)

    def _retrieve_lazy_loaded_part_html(self, url: str):
        response = requests.get(url, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        return response.text

    def _combine_parts(self, parts: list[str]):
        first, *remaining = parts
        return first + "".join(remaining)
