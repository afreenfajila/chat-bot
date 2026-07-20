# certs/

Optional folder for corporate root CA certificates (e.g. Zscaler or another
TLS-inspection proxy). `docker-compose.yml` mounts this whole directory
read-only into every container and runs `update-ca-certificates` before
starting each service.

- **On a network with SSL inspection:** drop your corporate root CA `.crt`
  file(s) in here (any filename). No other setup needed — the container will
  pick them up automatically on the next `docker compose up --build`.
- **On a normal network:** leave this folder empty. An empty folder is
  completely harmless; `update-ca-certificates` just has nothing to add.

Everything in this folder except this README is gitignored, so your
certificate never gets committed. You never need to edit
`docker-compose.yml` to use (or not use) a corporate CA.
