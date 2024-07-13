import os
from datetime import datetime, timedelta
from typing import Literal

import requests
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator


class Product:
    def __init__(
        self,
        id: str,
        name: str,
        tagline: str,
        url: str,
        votesCount: int,
        featuredAt: str | None,
        createdAt: str | None,
        website: str,
        **kwargs,
    ):
        self.name = name
        self.tagline = tagline
        self.url = url
        self.votes_count = votesCount
        self.featured_at = datetime.fromisoformat(featuredAt) if featuredAt else None
        self.created_at = datetime.fromisoformat(createdAt) if createdAt else None
        self.id = id
        self.website = website

        self.full_name = f"{self.name} - {self.tagline}"

        self.__dict__.update(kwargs)  # Add kwargs as class attributes just in case

    @property
    def feed_entry(self):
        fe = FeedEntry()
        fe.author({"name": "Product Hunt"})
        fe.summary(self.tagline)
        fe.published(self.created_at)
        fe.updated(self.featured_at)
        fe.title(self.full_name)
        fe.id(self.url)
        fe.link({"href": self.url, "title": "Product Hunt", "rel": "alternate"})
        fe.content(
            f"""
<b>{self.name}</b>
<br />
{self.tagline}
<br />
🔼 {self.votes_count} votes
<br/>
<br/> 
<a href="{self.url}">[Product Hunt page]</a>
<br />
<br />
<a href="{self.website}">[Website]</a>
        """,
            type="html",
        )

        return fe

    def __repr__(self) -> str:
        return f"{self.name} | {self.votes_count} | {self.featured_at}"


class ProductHunt:
    def __init__(self):
        self.client_id = os.getenv("PH_CLIENT_ID")
        self.client_secret = os.getenv("PH_CLIENT_SECRET")

        self.token = self._generate_token()

        self.products = []

        self._fetch_products()

    def _generate_token(self) -> str:
        url = "https://api.producthunt.com/v2/oauth/token"

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        response = requests.post(url, json=payload)

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()["access_token"]

    def _fetch_products(self):
        url = "https://api.producthunt.com/v2/api/graphql"

        headers = {"Authorization": f"Bearer {self.token}"}

        cursor = ""
        has_next_page = True
        date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

        while has_next_page:
            query = """
            {
              posts(order: FEATURED_AT, postedAfter: "%s", after: "%s" ) {
                  nodes {
                    id
                    name
                    tagline
                    votesCount
                    featuredAt
                    createdAt
                    url
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            """ % (
                date,
                cursor,
            )

            response = requests.post(url, headers=headers, json={"query": query})

            if response.status_code != 200:
                raise Exception(response.text)

            data = response.json().get("data", {}).get("posts", {})
            posts = data.get("nodes", {})

            for post in posts:
                self.products.append(Product(**post))

            has_next_page = data.get("pageInfo", {}).get("hasNextPage", False)
            cursor = data.get("pageInfo", {}).get("endCursor", "")

    def _get_products(
        self,
        max_items: int = 0,
        sort_by: Literal["votes", "featured_at"] = "featured_at",
        *args,
        **kwargs,
    ):
        def sort_by_vote(e: Product):
            return e.votes_count

        def sort_by_featured_at(e: Product):
            return e.featured_at

        if sort_by == "votes":
            items = sorted(self.products, key=sort_by_vote, reverse=True)
        elif sort_by == "featured_at":
            items = [product for product in self.products if product.featured_at]
            items = sorted(items, key=sort_by_featured_at, reverse=True)
        else:
            items = self.products

        if max_items > 0:
            items = items[:max_items]

        return items

    def generate_feed(self, *args, **kwargs):
        fg = FeedGenerator()
        fg.id("https://www.producthunt.com/")
        fg.title("Some Testfeed")
        fg.author([{"name": "Product Hunt"}, {"name": "Herculino Trotta"}])
        fg.logo("https://ph-static.imgix.net/ph-favicon-coral.ico")
        fg.subtitle("This is a cool feed!")
        fg.language("en")

        products = self._get_products(*args, **kwargs)

        for product in products:
            fg.add_entry(product.feed_entry)
        fg.atom_file("teste.atom", pretty=True)


if __name__ == "__main__":
    ph = ProductHunt()
    ph.generate_feed(max_items=10, sort_by="featured_at")
