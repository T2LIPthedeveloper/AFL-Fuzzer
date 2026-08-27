package com.aflfuzzer.spring.campaign;

import com.aflfuzzer.spring.config.AflProperties;
import com.aflfuzzer.spring.model.CampaignRequest;
import com.aflfuzzer.spring.model.CampaignStatus;
import com.aflfuzzer.spring.model.SeedPayload;
import com.aflfuzzer.spring.model.TargetResponse;
import com.aflfuzzer.spring.mutation.DictionaryFileLoader;
import com.aflfuzzer.spring.mutation.DictionaryMutator;
import com.aflfuzzer.spring.mutation.MutationEngine;
import com.aflfuzzer.spring.schedule.PowerScheduleService;
import com.aflfuzzer.spring.targetclient.HttpTargetClient;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class CampaignService {
    private final SeedQueueService seedQueueService;
    private final MutationEngine mutationEngine;
    private final HttpTargetClient targetClient;
    private final AflProperties properties;
    private final CrashHotIntensity crashHotIntensity;
    private final PowerScheduleService powerScheduleService;
    private final DictionaryMutator dictionaryMutator;
    private final DictionaryFileLoader dictionaryFileLoader;
    private final Map<String, CampaignStatus> campaigns = new ConcurrentHashMap<>();
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public CampaignService(
            SeedQueueService seedQueueService,
            MutationEngine mutationEngine,
            HttpTargetClient targetClient,
            AflProperties properties,
            CrashHotIntensity crashHotIntensity,
            PowerScheduleService powerScheduleService,
            DictionaryMutator dictionaryMutator,
            DictionaryFileLoader dictionaryFileLoader
    ) {
        this.seedQueueService = seedQueueService;
        this.mutationEngine = mutationEngine;
        this.targetClient = targetClient;
        this.properties = properties;
        this.crashHotIntensity = crashHotIntensity;
        this.powerScheduleService = powerScheduleService;
        this.dictionaryMutator = dictionaryMutator;
        this.dictionaryFileLoader = dictionaryFileLoader;
        try {
            Path dict = new ClassPathResource("dictionaries/http_api.dict").getFile().toPath();
            List<String> tokens = dictionaryFileLoader.load(dict);
            dictionaryMutator.replaceTokens(tokens);
        } catch (Exception ignored) {
            // Keep built-in tokens when classpath dict is unavailable.
        }
    }

    public CampaignStatus start(CampaignRequest request) {
        CampaignStatus status = new CampaignStatus();
        status.setId(UUID.randomUUID().toString());
        status.setState(CampaignStatus.State.PENDING);
        int iterations = request.getIterations() > 0 ? request.getIterations() : properties.getDefaultIterations();
        status.setPlannedIterations(iterations);
        status.setStartedAt(Instant.now());

        if (request.getResumeFile() != null && !request.getResumeFile().isBlank()) {
            Path resume = Path.of(request.getResumeFile()).toAbsolutePath().normalize();
            if (!Files.exists(resume)) {
                status.setState(CampaignStatus.State.FAILED);
                status.setMessage("Resume file not found: " + resume);
                status.setFinishedAt(Instant.now());
                campaigns.put(status.getId(), status);
                return status;
            }
            status.getNotes().add("Resume path accepted: " + resume);
        }

        seedQueueService.replaceAll(request.getSeeds());
        campaigns.put(status.getId(), status);
        executor.submit(() -> runCampaign(status.getId(), iterations));
        return status;
    }

    public CampaignStatus get(String id) {
        return campaigns.get(id);
    }

    private void runCampaign(String id, int iterations) {
        CampaignStatus status = campaigns.get(id);
        if (status == null) {
            return;
        }
        status.setState(CampaignStatus.State.RUNNING);
        try {
            for (int i = 0; i < iterations; i++) {
                SeedPayload seed = seedQueueService.choose();
                int legacy = crashHotIntensity.mutationCount(
                        seed.getMethod(), seed.getPath(), properties.getMutationMin(), properties.getMutationMax());
                int scheduled = powerScheduleService.energy(seed);
                int mutationCount = Math.max(1, (int) Math.round(0.45 * legacy + 0.55 * Math.min(12, scheduled)));
                SeedPayload mutated;
                if (ThreadLocalRandom.current().nextDouble() < 0.15) {
                    mutated = mutationEngine.mutateWithDonor(seed, seedQueueService.choose(), mutationCount);
                } else {
                    mutated = mutationEngine.mutate(seed, mutationCount);
                }
                TargetResponse response = targetClient.execute(mutated);
                status.setCompletedIterations(i + 1);
                // BUG: coverage gain is not forwarded (always 0), so schedule coverage counters stall.
                powerScheduleService.record(mutated, 0.0, response.isCrash());
                if (response.isInteresting()) {
                    status.setInterestingCount(status.getInterestingCount() + 1);
                    seedQueueService.addInteresting(mutated);
                }
                if (response.isCrash()) {
                    status.setCrashCount(status.getCrashCount() + 1);
                    crashHotIntensity.noteCrash(mutated.getMethod(), mutated.getPath());
                }
            }
            status.setState(CampaignStatus.State.COMPLETED);
            status.setMessage("Campaign completed");
            status.getNotes().add("powerScheduleMode=" + powerScheduleService.getMode());
        } catch (Exception ex) {
            status.setState(CampaignStatus.State.FAILED);
            status.setMessage(ex.getMessage());
        } finally {
            status.setFinishedAt(Instant.now());
        }
    }
}
