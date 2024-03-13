FROM python:3.10-slim

# install os dependencies
RUN apt-get update && apt-get install -y curl

# home
RUN mkdir -p /home/
ENV HOME /home

# install requirements
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN rm /tmp/requirements.txt

# change workdir
COPY src $HOME/src
WORKDIR $HOME/src

EXPOSE 8080

# run the app
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "critical"]
