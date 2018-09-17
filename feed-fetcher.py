#!/usr/bin/env python

import time
from hashlib import md5
from optparse import OptionParser
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, timedelta
import sqlite3
import yaml
import feedparser
import threading

parser = OptionParser()
parser.add_option("-f", "--feeds", dest="feed_file",
                  help="Path to yaml file containing a list of feeds.")
parser.add_option("-d", "--database", dest="database",
                  help="Path to sqlite database for tracking already parsed \
                  feeds")
parser.add_option("-t", "--template_dir", dest="template",
                  help="Path to a directory containing jinja2 templates.")
parser.add_option("-o", "--output", dest="output",
                  help="Path to directory to generate a static site.")
(options, args) = parser.parse_args()

FEED_FILE = options.feed_file
DATABASE = options.database
TEMPLATE_DIR = options.template
OUTPUT = options.output

if not FEED_FILE or not DATABASE or not TEMPLATE_DIR or not OUTPUT:
    parser.print_help()
    exit(1)


def initialize_and_connect_database(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    result = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='feeds'")
    if result.fetchone() is None:
        connection.execute(
            """CREATE TABLE feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url VARCHAR(2000),
            url_md5 CHAR(32),
            title VARCHAR(2000),
            site_url VARCHAR(2000),
            site_title VARCHAR(2000),
            date DATETIME,
            content TEXT )"""
        )
        connection.execute(
            "CREATE UNIQUE INDEX feeds_url_md5_index ON feeds(url_md5)")
        connection.execute(
            """CREATE TABLE settings (
            key VARCHAR(255) PRIMARY KEY,
            val VARCHAR(255) )"""
        )
        connection.commit()
    result.close()
    return connection


def thread_wrapper(func, args, res):
    res.append(func(*args))


def fetch_and_parse_feeds(urls):
    feeds = []
    threads = [threading.Thread(target=thread_wrapper, args=(
        feedparser.parse, (url,), feeds,)) for url in urls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return feeds


def check_and_cache_feed(feed, db_connection):
    for item in feed["entries"]:
        m = md5(item["link"].encode("utf-8")).hexdigest()
        result = db_connection.execute(
            "SELECT * FROM feeds WHERE url_md5 = :m", {"m": m})
        if result.fetchone() is None:
            if "title" not in item:
                title = ""
            else:
                title = item["title"]

            if "content" in item:
                content = item["content"][0]["value"]
            else:
                content = item["summary"]

            if "published_parsed" in item:
                date = item["published_parsed"]
            else:
                date = item["updated_parsed"]

            db_connection.execute(
                """INSERT INTO feeds (
                    url,
                    url_md5,
                    title,
                    site_url,
                    site_title,
                    date,
                    content
                ) VALUES (
                    :url,
                    :url_md5,
                    :title,
                    :site_url,
                    :site_title,
                    :date,
                    :content
                )""", {
                    "url": item["link"],
                    "url_md5": m,
                    "title": title,
                    "site_url": feed["feed"]["link"],
                    "site_title": feed["feed"]["title"],
                    "date":
                        datetime.fromtimestamp(time.mktime(date)).isoformat(),
                    "content": content
                }
            )
        result.close()


def write_static_page(path, title, template, items):
    with open(path, "wb") as stream:
        stream.write(template.render(items=items, title=title).encode("utf-8"))


connection = initialize_and_connect_database(DATABASE)
with open(FEED_FILE, "r") as yaml_file:
    for feed in fetch_and_parse_feeds(yaml.load(yaml_file)):
        check_and_cache_feed(feed, connection)
connection.commit()

jinja = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)
jinja.filters["date"] = lambda s: datetime.strptime(
    s, "%Y-%m-%dT%H:%M:%S").strftime("%A, %B %d, %Y")
template = jinja.get_template("template.html")

for page in [{
    "title": "Today",
    "file": "index.html",
    "query": ("SELECT * FROM feeds WHERE date > :today ORDER BY date DESC", {
        "today": datetime.now().strftime("%Y-%m-%d")
    })
}, {
    "title": "Yesterday",
    "file": "yesterday.html",
    "query": ("SELECT * FROM feeds WHERE date > :yesterday AND date < :today \
                ORDER BY date DESC", {
        "yesterday": datetime.strftime(datetime.now() - timedelta(1),
                                       "%Y-%m-%d"),
        "today": datetime.now().strftime("%Y-%m-%d")
    })
}, {
    "title": "Latest 100",
    "file": "latest100.html",
    "query": ("SELECT * FROM feeds ORDER BY date DESC LIMIT 100", {})
}]:
    items = connection.execute(page["query"][0], page["query"][1])
    write_static_page(
        "{}/{}".format(OUTPUT, page["file"]), page["title"], template, items)
    items.close()

connection.close()
