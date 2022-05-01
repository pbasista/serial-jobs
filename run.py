#!/usr/bin/env python
from asyncio import run

from serial_jobs import work

run(work())
