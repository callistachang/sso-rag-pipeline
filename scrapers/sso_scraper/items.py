# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from dataclasses import dataclass


@dataclass
class SsoAct:
    html_content = str
    shorthand = str  # e.g. AA1966
    title = str  # e.g. "Audit Act 1966"
