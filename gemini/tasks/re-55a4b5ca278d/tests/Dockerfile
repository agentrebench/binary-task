FROM python@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0
WORKDIR /tests
COPY verifier.py contract.json test.sh /tests/
RUN mkdir -p /logs/verifier /logs/artifacts && chmod 0555 /tests/test.sh
