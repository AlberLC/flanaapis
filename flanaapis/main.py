import os
import sys

import flanautils
import uvicorn
from fastapi import FastAPI

import flanaapis.geolocation.routes
import flanaapis.scraping.routes
import flanaapis.weather.routes

os.environ |= flanautils.find_environment_variables('../.env')

sub_app = FastAPI()
sub_app.include_router(flanaapis.geolocation.routes.router)
sub_app.include_router(flanaapis.scraping.routes.router)
sub_app.include_router(flanaapis.weather.routes.router)

app = FastAPI()
app.mount('/flanaapis', sub_app)

if __name__ == '__main__':
    try:
        host = sys.argv[1]
    except IndexError:
        host = os.environ.get('FLANAAPIS_HOST')
    try:
        port = sys.argv[2]
    except IndexError:
        port = os.environ.get('FLANAAPIS_PORT')

    uvicorn.run('main:app', host=host, port=int(port))
