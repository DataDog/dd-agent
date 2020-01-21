FROM python:2.7-stretch

RUN apt update && apt install -y ssh ca-certificates git tar gzip ruby bundler
RUN apt install -y libgnutls28-dev

# setup for docker in docker
RUN apt install -y apt-transport-https ca-certificates curl gnupg2 software-properties-common && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add - && \
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian stretch stable" && \
    apt-get update && apt install -y docker-ce

# setup java
RUN apt install -y default-jre


