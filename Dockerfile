FROM python:3.11

RUN python3 -m venv venv
RUN . ./venv/bin/activate

COPY ./requirements.txt requirements.txt

RUN pip3 install -r requirements.txt
