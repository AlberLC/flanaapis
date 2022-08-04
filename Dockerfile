FROM flanaganvaquero/flanawright

WORKDIR /application

COPY flanaapis flanaapis
COPY venv/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

ENV PYTHONPATH=/application

CMD python3.10 -u flanaapis/main.py
