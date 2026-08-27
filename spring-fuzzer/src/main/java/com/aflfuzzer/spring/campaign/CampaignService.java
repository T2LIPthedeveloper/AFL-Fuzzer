package com.aflfuzzer.spring.campaign;

import com.aflfuzzer.spring.config.AflProperties;
import com.aflfuzzer.spring.model.CampaignRequest;
import com.aflfuzzer.spring.model.CampaignStatus;
import com.aflfuzzer.spring.model.SeedPayload;
import com.aflfuzzer.spring.model.TargetResponse;
import com.aflfuzzer.spring.mutation.MutationEngine;
import com.aflfuzzer.spring.targetclient.HttpTargetClient;
import org.springframework.stereotype.Service;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
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
    private final Map<String, CampaignStatus> campaigns = new ConcurrentHashMap<>();
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public CampaignService(
            SeedQueueService seedQueueService,
            MutationEngine mutationEngine,
            HttpTargetClient targetClient,
            AflProperties properties,
            CrashHotIntensity crashHotIntensity
    ) {
        this.seedQueueService = seedQueueService;
        this.mutationEngine = mutationEngine;
        this.targetClient = targetClient;
        this.properties = properties;
        this.crashHotIntensity = crashHotIntensity;
    }

    public CampaignStatus start(CampaignRequest request) {
        CampaignStatus status = new CampaignStatus();
        status.setId(UUID.randomUUID().toString());
        status.setState(CampaignStatus.State.PENDING);
        int iterations = request.getIterations() > 0 ? request.getIterations() : properties.getDefaultIterations();
        status.setPlannedIterations(iterations);
        status.setStartedAt(Instant.now());

        if (request.getResumeFile() != null && !request.getResumeFile().isBlank()) {
            // Resolve to an absolute path so resume loads reliably across working directories.
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
                int mutationCount = crashHotIntensity.mutationCount(
                        seed.getMethod(),
                        seed.getPath(),
                        properties.getMutationMin(),
                        properties.getMutationMax()
                );
                SeedPayload mutated;
                if (ThreadLocalRandom.current().nextDouble() < 0.15) {
                    SeedPayload donor = seedQueueService.choose();
                    mutated = mutationEngine.mutateWithDonor(seed, donor, mutationCount);
                } else {
                    mutated = mutationEngine.mutate(seed, mutationCount);
                }
                TargetResponse response = targetClient.execute(mutated);
                status.setCompletedIterations(i + 1);
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
        } catch (Exception ex) {
            status.setState(CampaignStatus.State.FAILED);
            status.setMessage(ex.getMessage());
        } finally {
            status.setFinishedAt(Instant.now());
        }
    }
}
