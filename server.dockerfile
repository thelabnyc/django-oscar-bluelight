FROM python:3.6

RUN mkdir -p /oscarbluelight/server /oscarbluelight/client
WORKDIR /oscarbluelight/server

ADD server/ /oscarbluelight/server/
RUN pip install -e .[development]

RUN mkdir /oscarbluelight/tox
ENV TOX_WORK_DIR='/oscarbluelight/tox'

# Set entry point so that packages are always updated before compiling things
ENTRYPOINT ["/oscarbluelight/server/entrypoint.sh"]
CMD ["python", "sandbox/manage.py", "runserver"]
