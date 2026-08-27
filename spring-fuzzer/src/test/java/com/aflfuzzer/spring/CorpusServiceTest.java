package com.aflfuzzer.spring;

import com.aflfuzzer.spring.corpus.CorpusService;
import com.aflfuzzer.spring.model.SeedPayload;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class CorpusServiceTest {
    @Test
    void storesAndChoosesSeed() {
        CorpusService corpus = new CorpusService(10);
        SeedPayload seed = new SeedPayload();
        seed.setPath("/x");
        seed.setMethod("POST");
        seed.getBody().put("a", 1);
        corpus.add(seed, 1.2, 1.0, true, 1, null);
        assertTrue(corpus.choose().isPresent());
    }
}
