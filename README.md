# GptFlow

To run in production environment:
1. Copy the example configuration files to production files and make the actual
changes.
```
cp example.docker-compose.prod.yaml docker-compose.prod.yaml
cp example.traefik.prod.toml traefik.prod.toml
```
2. Run containers.
```
$ docker-compose -f docker-compose.prod.yml up -d --build
```