From debian
MAINTAINER docker@deliverous.com
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get -y dist-upgrade && apt-get install -y python-pip python-dev supervisor exim4 && apt-get clean
RUN pip install graphite-beacon
RUN pip install supervisor-stdout

# Supervisord
ADD docker/supervisor.conf /etc/supervisor/conf.d/deliverous.conf

# Conf Exim
ADD docker/update-exim4.conf.conf /etc/exim4/update-exim4.conf.conf
ADD docker/exim4 /etc/default/exim4

# Add a default /config.json for backward compatibility
RUN echo '{ "include":["/srv/alerting/etc/config.json"] }' > /config.json

CMD ["/usr/bin/supervisord"]

