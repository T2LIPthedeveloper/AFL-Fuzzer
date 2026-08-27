package com.aflfuzzer.spring.targetclient;

import com.aflfuzzer.spring.config.AflProperties;
import com.aflfuzzer.spring.model.SeedPayload;
import com.aflfuzzer.spring.model.TargetResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class HttpTargetClient {
    private final RestClient restClient;

    public HttpTargetClient(AflProperties properties) {
        this.restClient = RestClient.builder()
                .baseUrl(properties.getTargetBaseUrl())
                .build();
    }

    public TargetResponse execute(SeedPayload seed) {
        TargetResponse response = new TargetResponse();
        try {
            String body = restClient.method(org.springframework.http.HttpMethod.valueOf(seed.getMethod()))
                    .uri(seed.getPath())
                    .body(seed.getBody())
                    .retrieve()
                    .body(String.class);
            response.setStatusCode(200);
            response.setBody(body == null ? "" : body);
            response.setInteresting(body != null && body.length() > 0);
            response.setCrash(false);
        } catch (RestClientException ex) {
            response.setStatusCode(0);
            response.setError(ex.getMessage());
            response.setInteresting(true);
            response.setCrash(true);
        }
        return response;
    }
}
