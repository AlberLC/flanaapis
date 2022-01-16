import os

import flanautils

os.environ |= flanautils.find_environment_variables('../.env')

import sys

import uvicorn
from fastapi import APIRouter, FastAPI

import flanaapis.geolocation.routes
import flanaapis.scraping.routes
import flanaapis.weather.routes

main_router = APIRouter(prefix='/flanaapis')
main_router.include_router(flanaapis.geolocation.routes.router)
main_router.include_router(flanaapis.scraping.routes.router)
main_router.include_router(flanaapis.weather.routes.router)
app = FastAPI()
app.include_router(main_router)

if __name__ == '__main__':
    try:
        host = sys.argv[1]
    except IndexError:
        host = os.environ.get('FLANAAPIS_ADDRESS')
    try:
        port = sys.argv[2]
    except IndexError:
        port = os.environ.get('FLANAAPIS_PORT')

    uvicorn.run('main:app', host=host, port=int(port))
