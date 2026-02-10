FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=18080
ENV PYTHONPATH=/opt/domainac

WORKDIR /opt/domainac

COPY requirements.txt /opt/domainac/requirements.txt
RUN pip install --no-cache-dir -r /opt/domainac/requirements.txt

COPY app /opt/domainac/app

EXPOSE 18080

CMD ["python", "-m", "app.run_server"]
