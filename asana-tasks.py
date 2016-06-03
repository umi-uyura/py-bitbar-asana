#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Displays the tasks that are assigned to you in the specified workspace on Asana
#
# by Umi Uyura (http://github.com/umi-uyura)
#
# <bitbar.title>Asana tasks</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>Umi Uyura</bitbar.author>
# <bitbar.author.github>umi-uyura</bitbar.author.github>
# <bitbar.desc>Displays the tasks that are assigned to you in the specified workspace on Asana.</bitbar.desc>
# <bitbar.image>https://raw.githubusercontent.com/umi-uyura/py-bitbar-asana/master/doc/screenshot1.png</bitbar.image>
# <bitbar.dependencies>python</bitbar.dependencies>
# <bitbar.abouturl>https://github.com/umi-uyura/py-bitbar-asana</bitbar.abouturl>

import sys
import os
import httplib
import urllib
import json
from datetime import datetime, date, timedelta
import time
import locale


#
# Constant
#

PERSONAL_ACCESS_TOKEN = ""
WORKSPACE_ID = ""
DISPLAY_RANGE_MONTH = 2
LOCALE = ""
MENUBAR_IMAGE = ""

# Script constant
ASANA_API_BASE = "/api/1.0"
ASANA_URL_BASE = "https://app.asana.com/0/"
ASANA_MENUBAR_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAQAAAC1+jfqAAABAklEQVR4AW1RJ2ICURQcyp+3rMWBxqT3xKReAJNyCyxIJAfAozkBkiugyA1SHCY94eU3Ov/1ebNldjE9GZ+z1mYTltZs8tFacx0lB0hblNZEpR2Q2ckChTLfqfyxpvwolB26QOAm/6yNrbm6tUjIuOBQlJ/8tHkYkNk6DwLmTF5Frb2YMwC0aGb5bYt84AOKy+ogNemxm9xM0OSGXelJLY7sTOSx6ufqdO4AMIdR3AeVA08YOKFBsDkE7+z4TeWYKs9IkcqzmyJ6B6lQrX3xQ1T6/o364u7w5XCpAGBd1BlHZtcRzC5HEalHIckFW2ykpcnfTEtssJVchO38J83N5bj5BynJX+qZZpYZAAAAAElFTkSuQmCC"

#
# Functions
#

def print_error(excep):
    print "{0}: {1}".format(type(excep), excep)


def is_show_task(t, show_limit):
    if t["due_on"] is not None:
        due_on = datetime.strptime(t["due_on"], "%Y-%m-%d").date()
        return due_on <= show_limit
    return False


#
# Logic
#

if LOCALE != "":
    locale.setlocale(locale.LC_ALL, LOCALE)


# Action

param = sys.argv

if len(param) > 1:
    text = param[1]
    os.system("echo {0} | pbcopy".format(text))
    os.system("osascript -e 'display notification \"Copy the selected workspace ID to the clipboard\" with title \"asana-tasks\"' &>/dev/null && echo true || echo false")
    sys.exit(1)

script_path = os.path.abspath(__file__)


# Menubar image

print "| templateImage={0}".format(ASANA_MENUBAR_IMAGE if MENUBAR_IMAGE == "" else MENUBAR_IMAGE)
print "---"

# Get user information

headers = {"Authorization": "Bearer " + PERSONAL_ACCESS_TOKEN}
conn = httplib.HTTPSConnection("app.asana.com")

try:
    conn.request("GET", ASANA_API_BASE + "/users/me", None, headers)
    response = conn.getresponse()
except Exception as e:
    print_error(e)
    conn.close()
    sys.exit(1)

user = None
assignee_name = ""
assignee_id = ""

if response.status == httplib.OK:
    user = json.load(response)
    assignee_name = user["data"]["name"]
    assignee_id = user["data"]["id"]
else:
    print response.status, response.reason
    conn.close()
    sys.exit(1)

# List workspaces

if WORKSPACE_ID == "":
    print "Workspaces:"
    for ws in user["data"]["workspaces"]:
        print "{0} ({1}) | bash='{2}' param1={1} terminal=false".format(ws["name"].encode("utf-8"),
                                                                        ws["id"],
                                                                        script_path)
    conn.close()
    sys.exit()

workspace = next(ws for ws in user["data"]["workspaces"] if str(ws["id"]) == WORKSPACE_ID)
print "Workspace: {0} (Assignee: {1}) | href={2}{3}".format(workspace["name"].encode("utf-8"),
                                                            assignee_name.encode("utf-8"),
                                                            ASANA_URL_BASE,
                                                            WORKSPACE_ID)
print "--Calendar | href={0}{1}/calendar".format(ASANA_URL_BASE, WORKSPACE_ID)
print "-----"

# List projects

try:
    conn.request("GET", ASANA_API_BASE + "/workspaces/" + WORKSPACE_ID + "/projects", None, headers)
    response = conn.getresponse()
except Exception as e:
    print_error(e)
    conn.close()
    sys.exit(1)

projects = None

if response.status == httplib.OK:
    projects = json.load(response)
else:
    print response.status, response.reason
    conn.close()
    sys.exit(1)

for pj in projects["data"]:
    print "--{0} | href={1}{2}".format(pj["name"].encode("utf-8"), ASANA_URL_BASE, pj["id"])

print "---"

# List tasks

today = date.today()

tomorrow = today + timedelta(days=1)
query = urllib.urlencode({"assignee": assignee_id,
                          "workspace": WORKSPACE_ID,
                          "opt_fields": "due_on,name,projects",
                          "completed_since": tomorrow.strftime("%Y-%m-%dT%H:%M:%S.000Z")})

try:
    conn.request("GET", ASANA_API_BASE + "/tasks?" + query, None, headers)
    response = conn.getresponse()
except Exception as e:
    print_error(e)
    conn.close()
    sys.exit(1)

tasks = None

if response.status == httplib.OK:
    tasks = json.load(response)
else:
    print response.status, response.reason
    conn.close()
    sys.exit(1)

current_week = today + timedelta(days=(6 - today.weekday()))
limit = today + timedelta(days=(DISPLAY_RANGE_MONTH * 30))

progress_tasks = [x for x in tasks["data"] if is_show_task(x, limit)]
progress_tasks = sorted(progress_tasks,
                        key=lambda x: int(time.mktime(datetime.strptime(x["due_on"], "%Y-%m-%d").timetuple())))

nextweek = None
for task in progress_tasks:
    due = datetime.strptime(task["due_on"], "%Y-%m-%d").date()
    task["due_on_datetime"] = due

    if nextweek is None and due > current_week:
        nextweek = due
        print "---"

    pj = None
    if len(task["projects"]):
        pj = [x for x in projects["data"] if x["id"] == task["projects"][0]["id"]]

    if due == today:
        color = "green"
    elif due < today:
        color = "red"
    else:
        color = "black"

    print "{0}({1}) {2} [{3}] | href={4}{5}/{6} color={7}".format(
        task["due_on_datetime"].strftime(locale.nl_langinfo(locale.D_FMT)),
        task["due_on_datetime"].strftime("%a"),
        task["name"].encode("utf-8"),
        pj[0]["name"].encode("utf-8") if pj is not None else "",
        ASANA_URL_BASE,
        WORKSPACE_ID,
        task["id"],
        color)

# Close session
conn.close()

sys.exit()
