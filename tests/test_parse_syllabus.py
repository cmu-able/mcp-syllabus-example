# -*- coding: utf-8 -*-
from syllabus_server.server import parse_syllabus
import json

print(json.dumps(parse_syllabus("pdfs/17611.pdf"), indent=2))