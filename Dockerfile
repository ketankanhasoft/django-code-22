FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/
# Expose ports
#RUN python manage.py makemigrations account
#RUN python manage.py migrate
#RUN python manage.py makemigrations job
#RUN python manage.py migrate
#RUN python manage.py makemigrations match
#RUN python manage.py migrate
EXPOSE 8000
EXPOSE 6379
# default command to execute    
CMD exec gunicorn django_demo.wsgi:application --bind 0.0.0.0:8000 --workers 3
# CMD ["gunicorn", "truckerpilot.wsgi", "0:8000" , "0:6379"]
