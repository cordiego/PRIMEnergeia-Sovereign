FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY optimization/ ./optimization/

ENV SIBO_API_KEY_STARTER=sibo_starter_demo
ENV SIBO_API_KEY_PRO=sibo_pro_demo
ENV SIBO_API_KEY_ENTERPRISE=sibo_enterprise_demo

EXPOSE 8000

CMD ["uvicorn", "api.sibo_api:app", "--host", "0.0.0.0", "--port", "8000"]
