FROM flanaganvaquero/flanawright

WORKDIR /application
COPY flanaapis flanaapis
COPY requirements.txt .

RUN pip3.10 install -r requirements.txt

ENV PYTHONPATH=/application

CMD python3.10 flanaapis/main.py