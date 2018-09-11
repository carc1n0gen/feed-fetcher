#!/usr/bin/env python

import time
from hashlib import md5
from optparse import OptionParser
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime
import sqlite3
import yaml
import feedparser

parser = OptionParser()
parser.add_option("-f", "--feeds", dest="feed_file", help="Path to yaml file containing a list of feeds.")
parser.add_option("-d", "--database", dest="database", help="Path to sqlite database for tracking already parsed feeds")
parser.add_option("-t", "--template_dir", dest="template", help="Path to a directory containing jinja2 templates.")
parser.add_option("-o", "--output", dest="output", help="Path to directory to generate a static site.")
(options, args) = parser.parse_args()

FEED_FILE = options.feed_file
DATABASE = options.database
TEMPLATE_DIR = options.template
OUTPUT = options.output

if not FEED_FILE or not DATABASE or not TEMPLATE_DIR or not OUTPUT:
    parser.print_help()
    exit(1)

connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row
result = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feeds'")
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
    connection.execute("CREATE UNIQUE INDEX feeds_url_md5_index ON feeds(url_md5)")
    connection.execute(
        """CREATE TABLE settings (
        key VARCHAR(255) PRIMARY KEY,
        val VARCHAR(255) )"""
    )
    connection.commit()
    print("Database initialized.")

jinja = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)
jinja.filters["date"] = lambda s: datetime.strptime(s, '%Y-%m-%dT%H:%M:%S').strftime("%A, %B %d, %Y")

with open(FEED_FILE, "r") as stream:
    for feed_url in yaml.load(stream):
        feed = feedparser.parse(feed_url)
        for item in feed["entries"]:
            m = md5(item["link"].encode("utf-8")).hexdigest()
            result = connection.execute("SELECT * FROM feeds WHERE url_md5 = :m", { "m": m })
            if result.fetchone() is None:
                if "content" in item:
                    content = item["content"][0]["value"]
                else:
                    content = item["summary"]
                connection.execute(
                    """INSERT INTO feeds (
                        url, url_md5, title, site_url, site_title, date, content
                    ) VALUES (
                        :url, :url_md5, :title, :site_url, :site_title, :date, :content
                    )""", {
                        "url": item["link"],
                        "url_md5": m,
                        "title": item["title"],
                        "site_url": feed["feed"]["link"],
                        "site_title": feed["feed"]["title"],
                        "date": datetime.fromtimestamp(time.mktime(item["updated_parsed"])).isoformat(),
                        "content": item["summary"]
                    }
                )

connection.commit()
result = connection.execute("SELECT * FROM feeds ORDER BY date DESC LIMIT 100")
template = jinja.get_template('template.html', globals={ "items": result })
with open("{}/index.html".format(OUTPUT), "wb") as stream:
    stream.write(template.render().encode('utf-8'))
connection.close()
