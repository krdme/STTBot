#FROM tiangolo/uwsgi-nginx-flask:python3.7
FROM python:3.7
#ENV LISTEN_PORT 3000
#EXPOSE 3000
COPY . /bot
WORKDIR /bot
RUN pip3.7 install -r requirements.txt
CMD [ "python3.7", "./start.py" ]
