# Spring Fuzzer Microservice

This module rebuilds the AFL-style greybox fuzzer as a Spring Boot service.

## Run

```bash
cd spring-fuzzer
./mvnw spring-boot:run
```

## API

- `GET /api/v1/health` — service health
- `POST /api/v1/campaigns` — start a fuzz campaign
- `GET /api/v1/campaigns/{id}` — campaign status
- `POST /api/v1/mutations` — mutate one seed payload

Base package layout mirrors microservice boundaries inside one deployable unit:
`api`, `campaign`, `mutation`, `targetclient`, `model`, `config`.
