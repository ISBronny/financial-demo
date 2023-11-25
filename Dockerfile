FROM rasa/rasa-sdk:3.1.0

COPY actions /app/actions

USER root
RUN pip install --no-cache-dir -r /Users/bastard/PycharmProjects/financial-demo/actions/requirements-actions.txt

USER 1001
CMD ["start", "--actions", "actions"]
