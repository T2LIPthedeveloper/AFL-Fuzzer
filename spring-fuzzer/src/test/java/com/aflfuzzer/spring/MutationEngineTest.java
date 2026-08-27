package com.aflfuzzer.spring;

import com.aflfuzzer.spring.model.SeedPayload;
import com.aflfuzzer.spring.mutation.DictionaryMutator;
import com.aflfuzzer.spring.mutation.MutationEngine;
import com.aflfuzzer.spring.mutation.SpliceService;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertNotNull;

class MutationEngineTest {
    @Test
    void mutatesPayload() {
        MutationEngine engine = new MutationEngine(new DictionaryMutator(), new SpliceService());
        SeedPayload seed = new SeedPayload();
        seed.getBody().put("x", "hello");
        SeedPayload mutated = engine.mutate(seed, 2);
        assertNotNull(mutated);
        assertNotNull(mutated.getBody());
    }
}
