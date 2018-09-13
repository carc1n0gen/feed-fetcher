#!/usr/bin/env python

import time
from hashlib import md5
from optparse import OptionParser
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, timedelta
import sqlite3
import yaml
import feedparser
import asyncio
import threading

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

# connection = sqlite3.connect(DATABASE)
# connection.row_factory = sqlite3.Row
# result = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feeds'")
# if result.fetchone() is None:
#     connection.execute(
#         """CREATE TABLE feeds (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         url VARCHAR(2000),
#         url_md5 CHAR(32),
#         title VARCHAR(2000),
#         site_url VARCHAR(2000),
#         site_title VARCHAR(2000),
#         date DATETIME,
#         content TEXT )"""
#     )
#     connection.execute("CREATE UNIQUE INDEX feeds_url_md5_index ON feeds(url_md5)")
#     connection.execute(
#         """CREATE TABLE settings (
#         key VARCHAR(255) PRIMARY KEY,
#         val VARCHAR(255) )"""
#     )
#     connection.commit()
#     print("Database initialized.")

# jinja = Environment(
#     loader=FileSystemLoader(TEMPLATE_DIR),
#     autoescape=select_autoescape(["html", "xml"]),
# )
# jinja.filters["date"] = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").strftime("%A, %B %d, %Y")

#--
# async def parse_feed(feed_url):
#     return feedparser.parse(feed_url)

# async def main():
#     a = datetime.now()
#     with open(FEED_FILE, "r") as stream:
#         tasks = [parse_feed(url) for url in yaml.load(stream)]
#         await asyncio.gather(*tasks)
#     b = datetime.now()
#     c = b - a
#     print(divmod(c.days * 86400 + c.seconds, 60))

# asyncio.run(main())
#--

#-
def thread_wrapper(func, args, res):
    res.append(func(*args))

a = datetime.now()
feeds = []
with open(FEED_FILE, "r") as stream:
    threads = [threading.Thread(target=thread_wrapper, args=(feedparser.parse, (url,), feeds,)) for url in yaml.load(stream)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
b = datetime.now()
c = b - a
print(divmod(c.days * 86400 + c.seconds, 60))
print(len(feeds))
#-

#--
# a = datetime.now()
# with open(FEED_FILE, "r") as stream:
#     for feed_url in yaml.load(stream):
#         feed = feedparser.parse(feed_url)
# b = datetime.now()
# c = b - a
# print(divmod(c.days * 86400 + c.seconds, 60))
#--

#         for item in feed["entries"]:
#             m = md5(item["link"].encode("utf-8")).hexdigest()
#             result = connection.execute("SELECT * FROM feeds WHERE url_md5 = :m", { "m": m })
#             if result.fetchone() is None:
#                 if "content" in item:
#                     content = item["content"][0]["value"]
#                 else:
#                     content = item["summary"]

#                 if "published_parsed" in item:
#                     date = item["published_parsed"]
#                 else:
#                     date = item["updated_parsed"]
#                 connection.execute(
#                     """INSERT INTO feeds (
#                         url, url_md5, title, site_url, site_title, date, content
#                     ) VALUES (
#                         :url, :url_md5, :title, :site_url, :site_title, :date, :content
#                     )""", {
#                         "url": item["link"],
#                         "url_md5": m,
#                         "title": item["title"],
#                         "site_url": feed["feed"]["link"],
#                         "site_title": feed["feed"]["title"],
#                         "date": datetime.fromtimestamp(time.mktime(date)).isoformat(),
#                         "content": content
#                     }
#                 )
#             result.close()

# connection.commit()

# template = jinja.get_template("template.html")
# with open("{}/index.html".format(OUTPUT), "wb") as stream:
#     today = connection.execute("SELECT * FROM feeds WHERE date > :today ORDER BY date DESC", {
#         "today": datetime.now().strftime("%Y-%m-%d")
#     })
#     stream.write(template.render(items=today, title="Today").encode("utf-8"))
#     today.close()

# with open("{}/yesterday.html".format(OUTPUT), "wb") as stream:
#     yesterday = connection.execute("SELECT * FROM feeds WHERE date > :yesterday AND date < :today ORDER BY date DESC", {
#         "yesterday": datetime.strftime(datetime.now() - timedelta(1), "%Y-%m-%d"),
#         "today": datetime.now().strftime("%Y-%m-%d")
#     })
#     stream.write(template.render(items=yesterday, title="Yesterday").encode("utf-8"))
#     yesterday.close()

# with open("{}/latest100.html".format(OUTPUT), "wb") as stream:
#     latest100 = connection.execute("SELECT * FROM feeds ORDER BY date DESC LIMIT 100")
#     stream.write(template.render(items=latest100, title="Latest 100").encode("utf-8"))
#     latest100.close()

# connection.close()
