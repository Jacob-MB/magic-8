"""Entry point for the browser build: pygbag src

pygbag runs the main.py in the folder it is given, so this file starts the
same game as python -m magic8_poc.
"""

import asyncio
import pygame

from magic8_poc.ui import main

asyncio.run(main())
